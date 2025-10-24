# Monitoring, Alerting, and System Health

This document describes the monitoring, alerting, and system health features implemented in the TradingAgents backend.

## Overview

The monitoring system provides comprehensive health checks, metrics collection, alerting capabilities, and background task watchdogs to ensure system reliability and observability.

## Features

### 1. Health & Metrics Endpoints

#### `/monitoring/health`
Comprehensive health check endpoint that returns:
- Overall system status (healthy, degraded, error)
- Database health and latency
- Redis health and memory usage (if enabled)
- Vendor plugin availability and error rates
- Background worker status

**Example Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "uptime_seconds": 86400,
  "services": {
    "database": {
      "status": "healthy",
      "latency_ms": 5.23,
      "message": "Database is accessible"
    },
    "redis": {
      "status": "healthy",
      "enabled": true,
      "latency_ms": 2.15,
      "connected_clients": 3,
      "used_memory_mb": 12.5
    },
    "vendors": {
      "status": "healthy",
      "total_vendors": 5,
      "healthy_vendors": 5,
      "vendors": {...}
    },
    "workers": {
      "status": "healthy",
      "total_workers": 2,
      "running_workers": 2,
      "workers": {...}
    }
  }
}
```

#### `/monitoring/metrics`
Prometheus-compatible metrics endpoint for integration with monitoring tools like Prometheus, Grafana, etc.

**Metrics Exposed:**
- `tradingagents_http_requests_total` - Total HTTP requests by method, endpoint, and status
- `tradingagents_http_request_duration_seconds` - Request duration histogram
- `tradingagents_db_latency_seconds` - Database query latency
- `tradingagents_redis_latency_seconds` - Redis operation latency
- `tradingagents_vendor_requests_total` - Vendor API request counts
- `tradingagents_vendor_errors_total` - Vendor API error counts
- `tradingagents_worker_tasks_active` - Active worker task counts
- `tradingagents_queue_size` - Queue backlog sizes
- `tradingagents_service_up` - Service availability (1 = up, 0 = down)

#### `/monitoring/vendors`
Detailed vendor plugin status including:
- Request counts
- Error rates
- Rate limits
- Provider information

#### `/monitoring/workers`
Background worker status including:
- Running/stopped status
- Tasks processed
- Current active tasks
- Watchdog monitoring status

#### `/monitoring/queues`
Queue backlog metrics showing:
- Queue sizes
- Total items across all queues
- Per-queue statistics

#### `/monitoring/database`
Database-specific health and metrics

#### `/monitoring/redis`
Redis-specific health and metrics (if enabled)

#### `/monitoring/uptime`
System uptime information

#### `/monitoring/alerts/history`
Recent alert history with optional limit parameter

#### `/monitoring/alerts/test` (POST)
Send a test alert to verify alerting configuration

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Monitoring configuration
MONITORING_ENABLED=true
METRICS_ENABLED=true

# Alerting configuration
ALERTING_ENABLED=false
ALERT_EMAIL_ENABLED=false
ALERT_EMAIL_TO=alerts@example.com
ALERT_EMAIL_FROM=tradingagents@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
SMTP_USE_TLS=true

ALERT_WEBHOOK_ENABLED=false
ALERT_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
# ALERT_WEBHOOK_HEADERS={"Authorization": "Bearer token"}

# Worker watchdog configuration
WATCHDOG_ENABLED=true
WATCHDOG_CHECK_INTERVAL=60
WATCHDOG_TASK_TIMEOUT=300
```

### Alerting Channels

#### Email Alerts
Configure SMTP settings to receive email notifications for critical events.

**Supported providers:**
- Gmail (use app passwords)
- SendGrid
- AWS SES
- Any SMTP-compatible service

#### Webhook Alerts
Send alerts to webhook endpoints (Slack, Discord, Microsoft Teams, custom endpoints).

**Slack Example:**
1. Create a Slack webhook URL
2. Set `ALERT_WEBHOOK_URL` to your webhook URL
3. Enable webhook alerts: `ALERT_WEBHOOK_ENABLED=true`

**Custom Headers:**
For services requiring authentication:
```bash
ALERT_WEBHOOK_HEADERS='{"Authorization": "Bearer your_token"}'
```

### Alert Levels

- `INFO` - Informational messages
- `WARNING` - Warning conditions
- `ERROR` - Error conditions requiring attention
- `CRITICAL` - Critical failures requiring immediate action

## Worker Watchdog

The watchdog monitors background workers and triggers alerts for:

1. **Worker Failures**: When a worker stops unexpectedly
2. **Stuck Tasks**: When tasks exceed the configured timeout
3. **Health Issues**: When workers become unresponsive

**Configuration:**
- `WATCHDOG_ENABLED` - Enable/disable watchdog (default: true)
- `WATCHDOG_CHECK_INTERVAL` - How often to check workers in seconds (default: 60)
- `WATCHDOG_TASK_TIMEOUT` - Maximum task duration before alerting in seconds (default: 300)

## Frontend Dashboard

Access the monitoring dashboard at `/monitoring` in the frontend application.

