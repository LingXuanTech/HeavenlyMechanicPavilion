# Real-Time Data Streaming Infrastructure

This document describes the real-time data ingestion and streaming infrastructure for the TradingAgents platform.

## Overview

The streaming infrastructure provides:

1. **Background Workers** - Poll market data, news, and analytics from vendor plugins
2. **Redis Pub/Sub** - Cache snapshots/deltas and emit structured messages
3. **FastAPI SSE/WebSocket** - Real-time streaming endpoints for clients
4. **Resilience Features** - Retry logic, vendor fallback, and telemetry
5. **Configuration API** - Manage instruments and refresh cadences

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Data Workers   │────▶│  Redis Pub/Sub  │────▶│  SSE/WebSocket  │
│  (Background)   │     │  (Channels)     │     │  (Clients)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                                               │
        ▼                                               ▼
┌─────────────────┐                           ┌─────────────────┐
│ Vendor Plugins  │                           │   Web Clients   │
│ (yfinance, etc) │                           │   (Browser)     │
└─────────────────┘                           └─────────────────┘
```

## Components

### 1. Data Workers (`app/workers/`)

Background workers that poll data from vendor plugins:

- **DataWorker** - Polls specific data type (market_data, news, fundamentals, etc.)
- **WorkerManager** - Coordinates multiple workers, handles lifecycle

Each worker:
- Polls at configured intervals
- Implements retry with exponential backoff
- Falls back to alternate vendors on failure
- Records telemetry for monitoring

### 2. Redis Channels

Data is published to Redis channels:

```
stream:market_data:{symbol}    - Market data for specific symbol
stream:news:{symbol}           - News for specific symbol
stream:fundamentals:{symbol}   - Fundamental data
stream:analytics:{symbol}      - Technical indicators
stream:insider_data:{symbol}   - Insider transactions/sentiment
```

Latest data is also cached with TTL:
```
latest:stream:market_data:{symbol}
```

### 3. Streaming Endpoints (`app/api/streaming.py`)

#### Server-Sent Events (SSE)
```
POST /streaming/subscribe/sse
Body: {
  "channels": ["stream:market_data:AAPL"],
  "data_types": ["market_data"],
  "symbols": ["AAPL"]
}
```

Returns SSE stream with real-time updates.

#### WebSocket
```
WS /streaming/ws?channels=stream:market_data:AAPL&symbols=AAPL
```

Bidirectional WebSocket connection for real-time data.

#### Other Endpoints
- `GET /streaming/channels` - List available channels
- `GET /streaming/latest/{channel}` - Get latest cached message

### 4. Configuration API (`app/api/streaming_config.py`)

#### Instruments
```
GET    /streaming/config/instruments           - List all instruments
POST   /streaming/config/instruments           - Add/update instrument
GET    /streaming/config/instruments/{symbol}  - Get specific instrument
DELETE /streaming/config/instruments/{symbol}  - Remove instrument
```

Example instrument config:
```json
{
  "symbol": "AAPL",
  "data_types": ["market_data", "news", "fundamentals"],
  "enabled": true,
  "custom_config": {}
}
```

#### Cadences
```
GET /streaming/config/cadences/{data_type}  - Get cadence for data type
PUT /streaming/config/cadences/{data_type}  - Update cadence
```

Example cadence config:
```json
{
  "data_type": "market_data",
  "interval_seconds": 60,
  "enabled": true,
  "retry_attempts": 3,
  "retry_backoff_multiplier": 2.0,
  "vendor_fallback": true
}
```

#### Workers
```
GET  /streaming/config/workers              - List all workers
GET  /streaming/config/workers/{worker_id}  - Get worker status
POST /streaming/config/workers/{worker_id}/start  - Start worker
POST /streaming/config/workers/{worker_id}/stop   - Stop worker
POST /streaming/config/workers/start-all    - Start all workers
POST /streaming/config/workers/stop-all     - Stop all workers
```

#### Telemetry
```
GET /streaming/config/telemetry/{data_type}?limit=100
```

Returns telemetry records showing vendor performance, latency, errors, etc.

## Configuration

### Environment Variables

```bash
# Enable Redis (required for streaming)
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379

# Streaming configuration
STREAMING_ENABLED=true
AUTO_START_WORKERS=false  # Set to true to auto-start on app startup
```

### Default Cadences

| Data Type      | Default Interval |
|----------------|------------------|
| market_data    | 60 seconds       |
| news           | 300 seconds      |
| fundamentals   | 3600 seconds     |
| analytics      | 600 seconds      |
| insider_data   | 1800 seconds     |

## Usage Examples

### 1. Configure Instruments

```bash
# Add Apple stock tracking
curl -X POST http://localhost:8000/streaming/config/instruments \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "data_types": ["market_data", "news"],
    "enabled": true
  }'

