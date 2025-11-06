# Architecture Overview

TradingAgents coordinates a LangGraph-powered ensemble of specialised agents, a FastAPI services layer, optional background workers, and a Next.js Control Center. This document summarises the major components, data flows, and extensibility hooks that power the platform with an emphasis on the unified LLM provider registry, deterministic market data pipeline, and persisted session history.

## Table of Contents

1. [Multi-Agent Workflow](#multi-agent-workflow)
2. [Repository Layout](#repository-layout)
3. [Backend Architecture](#backend-architecture)
   - [LangGraph Orchestration](#langgraph-orchestration)
   - [Agent Plugin System](#agent-plugin-system)
   - [LLM Provider Stack](#llm-provider-stack)
   - [Data Vendor Plugin System](#data-vendor-plugin-system)
   - [Market Data Service & Broker Pipeline](#market-data-service--broker-pipeline)
   - [Persistence & Caching](#persistence--caching)
   - [Analysis Session Persistence & Event Streaming](#analysis-session-persistence--event-streaming)
   - [Streaming Infrastructure](#streaming-infrastructure)
   - [Execution & Risk Management](#execution--risk-management)
   - [Monitoring & Alerting](#monitoring--alerting)
4. [Frontend Control Center](#frontend-control-center)
5. [Data & Configuration Flow](#data--configuration-flow)
6. [Troubleshooting & Operational Notes](#troubleshooting--operational-notes)
7. [Related Resources](#related-resources)

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
│   └── shared/                  # Shared TypeScript clients, schemas, UI tokens and DTOs
├── docs/                        # Unified documentation (setup, architecture, API, etc.)
├── scripts/                     # Deployment helpers (deploy.sh, healthcheck.sh)
├── docker-compose*.yml          # Deployment stacks
└── assets/                      # Architecture diagrams, CLI screenshots
```

The workspace is orchestrated by PNPM. `pnpm sync` installs JavaScript dependencies and runs `uv sync` for the Python backend.

## Backend Architecture

### LangGraph Orchestration

- **Asynchronous Execution**: The `TradingGraphService` executes the synchronous `TradingAgentsGraph` within a `ThreadPoolExecutor`. This is a critical design pattern that prevents the computationally intensive graph runs from blocking the main FastAPI asynchronous event loop, ensuring the application remains responsive.
- **Graph Definition**: `tradingagents.graph.TradingAgentsGraph` defines the state machine linking analyst, researcher, trader, and risk nodes.
- **Toolkit Access**: Nodes access vendor data, reflection memories, and shared state through toolkits defined under `tradingagents.agents.utils`.
- **Configuration**: Graph runs can be configured via environment variables (`TRADINGAGENTS_*`), CLI parameters, or API payload overrides.

### Agent Plugin System

Location: `tradingagents/agents/`

- **AgentPlugin** (`plugin_base.py`) defines the contract for all agents (metadata, capabilities, prompts, required tools, node factory).
- **Registry** (`plugin_registry.py`) manages built-in and custom plugins, slot assignments, and discovery via entry points.
- **Built-in agents** cover 12 specialised roles across analysts, researchers, risk analysts, and managers. Reserved workflow slots guarantee core coverage while allowing custom extensions.
- **Persistence** (`app/db/models/agent_config.py`) stores agent definitions with hot-reload support through REST endpoints.
- **API** (`app/api/agents.py`) exposes CRUD operations, filtering, pagination, and a `/agents/reload` endpoint for dynamic updates.

### LLM Provider Stack

Location: `tradingagents/llm_providers/`, `app/services/llm_runtime.py`

- **Dynamic LLM Resolution**: The system supports dynamic, per-agent LLM configuration. The `TradingAgentsGraph` uses a `_resolve_llm` method that queries the `AgentLLMRuntime` service. This service fetches agent-specific LLM configurations from the database, enabling hot-reloading and fine-grained control without requiring a server restart.
- **Fallback Mechanism**: If the runtime manager fails to resolve an LLM for a specific agent, it gracefully falls back to a default `quick` or `deep` thinking model defined in the configuration.
- **Canonical Registry** (`registry.py`): This remains the source of truth for provider metadata (e.g., pricing, context windows, rate limits). The `AgentLLMRuntime` and `AgentLLMService` use this registry to validate configurations and populate model details.
- **Factory and Implementations**: The factory pattern (`factory.py`) and provider implementations (`openai_provider.py`, etc.) remain the core components for instantiating and interacting with different LLM APIs.

> ℹ️ The legacy static provider maps have been removed; all validation and pricing data should flow through `tradingagents.llm_providers`.

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

### Market Data Service & Broker Pipeline

Location: `app/services/market_data.py`

- **MarketDataService** mediates between broker operations and vendor plugins. It requests recent historical quotes via `route_to_vendor("get_stock_data", ...)`, parses CSV payloads, and derives bid/ask/last prices using configurable spreads.
- **Deterministic Fallbacks** – When vendors return nothing or raise errors, the service reuses cached quotes or computes a deterministic baseline derived from the ticker symbol. This guarantees reproducible fills for the simulated broker while surfacing warnings for observability.
- **Broker Integration** – Execution paths obtain `MarketPrice` instances from the service, ensuring order books reflect either live vendor data or consistent fallbacks. Spread settings and default baselines can be tuned per environment.

### Persistence & Caching

Location: `app/db/`, `app/repositories/`, `app/cache/`

- **Models** (`SQLModel`) store portfolios, positions, trades, executions, agent configs, vendor configs, analysis sessions, and run logs.
- **Alembic** powers schema migrations with async support (`alembic.ini`, `alembic/env.py`).
- **Repositories** implement a typed CRUD layer (e.g., `PortfolioRepository`, `TradeRepository`, `AnalysisSessionRepository`) with domain-specific queries.
- **Database Manager** handles engine initialisation, session lifecycle, and optional table creation for SQLite development use.
- **Redis Cache Service**: A high-level `CacheService` (`app/cache/cache_service.py`) exists, providing methods to cache market data, session data, and agent configurations in Redis.
- **Architectural Discrepancy**: The `MarketDataService` currently **does not** use the centralized `CacheService`. Instead, it relies on a simple instance-level dictionary (`_quote_cache`) for caching. This is a known architectural inconsistency; future work should integrate `MarketDataService` with `CacheService` to leverage distributed caching.

### Analysis Session Persistence & Event Streaming

Locations: `app/db/models/analysis_session.py`, `app/services/analysis_session.py`, `app/services/events.py`, `app/api/sessions.py`, `app/api/streams.py`

- **AnalysisSession Model** persists each run with ticker, status, trade date, selected analysts, and summary JSON blobs. Status transitions (`pending → running → completed/failed`) are timestamped for auditability.
- **SessionEventManager** maintains bounded in-memory buffers (`deque`) of timestamped events per session. Events are appended during active streams and remain queryable after completion. **Note: Event history is not persisted to the database**; only the final session summary is stored. This means detailed event logs are lost upon service restart.
- **REST Endpoints** – `/sessions` lists summaries, `/sessions/{id}` returns a summary plus buffered events, and `/sessions/{id}/events-history` exposes the same event history for REST consumers. Payloads align with the shared DTOs under `packages/shared/src/domain/session.ts`.
- **Realtime Delivery** – `/sessions/{id}/events` (SSE) and `/sessions/{id}/ws` (WebSocket) deliver live updates that mirror the buffered events. Streams are initialised by `TradingGraphService.ensure_session_stream`, and closing messages preserve event history.
- **Frontend Consumption** – The Control Center hydrates `TradingSession` views using `normalizeSessionSummary`, `normalizeSessionEventsHistory`, and `enrichSessionWithEvents` from the shared package, combining REST history with live SSE updates.

### Background Worker System (Streaming Infrastructure)

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

- **ExecutionService** transforms trader decisions into orders, enforcing pre-trade risk checks and updating persistence. Market prices flow through `MarketDataService` to maintain consistent book states.
- **PositionSizingService** supports multiple strategies (fixed dollar, fixed percentage, risk-based, volatility-weighted, fractional Kelly) with configurable caps.
- **RiskManagementService** computes diagnostics (VaR, exposure, max drawdown, Sharpe) and enforces constraints (position limits, stop-loss/take-profit rules).
- **BrokerAdapter** abstraction includes a `SimulatedBroker` for paper trading with commission/slippage modelling. The adapter now expects deterministic pricing from the Market Data Service rather than generating random prices, making fills reproducible across runs.
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
- **Session Detail Views**: The sessions route uses shared DTOs (`@tradingagents/shared/domain`) to hydrate persisted summaries, buffered events, and live SSE updates via the `useSessionStream` hook.
- **View Controls**: Time-range filters, overview vs. detailed tabs, dark-mode aware components built with shadcn/ui primitives.
- **Real-time Transport**: SSE/WebSocket hooks (`useRealtimePortfolio`, `useRealtimeSignals`, etc.) handle reconnection and status indicators.
- **Accessibility & Performance**: Keyboard navigation, ARIA labelling, responsive layout, virtualised lists, and Recharts for live visualisations.

Configuration is handled via `.env.local` (e.g., `NEXT_PUBLIC_API_URL`) or Compose environment variables during deployment.

## Data & Configuration Flow

1. **Environment variables** (see [docs/CONFIGURATION.md](./CONFIGURATION.md)) configure LLM providers, vendor routing, database targets, Redis, monitoring, and deployment-specific behaviour.
2. **LLM Provider Registry** supplies metadata and health checks to `AgentLLMService`, API routes, and the Control Center. Provider costs and capabilities originate from the registry to keep databases and UI aligned.
3. **Vendor and agent registries** load built-in plugins, discover third-party extensions, and persist configuration in the database or YAML/JSON files.
4. **LangGraph runs** pull data through vendor routers, maintain conversation state in vector memory, and propose trades.
5. **Market Data Service** supplies deterministic quotes to the broker adapter, pulling from vendors when possible and falling back to cached/baseline prices when necessary.
6. **Execution services** validate trades against risk constraints, trigger broker adapters, and persist results.
7. **Session persistence** stores analysis session metadata while SessionEventManager buffers events for later retrieval. REST endpoints expose summaries and event history, and SSE/WebSocket channels deliver live updates.
8. **Frontend dashboard** consumes shared DTOs to merge REST history and SSE streams, visualising activity in real time.

## Troubleshooting & Operational Notes

### LLM Provider Configuration

- Use `POST /llm-providers/validate-key` to verify API keys before saving configurations. The response includes a `valid` flag and diagnostic `detail` string when health checks fail.
- A `ProviderNotFoundError` or `ModelNotSupportedError` indicates an outdated provider/model combination; confirm against `GET /llm-providers/` and `GET /llm-providers/{provider}/models`.
- Missing environment variables surface as `APIKeyMissingError` exceptions. Ensure provider-specific keys (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) are present in runtime configuration.
- Disabled providers (e.g., removed from deployment via feature flags) still appear in the registry but health checks will fail. The frontend surfaces these failures using the shared DTOs so admins can remediate quickly.

### Market Data Fallback Behaviour

- Vendor routing failures trigger cached quote reuse. Check vendor logs and routing configuration via `/vendors/routing/config` when repeated fallbacks occur.
- If no prior quote is cached, MarketDataService derives a deterministic baseline informed by the ticker symbol. This keeps simulated fills stable across runs while clearly logging vendor failures.
- Tune `spread_bps`, `min_spread`, and `fallback_prices` via service configuration when operating in offline or limited-data environments.

### Session Event Buffers

- Buffered events are capped (default 100 per session) to prevent unbounded memory usage. Older events are discarded on overflow.
- `GET /sessions/{id}/events-history` mirrors the SSE payloads and should be used by automation that cannot maintain long-lived streams.
- The shared TypeScript DTOs provide guards and normalisers to safely consume events in the frontend and custom clients.

## Architecture Considerations

This section highlights known limitations and architectural trade-offs in the current implementation.

### Authentication Middleware

- **Logic vs. Integration**: The core logic for JWT and API Key handling is fully implemented in `app/security/auth.py`. However, the `AuthMiddleware` in `app/middleware/auth.py` currently acts only as a request logger and **does not enforce authentication**. To secure the API, this middleware must be updated to call the verification functions from `auth.py` and reject unauthorized requests.

### In-Memory State Management

Several critical components store their state in the service's memory, which introduces a single point of failure and data loss risk upon service restart.
- **Auto-Trading Tasks**: The `AutoTradingOrchestrator` manages continuous trading tasks (e.g., which portfolios are running, their intervals, and active task handles) in instance variables. If the application restarts, these tasks are not automatically recovered.
- **Event History**: As noted in the "Analysis Session" section, the `SessionEventManager` holds detailed event histories in memory. While performant, this data is ephemeral.
- **Market Data Cache**: The `MarketDataService`'s quote cache is instance-local, meaning a cold start will result in increased latency as the cache needs to be repopulated.

Future work should consider moving this state to a persistent, distributed store like Redis or a dedicated database table to improve fault tolerance and scalability.

## Related Resources

- [API Reference](./API.md) – Complete endpoint catalogue with payloads and examples.
- [Configuration Guide](./CONFIGURATION.md) – Environment variables, vendor routing, agent overrides.
- [Deployment Guide](./DEPLOYMENT.md) – Docker stacks, production hardening, scaling, and maintenance.
- [Shared Session DTOs](../packages/shared/src/domain/session.ts) – TypeScript contracts and helpers used by the Control Center and third-party clients.
- [Operations Guides](./operations/README.md) – Runtime playbooks and Kubernetes example manifests.

For detailed subsystem code, explore the paths highlighted above within `packages/backend` and `packages/frontend`.
