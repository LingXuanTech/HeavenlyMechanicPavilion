# Backend API Reference

The FastAPI backend exposes REST, SSE, and WebSocket interfaces for orchestrating TradingAgents runs, administering plugins, streaming telemetry, and monitoring system health. This reference summarises the primary endpoints and includes example payloads.

## Table of Contents

1. [Conventions](#conventions)
2. [Health & Metadata](#health--metadata)
3. [Session Management](#session-management)
4. [Streaming Endpoints](#streaming-endpoints)
5. [Vendor Plugin Administration](#vendor-plugin-administration)
6. [Agent Plugin Administration](#agent-plugin-administration)
7. [Configuration Management](#configuration-management)
8. [Monitoring & Metrics](#monitoring--metrics)

## Conventions

- Base URL: `http://localhost:8000`
- Authentication: Not enabled by default (add via FastAPI dependencies or reverse proxy in production)
- Content type: JSON unless noted
- All endpoints support `?limit=` and `?offset=` pagination where indicated
- SSE endpoints use the `text/event-stream` media type

Swagger UI is available at [http://localhost:8000/docs](http://localhost:8000/docs), and the OpenAPI schema at [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json).

## Health & Metadata

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/health` | Lightweight service heartbeat |
| `GET` | `/sessions/config` | Active TradingAgents configuration (LLM, vendors, results dir, etc.) |

Example response for `/health`:

```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "disabled"
}
```

## Session Management

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/sessions` | Start a new TradingAgents run. Returns a `session_id` and initial status. |
| `GET` | `/sessions/{session_id}` | Retrieve session status and final decision. |
| `GET` | `/sessions/{session_id}/events` | Server-Sent Events (SSE) stream for run lifecycle updates. |
| `WS` | `/sessions/{session_id}/ws` | WebSocket stream mirroring the SSE payload. |

### Start a Session

```bash
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "NVDA",
    "date": "2024-05-10",
    "config": {
      "deep_think_llm": "o4-mini",
      "quick_think_llm": "gpt-4o-mini",
      "max_debate_rounds": 1
    }
  }'
```

### Stream Session Events

```bash
# SSE
curl -N http://localhost:8000/sessions/<SESSION_ID>/events

# WebSocket (e.g., using websocat)
websocat ws://localhost:8000/sessions/<SESSION_ID>/ws
```

Each event carries a JSON payload describing agent progress, research outputs, trade decisions, and risk checks.

## Streaming Endpoints

Real-time data (market data, news, analytics) is delivered via dedicated streaming APIs once background workers and Redis are enabled.

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/streaming/subscribe/sse` | Subscribe to one or more channels via SSE. |
| `WS` | `/streaming/ws` | WebSocket stream using query params (`channels`, `symbols`, `data_types`). |
| `GET` | `/streaming/channels` | List available Redis channels. |
| `GET` | `/streaming/latest/{channel}` | Retrieve the most recent cached message for a channel. |

Payload example for SSE subscription:

```json
{
  "channels": ["stream:market_data:AAPL", "stream:news:AAPL"],
  "data_types": ["market_data", "news"],
  "symbols": ["AAPL"]
}
```

### Streaming Configuration API

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/streaming/config/instruments` | List configured instruments. |
| `POST` | `/streaming/config/instruments` | Add or update an instrument. |
| `GET` | `/streaming/config/instruments/{symbol}` | Retrieve instrument config. |
| `DELETE` | `/streaming/config/instruments/{symbol}` | Remove an instrument. |
| `GET` | `/streaming/config/cadences/{data_type}` | View polling cadence. |
| `PUT` | `/streaming/config/cadences/{data_type}` | Update cadence (interval, retries, fallback). |
| `GET` | `/streaming/config/workers` | List worker status. |
| `POST` | `/streaming/config/workers/{worker_id}/start` | Start a worker. |
| `POST` | `/streaming/config/workers/{worker_id}/stop` | Stop a worker. |
| `POST` | `/streaming/config/workers/start-all` | Start all workers. |
| `POST` | `/streaming/config/workers/stop-all` | Stop all workers. |
| `GET` | `/streaming/config/telemetry/{data_type}` | Fetch telemetry reports for a data type. |

Cadence update example:

```bash
curl -X PUT http://localhost:8000/streaming/config/cadences/market_data \
  -H "Content-Type: application/json" \
  -d '{
    "interval_seconds": 30,
    "retry_attempts": 5,
    "retry_backoff_multiplier": 2.0,
    "enabled": true,
    "vendor_fallback": true
  }'
```

## Vendor Plugin Administration

Manage data vendor plugins, routing, and configuration.

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/vendors/` | List registered vendor plugins and capabilities. |
| `GET` | `/vendors/{name}` | Inspect plugin metadata. |
| `GET` | `/vendors/{name}/config` | Retrieve vendor configuration (rate limits, API keys, flags). |
| `PUT` | `/vendors/{name}/config` | Update vendor configuration. |
| `GET` | `/vendors/capabilities/{capability}` | Filter plugins by capability (e.g., `stock_data`, `news`). |
| `GET` | `/vendors/routing/config` | View routing rules per data method. |
| `GET` | `/vendors/routing/config/{method}` | View routing configuration for a specific method. |
| `PUT` | `/vendors/routing/config` | Update routing order for a method. |
| `POST` | `/vendors/config/reload` | Hot-reload configuration from YAML/JSON files. |

Routing update example:

```bash
curl -X PUT http://localhost:8000/vendors/routing/config \
  -H "Content-Type: application/json" \
  -d '{
    "method": "get_stock_data",
    "vendors": ["alpha_vantage", "yfinance", "local"]
  }'
```

## Agent Plugin Administration

Agent definitions (metadata, prompts, slot assignments) are persisted and configurable at runtime.

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/agents/` | List agent configurations (supports filtering/pagination). |
| `POST` | `/agents/` | Create a new agent configuration. |
| `GET` | `/agents/{agent_id}` | Fetch an agent configuration. |
| `PUT` | `/agents/{agent_id}` | Update an agent configuration. |
| `DELETE` | `/agents/{agent_id}` | Remove a custom agent. |
| `POST` | `/agents/reload` | Reload agent registry and refresh workflow slots. |

Payload example for creating a custom analyst:

```bash
curl -X POST http://localhost:8000/agents/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_custom_analyst",
    "role": "analyst",
    "capabilities": ["market_analysis"],
    "llm_type": "quick",
    "slot_name": "custom",
    "required_tools": ["get_stock_data"],
    "prompt_template": "You are a specialised analyst...",
    "is_active": true,
    "is_reserved": false
  }'
```

## Configuration Management

Besides environment variables, certain settings (e.g., vendor routing) can be manipulated via the APIs above. Additional helper endpoints include:

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/config/defaults` | Inspect default TradingAgents configuration (if exposed). |
| `GET` | `/sessions/config` | Active runtime configuration, including overrides from `.env`. |

Refer to [docs/CONFIGURATION.md](./CONFIGURATION.md) for comprehensive environment variables and configuration files (`vendor_config.example.yaml`, etc.).

## Monitoring & Metrics

System health, telemetry, and alerting endpoints are exposed under `/monitoring`.

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/monitoring/health` | Aggregated system health (database, Redis, vendors, workers). |
| `GET` | `/monitoring/metrics` | Prometheus-compatible metrics. |
| `GET` | `/monitoring/vendors` | Vendor-specific status and error rates. |
| `GET` | `/monitoring/workers` | Worker status, throughput, and watchdog info. |
| `GET` | `/monitoring/queues` | Queue backlog metrics. |
| `GET` | `/monitoring/database` | Database latency and status metrics. |
| `GET` | `/monitoring/redis` | Redis health (if enabled). |
| `GET` | `/monitoring/uptime` | Service uptime measurements. |
| `GET` | `/monitoring/alerts/history?limit=` | Alert history feed. |
| `POST` | `/monitoring/alerts/test` | Trigger a test alert (email/webhook). |

Prometheus scrape example:

```yaml
scrape_configs:
  - job_name: 'tradingagents'
    static_configs:
      - targets: ['backend:8000']
```

> The frontend dashboard also surfaces these metrics at `/monitoring` for quick visual inspection.

Need a command catalogue for deployment? See [docs/DEPLOYMENT.md](./DEPLOYMENT.md). For lower-level subsystem details, refer to [docs/ARCHITECTURE.md](./ARCHITECTURE.md).
