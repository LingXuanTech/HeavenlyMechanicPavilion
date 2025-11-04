# Backend API Reference

The FastAPI backend exposes REST, SSE, and WebSocket interfaces for orchestrating TradingAgents runs, administering plugins, streaming telemetry, and monitoring system health. This reference summarises the primary endpoints and includes example payloads aligned with the shared DTOs consumed by the Control Center and external clients.

## Table of Contents

1. [Conventions](#conventions)
2. [Health & Metadata](#health--metadata)
3. [LLM Provider Registry](#llm-provider-registry)
4. [Session Management](#session-management)
5. [Streaming Endpoints](#streaming-endpoints)
6. [Vendor Plugin Administration](#vendor-plugin-administration)
7. [Agent Plugin Administration](#agent-plugin-administration)
8. [Configuration Management](#configuration-management)
9. [Monitoring & Metrics](#monitoring--metrics)
10. [Troubleshooting & Tips](#troubleshooting--tips)

## Conventions

- Base URL: `http://localhost:8000`
- Authentication: Not enabled by default (add via FastAPI dependencies or reverse proxy in production)
- Content type: JSON unless noted
- All endpoints support `?limit=` and `?offset=` pagination where indicated
- SSE endpoints use the `text/event-stream` media type
- Shared DTOs live in `packages/shared/src/domain/session.ts` and `packages/shared/src/clients` for consumers that want type-safe integrations

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

## LLM Provider Registry

The canonical provider registry is exposed for UI and automation. Metadata originates from `tradingagents.llm_providers.registry` and is shared with the frontend via DTOs.

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/llm-providers/` | List supported providers and their models with pricing/capabilities |
| `GET` | `/llm-providers/{provider}/models` | Retrieve model metadata for a provider (`openai`, `claude`, `deepseek`, `grok`) |
| `POST` | `/llm-providers/validate-key` | Perform a live health check using the supplied API key |

### Validate an API Key

```bash
curl -X POST http://localhost:8000/llm-providers/validate-key \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "api_key": "sk-...",
    "model_name": "gpt-4o-mini"
  }'
```

If no `model_name` is supplied the registry default is used. Example response:

```json
{
  "provider": "openai",
  "model_name": "gpt-4o-mini",
  "valid": true,
  "detail": null
}
```

Failed health checks return `valid: false` with diagnostic information in `detail` (e.g., missing API keys, disabled providers, or upstream errors).

## Session Management

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/sessions` | Start a new TradingAgents run. Returns a `session_id` and SSE endpoint. |
| `GET` | `/sessions` | List persisted analysis sessions with optional `status`/`ticker` filters. |
| `GET` | `/sessions/{session_id}` | Retrieve a persisted session summary plus buffered events. |
| `GET` | `/sessions/{session_id}/events-history` | Fetch recent event history (same payload shape as SSE stream) after a run completes. |
| `GET` | `/sessions/{session_id}/events` | Server-Sent Events stream for live lifecycle updates. |
| `WS` | `/sessions/{session_id}/ws` | WebSocket stream mirroring the SSE payload. |

### Start a Session

```bash
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "ticker": "NVDA",
    "trade_date": "2024-05-10",
    "selected_analysts": ["technical", "news"]
  }'
```

Response:

```json
{
  "session_id": "8c98f5b4-7f0d-4fb1-9b7b-19ad2b2795be",
  "stream_endpoint": "/sessions/8c98f5b4-7f0d-4fb1-9b7b-19ad2b2795be/events"
}
```

### List Sessions

```bash
curl "http://localhost:8000/sessions?limit=20&status=completed"
```

Example response (`SessionListResponse` / shared `SessionSummary` DTO):

```json
{
  "sessions": [
    {
      "id": "8c98f5b4-7f0d-4fb1-9b7b-19ad2b2795be",
      "ticker": "NVDA",
      "asOfDate": "2024-05-10",
      "status": "completed",
      "createdAt": "2024-05-10T14:21:03.814237",
      "updatedAt": "2024-05-10T14:23:44.019523"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 20
}
```

### Session Detail with Buffered Events

```bash
curl http://localhost:8000/sessions/8c98f5b4-7f0d-4fb1-9b7b-19ad2b2795be
```

Example response (`SessionDetailResponse`):

```json
{
  "session": {
    "id": "8c98f5b4-7f0d-4fb1-9b7b-19ad2b2795be",
    "ticker": "NVDA",
    "asOfDate": "2024-05-10",
    "status": "completed",
    "createdAt": "2024-05-10T14:21:03.814237",
    "updatedAt": "2024-05-10T14:23:44.019523"
  },
  "events": [
    {
      "timestamp": "2024-05-10T14:21:05.011924",
      "event": {
        "type": "status",
        "message": "session_started"
      }
    },
    {
      "timestamp": "2024-05-10T14:23:44.018912",
      "event": {
        "type": "decision",
        "message": "buy",
        "payload": {
          "ticker": "NVDA",
          "conviction": 0.78
        }
      }
    }
  ]
}
```

### Event History Endpoint

`GET /sessions/{session_id}/events-history` returns the same buffered events with a `count` field:

```json
{
  "session_id": "8c98f5b4-7f0d-4fb1-9b7b-19ad2b2795be",
  "events": [
    {
      "timestamp": "2024-05-10T14:21:05.011924",
      "event": {
        "type": "status",
        "message": "session_started"
      }
    }
  ],
  "count": 1
}
```

### Stream Session Events (SSE / WebSocket)

```bash
# SSE
tail -f <(curl -N http://localhost:8000/sessions/8c98f5b4-7f0d-4fb1-9b7b-19ad2b2795be/events)

# WebSocket (e.g., using websocat)
websocat ws://localhost:8000/sessions/8c98f5b4-7f0d-4fb1-9b7b-19ad2b2795be/ws
```

Each SSE message contains the serialised `SessionEvent` schema:

```json
{
  "type": "status",
  "message": "analyst_panel_complete",
  "payload": {
    "analysts": ["fundamental", "news"],
    "elapsed_seconds": 42.7
  }
}
```

Buffered histories persist after the SSE stream closes, enabling REST clients to reconcile runs without maintaining long-lived connections.

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

## Troubleshooting & Tips

- **Provider validation failures** – Inspect the `detail` field returned by `POST /llm-providers/validate-key`. Missing API keys surface as `APIKeyMissingError`; disabled providers or incorrect models map to `ProviderNotFoundError`/`ModelNotSupportedError`.
- **Fallback market data** – If REST responses or SSE payloads include deterministic baseline prices, review `/vendors/routing/config` and vendor logs. The Market Data Service reuses the last good quote or derives a symbol-based baseline when vendors are unreachable.
- **Session event gaps** – The bounded event buffer stores the most recent events (default 100). If expected history is missing, poll `/sessions/{id}/events-history` immediately after completion or increase the buffer size via `SessionEventManager` configuration.

Need a command catalogue for deployment? See [docs/DEPLOYMENT.md](./DEPLOYMENT.md). For system architecture context, refer to [docs/ARCHITECTURE.md](./ARCHITECTURE.md).