**Features:**
- Real-time system health status
- Service uptime visualization
- Vendor error rate tracking
- Queue backlog monitoring
- Recent alerts display
- Auto-refresh capability (every 10 seconds)

## Integration with Prometheus

1. **Add Prometheus scrape configuration:**
```yaml
scrape_configs:
  - job_name: 'tradingagents'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/monitoring/metrics'
```

2. **Create Grafana Dashboard:**
   - Import the metrics endpoint
   - Create panels for key metrics
   - Set up alerting rules

## Programmatic Usage

### Recording Vendor Metrics

```python
from app.services.monitoring import get_monitoring_service

monitoring = get_monitoring_service()

# Record successful vendor request
monitoring.record_vendor_request("yfinance", success=True)

# Record failed vendor request
monitoring.record_vendor_request("alpha_vantage", success=False, error_type="rate_limit")
```

### Sending Alerts

```python
from app.services.alerting import get_alerting_service, AlertLevel

alerting = get_alerting_service()

await alerting.send_alert(
    title="High Error Rate Detected",
    message="Vendor 'yfinance' error rate exceeded 50%",
    level=AlertLevel.ERROR,
    details={
        "vendor": "yfinance",
        "error_rate": 52.3,
        "total_requests": 100,
    }
)
```

### Recording Worker Activity

```python
from app.workers.watchdog import get_watchdog

watchdog = get_watchdog()
watchdog.record_worker_activity("data_worker")
```

## Metrics Middleware

The `MetricsMiddleware` automatically tracks:
- HTTP request counts
- Request durations
- Status codes
- Endpoint patterns

Enabled by default when `METRICS_ENABLED=true`.

## Best Practices

1. **Enable Monitoring in Production**: Always enable monitoring and metrics in production environments
2. **Configure Alerts**: Set up at least one alerting channel (email or webhook)
3. **Monitor Key Metrics**: Focus on database latency, vendor error rates, and queue backlogs
4. **Set Up Grafana**: Use Grafana for advanced visualization and alerting
5. **Regular Health Checks**: Implement external health checks that ping `/monitoring/health`
6. **Alert Fatigue**: Configure appropriate thresholds to avoid too many alerts
7. **Document Runbooks**: Create runbooks for common alert scenarios

## Troubleshooting

### Metrics Not Appearing
- Verify `METRICS_ENABLED=true`
- Check that Prometheus client is installed: `pip install prometheus-client`
- Ensure the metrics endpoint is accessible: `curl http://localhost:8000/monitoring/metrics`

### Alerts Not Sending
- Check alerting is enabled: `ALERTING_ENABLED=true`
- Verify channel configuration (SMTP or webhook)
- Test with `/monitoring/alerts/test` endpoint
- Check application logs for error messages

### Worker Watchdog Not Working
- Verify `WATCHDOG_ENABLED=true`
- Ensure workers are started: `AUTO_START_WORKERS=true` or start manually
- Check Redis is enabled and accessible (required for workers)
- Review watchdog logs for errors

### High Database Latency
- Check database connection pool settings
- Review slow query logs
- Consider adding indexes
- Check database server resources

### High Error Rates
- Review vendor API quotas and rate limits
- Check network connectivity
- Verify API keys are valid
- Review vendor-specific error logs

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FastAPI Application                   │
├─────────────────────────────────────────────────────────┤
│  MetricsMiddleware → Records HTTP metrics               │
├─────────────────────────────────────────────────────────┤
│  MonitoringService                                       │
│  ├─ Health Checks (DB, Redis, Vendors, Workers)        │
│  ├─ Metrics Collection (Prometheus)                     │
│  └─ Status Aggregation                                  │
├─────────────────────────────────────────────────────────┤
│  AlertingService                                         │
│  ├─ Email Alerts (SMTP)                                 │
│  ├─ Webhook Alerts (HTTP POST)                          │
│  └─ Alert History                                       │
├─────────────────────────────────────────────────────────┤
│  WorkerWatchdog                                          │
│  ├─ Worker Health Monitoring                            │
│  ├─ Task Timeout Detection                              │
│  └─ Automatic Alerting                                  │
└─────────────────────────────────────────────────────────┘
```

## API Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/monitoring/health` | GET | Comprehensive health status |
| `/monitoring/metrics` | GET | Prometheus metrics |
| `/monitoring/vendors` | GET | Vendor status and error rates |
| `/monitoring/workers` | GET | Worker status and watchdog info |
| `/monitoring/queues` | GET | Queue backlog metrics |
| `/monitoring/database` | GET | Database health |
| `/monitoring/redis` | GET | Redis health |
| `/monitoring/uptime` | GET | System uptime |
| `/monitoring/alerts/history` | GET | Recent alerts |
| `/monitoring/alerts/test` | POST | Send test alert |

## Future Enhancements

- [ ] Distributed tracing with OpenTelemetry
- [ ] Custom metric dashboards
- [ ] Alert rule engine
- [ ] SLA tracking
- [ ] Performance profiling
- [ ] Log aggregation
- [ ] Anomaly detection