# Add Tesla
curl -X POST http://localhost:8000/streaming/config/instruments \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "TSLA",
    "data_types": ["market_data", "fundamentals"],
    "enabled": true
  }'
```

### 2. Start Workers

```bash
# Start all workers
curl -X POST http://localhost:8000/streaming/config/workers/start-all

# Or start specific worker
curl -X POST http://localhost:8000/streaming/config/workers/worker_market_data/start
```

### 3. Subscribe to Stream (JavaScript)

#### Using SSE
```javascript
const response = await fetch('http://localhost:8000/streaming/subscribe/sse', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    channels: ['stream:market_data:AAPL'],
    symbols: ['AAPL']
  })
});

const reader = response.body.getReader();
const decoder = new TextDecoder();

while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  
  const text = decoder.decode(value);
  // Parse SSE format
  console.log(text);
}
```

#### Using WebSocket
```javascript
const ws = new WebSocket(
  'ws://localhost:8000/streaming/ws?channels=stream:market_data:AAPL&symbols=AAPL'
);

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  if (message.type === 'data') {
    console.log('Market data:', message.message);
  }
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

### 4. Get Latest Data

```bash
# Get latest market data for AAPL
curl http://localhost:8000/streaming/latest/stream:market_data:AAPL
```

### 5. Monitor Workers

```bash
# Get all worker statuses
curl http://localhost:8000/streaming/config/workers

# Get telemetry for market data
curl http://localhost:8000/streaming/config/telemetry/market_data?limit=10
```

## Resilience Features

### Retry Logic

Workers automatically retry failed requests with exponential backoff:

```
Attempt 1: immediate
Attempt 2: 2 seconds delay
Attempt 3: 4 seconds delay
Max: 60 seconds delay
```

Configurable per data type via `retry_attempts` and `retry_backoff_multiplier`.

### Vendor Fallback

When `vendor_fallback` is enabled, workers try alternate vendor plugins on failure:

1. Try primary vendor (based on plugin priority)
2. On error, try next vendor
3. Continue until success or all vendors exhausted

### Telemetry

All vendor operations are logged with:
- Success/failure status
- Latency (milliseconds)
- Error details
- Retry count
- Fallback usage

Access via `/streaming/config/telemetry/{data_type}` endpoint.

## Data Model

### StreamMessage
```json
{
  "channel": "stream:market_data:AAPL",
  "data_type": "market_data",
  "update_type": "snapshot",
  "timestamp": "2024-01-01T12:00:00Z",
  "symbol": "AAPL",
  "data": {
    "raw_data": "...",
    "symbol": "AAPL"
  },
  "vendor": "yfinance",
  "metadata": {
    "worker_id": "worker_market_data",
    "retry_count": 0
  }
}
```

### WorkerStatus
```json
{
  "worker_id": "worker_market_data",
  "data_type": "market_data",
  "status": "running",
  "last_run": "2024-01-01T12:00:00Z",
  "next_run": null,
  "success_count": 150,
  "error_count": 2,
  "current_vendor": "yfinance",
  "last_error": null
}
```

## Performance Considerations

### Redis Memory

Each message is cached with TTL. With 100 instruments and 5 data types:
- ~500 cached messages
- ~50KB per message
- ~25MB total (approximate)

Telemetry is limited to last 1000 records per data type.

### Worker Load

Workers run in separate asyncio tasks. Consider:
- Number of instruments
- Polling intervals
- Vendor rate limits

Example: 100 instruments, 60s interval = ~1.67 requests/second per data type.

### Connection Limits

WebSocket/SSE connections are persistent. Monitor:
- Number of active connections
- Redis connection pool
- Network bandwidth

## Troubleshooting

### Workers Not Starting

```bash
# Check Redis connection
curl http://localhost:8000/ | jq .redis

# Check worker status
curl http://localhost:8000/streaming/config/workers

# Check logs
docker logs tradingagents-backend
```

### No Data in Stream

1. Verify instruments are configured and enabled
2. Check worker status (should be "running")
3. Verify cadence is enabled
4. Check telemetry for errors
5. Verify vendor API keys are configured

### High Error Rate

```bash
# Check telemetry
curl http://localhost:8000/streaming/config/telemetry/market_data?limit=50

# Common issues:
# - Invalid vendor API keys
# - Rate limit exceeded
# - Network connectivity
# - Invalid symbols
```

## Future Enhancements

- Delta updates (only changed fields)
- Data aggregation (OHLC bars)
- Stream filtering server-side
- Compression for large messages
- Metrics dashboard
- Alert system for worker failures
- Multi-region Redis support
