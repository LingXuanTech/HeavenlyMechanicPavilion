# Performance Optimization Quick Start Guide

This guide provides a quick reference for developers to leverage the performance optimizations in TradingAgents.

## 🚀 Quick Wins

### 1. Use Performance Utilities (Backend)

```python
from app.utils import memoize, async_memoize, PerformanceTimer, batch_execute

# Cache expensive function results
@memoize(maxsize=128)
def expensive_calculation(x: int) -> int:
    return x ** 2

# Cache async function results
@async_memoize(maxsize=128)
async def fetch_market_data(symbol: str) -> dict:
    # API call or expensive operation
    return data

# Time operations for debugging
async def process_data():
    with PerformanceTimer("Data Processing"):
        # Your code here
        pass

# Batch process items to avoid overwhelming APIs
results = await batch_execute(
    items=symbols,
    async_func=fetch_price,
    batch_size=10,
    delay=0.1
)
```

### 2. Optimize API Responses (Backend)

Compression middleware is automatic - responses > 500 bytes are automatically gzipped.

```python
# For custom caching, use Redis
from app.cache import get_redis_manager

redis = get_redis_manager()

# Cache JSON data
await redis.set_json("prices:AAPL", price_data, expire=60)
data = await redis.get_json("prices:AAPL")
```

### 3. Optimize Frontend Components

```tsx
// Use dynamic imports for heavy components
import dynamic from 'next/dynamic';

const HeavyChart = dynamic(() => import('./HeavyChart'), {
  loading: () => <p>Loading chart...</p>,
  ssr: false  // Disable SSR for client-only components
});

// Memoize expensive computations
import { useMemo } from 'react';

function MyComponent({ data }) {
  const processedData = useMemo(() => {
    return expensiveDataProcessing(data);
  }, [data]);
  
  return <Chart data={processedData} />;
}
```

## 🔧 Configuration Tuning

### Development Environment

```bash
# .env.local
DATABASE_ECHO=true
DB_ENABLE_QUERY_LOGGING=true
DB_SLOW_QUERY_THRESHOLD=0.1
REDIS_ENABLED=true
```

### Production Environment

```bash
# .env.production
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_RECYCLE=900
REDIS_ENABLED=true
REDIS_MAX_MEMORY=512mb
RATE_LIMIT_ENABLED=true
MONITORING_ENABLED=true
```

## 📊 Monitoring Performance

### Check Backend Metrics

```bash
# Prometheus metrics
curl http://localhost:8000/metrics

# Health check
curl http://localhost:8000/health

# Database query logs (if enabled)
tail -f logs/app.log | grep "slow query"
```

### Check Redis Performance

```bash
# Connect to Redis
redis-cli -h localhost -p 6379

# Check stats
INFO stats

# Check memory usage
INFO memory

# Check cache hit rate
INFO stats | grep keyspace
```

### Analyze Frontend Bundle

```bash
cd packages/frontend

# Analyze bundle size
ANALYZE=true pnpm build

# This will open bundle analyzer in your browser
```

## 🎯 Performance Checklist

### Before Deploying to Production

- [ ] **Database**: Connection pooling configured (`DB_POOL_SIZE`)
- [ ] **Redis**: Connection pooling enabled with appropriate memory limit
- [ ] **Compression**: Middleware enabled (automatic in production)
- [ ] **Monitoring**: Prometheus metrics enabled
- [ ] **Caching**: Redis enabled for API responses
- [ ] **Rate Limiting**: Enabled to prevent abuse
- [ ] **Docker**: BuildKit enabled for faster builds
- [ ] **Frontend**: Bundle analyzed and optimized
- [ ] **Query Logging**: Enabled to catch slow queries

### Performance Testing

```bash
# Backend load test (requires apache2-utils)
ab -n 1000 -c 10 http://localhost:8000/api/health

# Or use k6 for advanced testing
k6 run tests/load/api-test.js

# Frontend lighthouse test
npm install -g lighthouse
lighthouse http://localhost:3000
```

## 🐛 Troubleshooting

### Slow API Responses

1. Check if compression is working:
   ```bash
   curl -H "Accept-Encoding: gzip" -I http://localhost:8000/api/portfolios
   # Should see "Content-Encoding: gzip"
   ```

2. Check slow query logs:
   ```bash
   # Enable query logging
   export DB_ENABLE_QUERY_LOGGING=true
   export DB_SLOW_QUERY_THRESHOLD=0.5
   
   # Restart and check logs
   tail -f logs/app.log | grep "slow query"
   ```

3. Check Redis hit rate:
   ```bash
   redis-cli INFO stats | grep keyspace_hits
   ```

### High Memory Usage

1. **Backend**:
   ```bash
   # Check Python memory usage
   ps aux | grep python
   
   # Reduce connection pool if needed
   DB_POOL_SIZE=10
   DB_MAX_OVERFLOW=15
   ```

2. **Redis**:
   ```bash
   # Check Redis memory
   redis-cli INFO memory
   
   # Reduce if needed
   REDIS_MAX_MEMORY=256mb
   ```

3. **Frontend**:
   ```bash
   # Check Node memory during build
   NODE_OPTIONS="--max-old-space-size=4096" pnpm build
   ```

### Slow Docker Builds

1. **Enable BuildKit**:
   ```bash
   export DOCKER_BUILDKIT=1
   docker-compose build
   ```

2. **Clean up build cache if needed**:
   ```bash
   docker builder prune
   ```

3. **Use cache mounts** (already configured in Dockerfiles)

## 📈 Expected Performance Gains

| Optimization | Impact | Metric |
|-------------|---------|--------|
| Response Compression | 60-80% | Response size |
| Redis Connection Pool | 30-50% | Redis latency |
| Database Indexes | 30-50% | Query time |
| Frontend Code Splitting | 40-60% | Initial load |
| Docker BuildKit | 60-80% | Build time (cached) |
| API Response Caching | 90%+ | Cache hit response |

## 🔗 Resources

- [Full Performance Documentation](PERFORMANCE_OPTIMIZATIONS.md)
- [Database Optimization Details](DB_OPTIMIZATION_SUMMARY.md)
- [Production Configuration Example](.env.production.example)
- [Next.js Optimization Docs](https://nextjs.org/docs/advanced-features/compiler)
- [FastAPI Performance Tips](https://fastapi.tiangolo.com/deployment/concepts/)

## 💡 Pro Tips

1. **Always profile before optimizing** - Use the `PerformanceTimer` context manager
2. **Monitor cache hit rates** - Aim for > 70% cache hit rate
3. **Set realistic pool sizes** - Start small and scale based on metrics
4. **Use batch operations** - Process multiple items together when possible
5. **Lazy load heavy components** - Use dynamic imports in Next.js
6. **Enable query logging in staging** - Catch N+1 queries before production
7. **Regular bundle analysis** - Keep frontend bundle size in check

## 🆘 Need Help?

- Check [PERFORMANCE_OPTIMIZATIONS.md](PERFORMANCE_OPTIMIZATIONS.md) for detailed explanations
- Review [IMPROVEMENT_PLAN.md](IMPROVEMENT_PLAN.md) for planned optimizations
- Monitor `/metrics` endpoint for real-time performance data
- Enable `DB_ENABLE_QUERY_LOGGING` to debug slow queries

---

**Last Updated**: January 2025
