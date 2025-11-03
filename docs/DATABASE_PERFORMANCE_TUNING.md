# Database Performance Tuning Guide

This guide covers database optimization features and configuration options for TradingAgents.

## Overview

The database layer has been optimized to provide:
- Connection pooling for better concurrent request handling
- Query performance monitoring and slow query logging
- Composite indexes for common query patterns
- Eager loading support to prevent N+1 queries
- Read replica support (feature-flagged)

## Connection Pooling

### Configuration

Connection pooling is automatically enabled for PostgreSQL and other supported databases (SQLite excluded). Configure via environment variables:

```bash
# Number of connections to maintain in the pool (default: 5)
DB_POOL_SIZE=10

# Maximum number of connections beyond pool_size (default: 10)
DB_MAX_OVERFLOW=20

# Timeout in seconds for getting a connection (default: 30.0)
DB_POOL_TIMEOUT=30.0

# Recycle connections after N seconds (default: 3600 = 1 hour)
DB_POOL_RECYCLE=3600

# Enable connection health checks before use (default: true)
DB_POOL_PRE_PING=true

# Log connection pool activity (default: false)
DB_ECHO_POOL=false
```

### Recommended Settings

**Development:**
```bash
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
```

**Production (moderate load):**
```bash
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=1800  # 30 minutes
```

**Production (high load):**
```bash
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
DB_POOL_RECYCLE=900  # 15 minutes
```

### How It Works

- **pool_size**: Minimum number of connections kept open
- **max_overflow**: Additional connections that can be created on demand
- **pool_timeout**: How long to wait for an available connection
- **pool_recycle**: Prevents stale connections by recycling them periodically
- **pool_pre_ping**: Checks connection health before use (recommended for production)

## Query Performance Monitoring

### Configuration

Enable query logging and slow query detection:

```bash
# Enable query performance logging (default: false)
DB_ENABLE_QUERY_LOGGING=true

# Threshold in seconds for slow query warnings (default: 1.0)
DB_SLOW_QUERY_THRESHOLD=0.5
```

### What Gets Logged

When enabled:
- **Slow queries**: Queries exceeding the threshold are logged as warnings with execution time
- **Debug queries**: All queries are logged at debug level with execution time (when DATABASE_ECHO=true)

Example log output:
```
WARNING - Slow query detected (took 1.23s): SELECT portfolios.id, portfolios.name...
DEBUG - Query executed in 0.0234s
```

### Best Practices

1. **Development**: Set `DB_ENABLE_QUERY_LOGGING=true` and `DB_SLOW_QUERY_THRESHOLD=0.1` to catch inefficient queries
2. **Production**: Set `DB_SLOW_QUERY_THRESHOLD=1.0` to only log genuinely slow queries
3. **Monitor logs**: Review slow query logs regularly to identify optimization opportunities

## Database Indexes

### Added Indexes

The following indexes have been added for performance optimization:

#### Trades Table
```sql
-- Session-based queries
CREATE INDEX ix_trades_session_id ON trades(session_id);

-- Portfolio + status filtering
CREATE INDEX ix_trades_portfolio_status ON trades(portfolio_id, status);

-- Time-based queries per portfolio
CREATE INDEX ix_trades_portfolio_created ON trades(portfolio_id, created_at);
```

#### Positions Table
```sql
-- Composite index for position lookups
CREATE INDEX ix_positions_portfolio_symbol ON positions(portfolio_id, symbol);
```

### Query Optimization Examples

**Before (N+1 problem):**
```python
# Get portfolio
portfolio = await portfolio_repo.get(portfolio_id)

# Get positions (separate query)
positions = await position_repo.get_by_portfolio(portfolio_id)
```

**After (eager loading):**
```python
# Get portfolio with positions in one query
portfolio = await portfolio_repo.get_with_positions(portfolio_id)
positions = portfolio.positions  # No additional query
```

## Eager Loading

### Repository Methods

New repository methods with eager loading support:

#### PortfolioRepository
```python
# Get portfolio with positions
portfolio = await portfolio_repo.get_with_positions(portfolio_id)

# Get portfolio with trades
portfolio = await portfolio_repo.get_with_trades(portfolio_id)

# Get portfolio with all relationships
portfolio = await portfolio_repo.get_with_all_relations(portfolio_id)
```

#### TradeRepository
```python
# Get trade with executions
trade = await trade_repo.get_with_executions(trade_id)

# Get trades by session
trades = await trade_repo.get_by_session(session_id)

# Get trades with executions for portfolio
trades = await trade_repo.get_by_portfolio_with_executions(portfolio_id)
```

### When to Use Eager Loading

✅ **Use eager loading when:**
- You know you'll access related objects
- Processing multiple parent objects and their children
- Building API responses that include related data

❌ **Don't use eager loading when:**
- You only need the parent object
- Related data is large and rarely accessed
- You're doing bulk updates without reading relationships

