# Configuration Guide

TradingAgents is flexible by design: you can tailor LLM providers, agent behaviour, vendor routing, persistence targets, and monitoring options through environment variables and configuration files. This guide consolidates the settings you can tweak.

## Table of Contents

1. [Overview](#overview)
2. [Environment Variables](#environment-variables)
   - [API Keys & Providers](#api-keys--providers)
   - [TradingAgents Behaviour](#tradingagents-behaviour)
   - [Database & Persistence](#database--persistence)
   - [Redis & Streaming](#redis--streaming)
   - [Monitoring & Alerting](#monitoring--alerting)
3. [Default Configuration Overrides](#default-configuration-overrides)
4. [Vendor Routing Configuration](#vendor-routing-configuration)
5. [Agent Configuration](#agent-configuration)
6. [Environment Files](#environment-files)
7. [Troubleshooting Tips](#troubleshooting-tips)

## Overview

Configuration can be supplied via:

- `.env` files loaded by `pydantic-settings`
- Environment variables (Docker, shell exports, CI secrets)
- JSON/YAML files consumed by vendor and streaming config managers
- REST endpoints for runtime adjustments (see [docs/API.md](./API.md))

## Environment Variables

> Copy `.env.example` or `.env.docker` as a starting point and remove any secrets before committing.

### API Keys & Providers

| Variable | Description |
| --- | --- |
| `OPENAI_API_KEY` | Required for default LLM and tool usage. |
| `ALPHA_VANTAGE_API_KEY` | Default market/fundamental/news data provider. |
| `ANTHROPIC_API_KEY` | Optional provider for Claude-based agents. |
| `GOOGLE_API_KEY` | Optional provider for Gemini models or Google News. |
| `FINNHUB_API_KEY`, `REDDIT_CLIENT_ID`, etc. | Optional vendor credentials used by the local plugin. |

### TradingAgents Behaviour

| Variable | Default | Description |
| --- | --- | --- |
| `TRADINGAGENTS_LLM_PROVIDER` | `openai` | Default provider for deep/quick think LLMs. |
| `TRADINGAGENTS_DEEP_THINK_LLM` | `o4-mini` | Model used for complex reasoning nodes. |
| `TRADINGAGENTS_QUICK_THINK_LLM` | `gpt-4o-mini` | Model for lighter-weight tasks. |
| `TRADINGAGENTS_MAX_DEBATE_ROUNDS` | `1` | Research debate iterations for bullish/bearish agents. |
| `TRADINGAGENTS_RESULTS_DIR` | `./results` | Output directory for reports and artefacts. |
| `AUTO_START_WORKERS` | `false` | Automatically boot background workers when the API starts. |
| `STREAMING_ENABLED` | `false` | Toggle for streaming infrastructure (requires Redis). |

### Database & Persistence

| Variable | Default | Description |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite+aiosqlite:///./tradingagents.db` | Connection string for SQLModel/SQLAlchemy. Use `postgresql+asyncpg://user:password@host/db` in production. |
| `DATABASE_ECHO` | `false` | Echo SQL statements (useful for debugging). |
| `ALEMBIC_CONFIG` | (derived) | Path to Alembic configuration if you relocate files. |

### Redis & Streaming

| Variable | Default | Description |
| --- | --- | --- |
| `REDIS_ENABLED` | `false` | Enables Redis usage for caching and streaming. |
| `REDIS_HOST` | `localhost` | Redis host. |
| `REDIS_PORT` | `6379` | Redis port. |
| `REDIS_DB` | `0` | Redis logical database. |
| `REDIS_PASSWORD` | (empty) | Optional password. |
| `STREAMING_ENABLED` | `false` | Master switch for streaming endpoints/workers. |
| `STREAMING_DEFAULT_INTERVAL` | `60` | Fallback polling cadence (seconds). |

### Monitoring & Alerting

| Variable | Default | Description |
| --- | --- | --- |
| `MONITORING_ENABLED` | `true` | Expose `/monitoring/*` endpoints and internal health checks. |
| `METRICS_ENABLED` | `true` | Serve Prometheus metrics at `/monitoring/metrics`. |
| `ALERTING_ENABLED` | `false` | Enables alert dispatchers. |
| `ALERT_EMAIL_ENABLED` | `false` | Send alert emails via SMTP. |
| `ALERT_EMAIL_TO` |  | Recipient(s). |
| `ALERT_EMAIL_FROM` |  | Sender identity. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_USE_TLS` |  | SMTP configuration for email alerts. |
| `ALERT_WEBHOOK_ENABLED` | `false` | Send alerts to arbitrary webhooks (Slack, Discord, Teams). |
| `ALERT_WEBHOOK_URL` |  | Destination webhook URL. |
| `ALERT_WEBHOOK_HEADERS` |  | Optional JSON string of headers (e.g., tokens). |
| `WATCHDOG_ENABLED` | `true` | Monitor worker liveness. |
| `WATCHDOG_CHECK_INTERVAL` | `60` | Watchdog poll interval (seconds). |
| `WATCHDOG_TASK_TIMEOUT` | `300` | Maximum task duration before alerting (seconds). |

### Error Tracking & Resilience

| Variable | Default | Description |
| --- | --- | --- |
| `ENVIRONMENT` | `development` | High-level environment label surfaced in logs and Sentry. |
| `ERROR_TRACKING_ENABLED` | `false` | Toggle Sentry error capture and distributed tracing. |
| `SENTRY_DSN` |  | Sentry DSN for the project. |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.0` | Fraction of requests to capture for tracing. |
| `SENTRY_PROFILES_SAMPLE_RATE` | `0.0` | Fraction of requests to sample for profiling. |
| `RETRY_DEFAULT_ATTEMPTS` | `3` | Default retry attempts for vendor/API calls. |
| `RETRY_DEFAULT_BACKOFF_SECONDS` | `0.5` | Base delay (seconds) for exponential backoff. |
| `RETRY_MAX_BACKOFF_SECONDS` | `30.0` | Ceiling for backoff delays. |
| `CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `5` | Consecutive failures before a vendor circuit opens. |
| `CIRCUIT_BREAKER_RECOVERY_SECONDS` | `60` | Cooldown period before half-open retries. |
| `CIRCUIT_BREAKER_HALF_OPEN_SUCCESSES` | `1` | Successful calls required to fully close the breaker. |

## Default Configuration Overrides

The Python package bundles a `DEFAULT_CONFIG` under `tradingagents/default_config.py`. You can clone and mutate it to experiment with model choices, debate settings, or vendor preferences:

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

def custom_graph():
    config = DEFAULT_CONFIG.copy()
    config["deep_think_llm"] = "gpt-4.1-nano"
    config["quick_think_llm"] = "gpt-4.1-nano"
    config["max_debate_rounds"] = 2
    config["data_vendors"] = {
        "core_stock_apis": "yfinance",
        "technical_indicators": "yfinance",
        "fundamental_data": "alpha_vantage",
        "news_data": "openai"
    }

    graph = TradingAgentsGraph(debug=True, config=config)
    return graph
```

CLI commands and REST payloads accept a `config` object that mirrors these fields, enabling ad-hoc overrides without editing source files.

## Vendor Routing Configuration

Vendor routing lives outside code so you can adapt quickly to rate limits or vendor availability.

1. Copy `packages/backend/vendor_config.example.yaml` (or `.json`) to a writable location.
2. Adjust vendor options (API keys, rate limits, enable flags) and routing priorities:

```yaml
vendors:
  alpha_vantage:
    api_key_ref: "ALPHA_VANTAGE_API_KEY"
    rate_limit_per_minute: 60
    enabled: true

routing:
  get_stock_data:
    - alpha_vantage
    - yfinance
    - local
```

3. Point the config manager to your file via environment variable or programmatically:

```python
from pathlib import Path
from tradingagents.plugins.config_manager import get_config_manager

config_manager = get_config_manager(config_file=Path("vendor_config.yaml"))
```

4. Use the vendor admin API to inspect or tweak configurations at runtime (`PUT /vendors/{name}/config`, `POST /vendors/config/reload`).

## Agent Configuration

Agent metadata (prompts, required tools, slots) can be stored in the database and edited via API:

```bash
curl -X POST http://localhost:8000/agents/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_custom_analyst",
    "role": "analyst",
    "slot_name": "custom",
    "capabilities": ["market_analysis"],
    "prompt_template": "You are a specialised analyst...",
    "llm_type": "quick",
    "is_active": true
  }'
```

- Reserved slots guarantee core workflow coverage; custom agents can be toggled on/off or slotted into analyst categories.
- `POST /agents/reload` refreshes the registry without restarting the service.

## Environment Files

Templates:

- `.env.example` – base template for local development.
- `.env.docker` – extended template for Docker Compose deployments (includes service ports, Redis, Postgres).
- `secrets.example.yml` – optional Docker/Kubernetes secrets mapping.

Never commit filled `.env` files; rely on `.gitignore` to keep them out of version control.

## Error Handling & Observability

- All REST responses follow the schema `{"error": {"code": ..., "message": ...}, "correlation_id": ...}`. The middleware automatically injects an `X-Correlation-ID` response header so logs and clients can trace requests across systems.
- Raise exceptions from `app.core.errors` in services and vendor adapters instead of `HTTPException`; the middleware maps them to status codes and error codes while logging structured context.
- External calls should use the `execute_with_retry` helper and share circuit breakers via `CircuitBreaker` to prevent cascading vendor failures. Defaults can be tuned with the resilience environment variables above.
- Enable Sentry by providing `ERROR_TRACKING_ENABLED=true` and a `SENTRY_DSN`. When active, unhandled exceptions are captured alongside correlation IDs, traces, and release metadata.

## Troubleshooting Tips

- **Configuration not applying?** Use `GET /sessions/config` to inspect the effective runtime configuration and ensure overrides are loaded.
- **Vendor errors?** Check `/vendors/`, `/vendors/{name}/config`, and `/monitoring/vendors` for availability and rate limits.
- **Streaming issues?** Verify `REDIS_ENABLED=true`, Redis connectivity, and worker status via `/streaming/config/workers`.
- **Alerting not triggering?** Use `POST /monitoring/alerts/test` after enabling the relevant email/webhook settings.

For additional operational context (deployment, scaling, monitoring), read [docs/DEPLOYMENT.md](./DEPLOYMENT.md) and [docs/ARCHITECTURE.md](./ARCHITECTURE.md).
