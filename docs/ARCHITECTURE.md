# Architecture Overview

TradingAgents coordinates a LangGraph-powered ensemble of specialised agents, a FastAPI services layer, optional background workers, and a Next.js Control Center. This document summarises the major components, data flows, and extensibility hooks that power the platform.

## Table of Contents

1. [Multi-Agent Workflow](#multi-agent-workflow)
2. [Repository Layout](#repository-layout)
3. [Backend Architecture](#backend-architecture)
   - [LangGraph Orchestration](#langgraph-orchestration)
   - [Agent Plugin System](#agent-plugin-system)
   - [Data Vendor Plugin System](#data-vendor-plugin-system)
   - [Persistence & Caching](#persistence--caching)
   - [Streaming Infrastructure](#streaming-infrastructure)
   - [Execution & Risk Management](#execution--risk-management)
   - [Monitoring & Alerting](#monitoring--alerting)
4. [Frontend Control Center](#frontend-control-center)
5. [Data & Configuration Flow](#data--configuration-flow)
6. [Related Resources](#related-resources)

## Multi-Agent Workflow

TradingAgents decomposes research-to-trade into coordinated agent roles:

- **Analyst Team** – Fundamental, sentiment, news, and technical analysts source signals, indicators, and qualitative context.
- **Research Panel** – Bullish and bearish researchers debate the analyst output to expose blind spots.
- **Trader Agent** – Synthesises recommendations into executable trade proposals with confidence scoring.
- **Risk & Portfolio Management** – Evaluates exposures, limits, and compliance before trades are approved for execution.

<p align="center">
  <img src="../assets/schema.png" style="width: 100%; height: auto;" alt="Multi-agent workflow">
</p>

Each role is implemented as a LangGraph node with access to toolkits, vector memories, and vendor data. Responses propagate through the state machine until a final decision (buy/sell/hold) is produced.

## Repository Layout

```
.
├── packages/
│   ├── backend/                 # LangGraph graph, FastAPI app, workers, persistence layer
│   ├── frontend/                # Next.js Control Center
│   └── shared/                  # Shared TypeScript clients, schemas, UI tokens
├── docs/                        # Unified documentation (setup, architecture, API, etc.)
├── scripts/                     # Deployment helpers (deploy.sh, healthcheck.sh)
├── docker-compose*.yml          # Deployment stacks
└── assets/                      # Architecture diagrams, CLI screenshots
```

The workspace is orchestrated by PNPM. `pnpm sync` installs JavaScript dependencies and runs `uv sync` for the Python backend.

## Backend Architecture

### LangGraph Orchestration

- `tradingagents.graph.TradingAgentsGraph` defines the state machine linking analyst, researcher, trader, and risk nodes.
- Nodes access vendor data, reflection memories, and shared state through toolkits defined under `tradingagents.agents.utils`.
- Graph runs can be configured via environment variables (`TRADINGAGENTS_*`), CLI parameters, or API payload overrides.

### Agent Plugin System

Location: `tradingagents/agents/`

- **AgentPlugin** (`plugin_base.py`) defines the contract for all agents (metadata, capabilities, prompts, required tools, node factory).
- **Registry** (`plugin_registry.py`) manages built-in and custom plugins, slot assignments, and discovery via entry points.
- **Built-in agents** cover 12 specialised roles across analysts, researchers, risk analysts, and managers. Reserved workflow slots guarantee core coverage while allowing custom extensions.
- **Persistence** (`app/db/models/agent_config.py`) stores agent definitions with hot-reload support through REST endpoints.
- **API** (`app/api/agents.py`) exposes CRUD operations, filtering, pagination, and a `/agents/reload` endpoint for dynamic updates.

### Data Vendor Plugin System

Location: `tradingagents/plugins/`

- **DataVendorPlugin** (`base.py`) encapsulates vendor behaviour, including capability advertising (stock data, fundamentals, news, technical indicators, insider data, etc.).
- **VendorPluginRegistry** (`registry.py`) discovers built-in and third-party vendors, manages lifecycle, and exposes capability filtering.
- **Router** (`router.py`) orchestrates fallback chains, priority ordering, and rate limiting when fetching data.
- **Config Manager** (`config_manager.py`) loads YAML/JSON config files with hot-reload support; routing rules are persisted to disk.
- **Built-in vendors** include Alpha Vantage, yfinance, OpenAI, Google News, and a local/offline bundle.
- **Admin API** (`app/api/vendors.py`) offers:
  - `GET /vendors/` – List plugins and capabilities
  - `GET /vendors/{name}/config` – Inspect vendor settings
  - `PUT /vendors/{name}/config` – Update configuration (rate limits, API keys)
  - `GET /vendors/routing/config` – View routing rules per method
  - `PUT /vendors/routing/config` – Set priority chains
  - `POST /vendors/config/reload` – Hot-reload configuration files

### Persistence & Caching

Location: `app/db/`, `app/repositories/`, `app/cache/`

- **Models** (`SQLModel`) store portfolios, positions, trades, executions, agent configs, vendor configs, and run logs.
- **Alembic** powers schema migrations with async support (`alembic.ini`, `alembic/env.py`).
- **Repositories** implement a typed CRUD layer (e.g., `PortfolioRepository`, `TradeRepository`) with domain-specific queries.
- **Database Manager** handles engine initialisation, session lifecycle, and optional table creation for SQLite development use.
- **Redis Cache** (`cache_service.py`) provides optional caching of market data, session state, and generic key/value storage. Connection details are managed by `REDIS_*` environment variables.

### Streaming Infrastructure

Location: `app/workers/`, `app/api/streaming.py`, `app/api/streaming_config.py`

- **Workers** poll vendor plugins on a cadence to refresh market data, fundamentals, news, analytics, and insider metrics. Backoff strategies and vendor fallback are built in.
- **Redis Pub/Sub** channels (e.g., `stream:market_data:{symbol}`) broadcast updates; latest snapshots are cached with TTL for quick access.
- **SSE Endpoint**: `POST /streaming/subscribe/sse` accepts channel subscriptions and streams real-time events.
- **WebSocket Endpoint**: `WS /streaming/ws` mirrors SSE payloads with bidirectional support.
- **Configuration API**:
  - Instruments: `GET/POST/DELETE /streaming/config/instruments`
  - Cadences: `GET/PUT /streaming/config/cadences/{data_type}`
  - Worker control: `/streaming/config/workers/*`
  - Telemetry: `/streaming/config/telemetry/{data_type}` exposes vendor latency and error metrics.
- **Environment Flags**: `STREAMING_ENABLED`, `AUTO_START_WORKERS`, and Redis settings govern behaviour.

### Execution & Risk Management

Location: `app/services/execution.py`, `app/services/risk_management.py`, `app/services/position_sizing.py`, `app/services/broker_adapter.py`

- **ExecutionService** transforms trader decisions into orders, enforcing pre-trade risk checks and updating persistence.
- **PositionSizingService** supports multiple strategies (fixed dollar, fixed percentage, risk-based, volatility-weighted, fractional Kelly) with configurable caps.
- **RiskManagementService** computes diagnostics (VaR, exposure, max drawdown, Sharpe) and enforces constraints (position limits, stop-loss/take-profit rules).
- **BrokerAdapter** abstraction includes a `SimulatedBroker` for paper trading with commission/slippage modelling; the interface is ready for live integrations.
- **TradingSessionService** orchestrates paper/live sessions, resets, and state transitions, persisting outcomes to the database.

### Monitoring & Alerting

Location: `app/monitoring/`, `app/api/monitoring.py`

- **Health Endpoint**: `GET /monitoring/health` aggregates database, Redis, vendor, and worker statuses with latency metrics.
- **Prometheus Metrics**: `GET /monitoring/metrics` exposes histograms and counters for HTTP requests, database latency, Redis operations, vendor usage, queue depth, and worker activity.
- **Additional Endpoints**: `/monitoring/vendors`, `/monitoring/workers`, `/monitoring/queues`, `/monitoring/database`, `/monitoring/redis`, `/monitoring/uptime`, `/monitoring/alerts/*`.
- **Alerting**: email and webhook channels can be enabled via environment variables (`ALERT_EMAIL_*`, `ALERT_WEBHOOK_*`); a worker watchdog monitors stalled tasks.
- **Frontend Dashboard**: `/monitoring` route in the Control Center surfaces real-time health, error rates, and alert history.

## Frontend Control Center

Located in `packages/frontend/`, the Next.js dashboard presents real-time trading operations.

Key features:

- **Portfolio Overview**: Live portfolio value, holdings, cash position, and P&L (daily and cumulative).
- **Signal Feed**: Streaming trading signals with action type, confidence, price context, and rationale.
- **Execution Timeline**: Chronological list of trades with status, cost, and agent justification.
- **Agent Activity Stream**: Role-filterable event feed for analysts, researchers, trader, and risk managers.
- **View Controls**: Time-range filters, overview vs. detailed tabs, dark-mode aware components built with shadcn/ui primitives.
- **Real-time Transport**: SSE/WebSocket hooks (`useRealtimePortfolio`, `useRealtimeSignals`, etc.) handle reconnection and status indicators.
- **Accessibility & Performance**: Keyboard navigation, ARIA labelling, responsive layout, virtualised lists, and Recharts for live visualisations.

Configuration is handled via `.env.local` (e.g., `NEXT_PUBLIC_API_URL`) or Compose environment variables during deployment.

## Data & Configuration Flow

1. **Environment variables** (see [docs/CONFIGURATION.md](./CONFIGURATION.md)) configure LLM providers, vendor routing, database targets, Redis, monitoring, and deployment-specific behaviour.
2. **Vendor and agent registries** load built-in plugins, discover third-party extensions, and persist configuration in the database or YAML/JSON files.
3. **LangGraph runs** pull data through vendor routers, maintain conversation state in vector memory, and propose trades.
4. **Execution services** validate trades against risk constraints, trigger broker adapters, and persist results.
5. **Streaming & monitoring** layers surface telemetry back to clients via REST, SSE/WebSocket, and Prometheus endpoints.
6. **Frontend dashboard** subscribes to streaming channels and monitoring endpoints to visualise activity in real time.

## Related Resources

- [API Reference](./API.md) – Complete endpoint catalogue with payloads and examples.
- [Configuration Guide](./CONFIGURATION.md) – Environment variables, vendor routing, agent overrides.
- [Deployment Guide](./DEPLOYMENT.md) – Docker stacks, production hardening, scaling, and maintenance.
- [Operations Guides](./operations/README.md) – Runtime playbooks and Kubernetes example manifests.

For detailed subsystem code, explore the paths highlighted above within `packages/backend` and `packages/frontend`.