## Read Replica Support

### Configuration

Enable read replicas for scaling read operations:

```bash
# Enable read replica (default: false)
DB_ENABLE_READ_REPLICA=true

# Read replica connection URL
DB_READ_REPLICA_URL=postgresql+asyncpg://user:pass@replica-host:5432/tradingagents
```

### How It Works

When read replica is enabled:
- **Write operations**: Use primary database
- **Read operations**: Can use read replica via `get_read_session()`
- **Fallback**: If read replica is unavailable, falls back to primary

### Usage in Code

```python
from app.db.session import get_db_manager

# For read operations (uses replica if configured)
db_manager = get_db_manager()
async for session in db_manager.get_read_session():
    # Read-only queries
    positions = await position_repo.get_by_portfolio(portfolio_id)

# For write operations (always uses primary)
async for session in db_manager.get_session():
    # Write queries
    await portfolio_repo.create(new_portfolio)
```

### Best Practices

1. **Replication lag**: Be aware of potential replication lag (typically < 1 second)
2. **Consistency**: Use primary for operations requiring immediate consistency
3. **Load distribution**: Route bulk read operations to replicas
4. **Monitoring**: Monitor replica lag and health

## Applying Database Migrations

### Run Migrations

Apply the database optimization migration:

```bash
cd packages/backend
source .venv/bin/activate
alembic upgrade head
```

### Migration Details

The optimization migration adds:
- `session_id` column to trades table with foreign key and index
- Composite index on `positions(portfolio_id, symbol)`
- Composite index on `trades(portfolio_id, status)`
- Composite index on `trades(portfolio_id, created_at)`

### Verify Migrations

Check that migrations applied successfully:

```bash
alembic current
alembic history
```

## Performance Testing

### Test Connection Pooling

Monitor connection pool usage:

```bash
# Enable pool logging
DB_ECHO_POOL=true
```

Watch for:
- "Pool size" messages indicating pool growth
- "Connection being returned" messages
- Pool timeout errors (increase pool_size or max_overflow if occurring)

### Test Query Performance

Enable query logging and test your endpoints:

```bash
DB_ENABLE_QUERY_LOGGING=true
DB_SLOW_QUERY_THRESHOLD=0.1
DATABASE_ECHO=true
```

Then run your application and monitor:
1. Number of queries per endpoint
2. Query execution times
3. N+1 query patterns (multiple similar queries)

### Benchmark Queries

Use the query logging to identify slow queries, then use database tools to analyze them:

**PostgreSQL:**
```sql
EXPLAIN ANALYZE SELECT * FROM trades WHERE portfolio_id = 1 AND status = 'FILLED';
```

**SQLite:**
```sql
EXPLAIN QUERY PLAN SELECT * FROM trades WHERE portfolio_id = 1 AND status = 'FILLED';
```

## Troubleshooting

### Connection Pool Exhaustion

**Symptom:** "QueuePool limit of size X overflow Y reached"

**Solutions:**
1. Increase `DB_POOL_SIZE` and `DB_MAX_OVERFLOW`
2. Check for connection leaks (unclosed sessions)
3. Reduce `DB_POOL_TIMEOUT` to fail faster
4. Optimize long-running queries

### Slow Queries

**Symptom:** Queries taking longer than expected

**Solutions:**
1. Check if appropriate indexes exist
2. Use `EXPLAIN ANALYZE` to understand query plans
3. Consider adding more specific indexes
4. Use eager loading for N+1 problems
5. Add pagination for large result sets

### Replication Lag

**Symptom:** Read replica returns stale data

**Solutions:**
1. Use primary database for critical reads
2. Add retry logic for read-after-write scenarios
3. Monitor replica lag metrics
4. Consider eventual consistency in application design

## Environment Variable Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | sqlite+aiosqlite:///./tradingagents.db | Primary database URL |
| `DATABASE_ECHO` | false | Log all SQL statements |
| `DB_POOL_SIZE` | 5 | Connection pool size |
| `DB_MAX_OVERFLOW` | 10 | Max additional connections |
| `DB_POOL_TIMEOUT` | 30.0 | Connection timeout (seconds) |
| `DB_POOL_RECYCLE` | 3600 | Connection recycle time (seconds) |
| `DB_POOL_PRE_PING` | true | Health check before use |
| `DB_ECHO_POOL` | false | Log pool activity |
| `DB_ENABLE_QUERY_LOGGING` | false | Enable query performance logging |
| `DB_SLOW_QUERY_THRESHOLD` | 1.0 | Slow query threshold (seconds) |
| `DB_ENABLE_READ_REPLICA` | false | Enable read replica |
| `DB_READ_REPLICA_URL` | null | Read replica database URL |

## Additional Resources

- [SQLAlchemy Connection Pooling](https://docs.sqlalchemy.org/en/14/core/pooling.html)
- [PostgreSQL Performance Tips](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
