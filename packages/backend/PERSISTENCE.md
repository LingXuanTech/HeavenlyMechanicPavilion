# Persistence, Caching, and Resource Management

This document describes the persistence, caching, and resource management layer implemented for the TradingAgents backend.

## Overview

The implementation includes:

1. **Database Layer** - SQLModel/SQLAlchemy with async support for PostgreSQL and SQLite
2. **Alembic Migrations** - Database schema versioning and migration management
3. **Repository Pattern** - Abstraction layer for database operations
4. **Redis Caching** - Optional caching layer with pub/sub placeholders
5. **Configuration Management** - Environment-based configuration for all resources

## Database Models

The following SQLModel models have been defined in `app/db/models/`:

### Portfolio (`portfolio.py`)
- Stores portfolio information including initial/current capital
- Tracks portfolio metadata and configuration
- Relationships: positions, trades

### Position (`position.py`)
- Represents current holdings in a portfolio
- Tracks quantity, cost basis, and P&L
- Supports LONG and SHORT position types

### Trade (`trade.py`)
- Stores trading decisions and orders
- Tracks order status (PENDING, FILLED, PARTIAL, CANCELLED, REJECTED)
- Includes agent decision rationale and confidence scores
- Relationships: portfolio, executions

### Execution (`execution.py`)
- Records trade executions and partial fills
- Tracks execution price, commission, and fees
- Links to parent trade

### AgentConfig (`agent_config.py`)
- Stores AI agent configurations
- Includes LLM settings (provider, model, temperature, etc.)
- Supports agent-specific parameters via JSON field

### VendorConfig (`vendor_config.py`)
- Stores data vendor configurations
- Manages API credentials (references to secrets)
- Tracks rate limiting parameters

### RunLog (`run_log.py`)
- Records agent execution and session logs
- Tracks run status, timing, and performance metrics
- Stores configuration snapshots used in runs

## Database Setup

### Configuration

Database connection is configured via environment variables:

```bash
# SQLite (default)
DATABASE_URL=sqlite+aiosqlite:///./tradingagents.db

# PostgreSQL
DATABASE_URL=postgresql+asyncpg://user:password@localhost/tradingagents

# Debug mode (echoes SQL)
DATABASE_ECHO=false
```

### Initialization

The database is automatically initialized on FastAPI startup:

```python
from app.db import init_db

db_manager = init_db(
    database_url=settings.database_url,
    echo=settings.database_echo,
)
```

### Migrations

Alembic is configured for database migrations:

```bash
# Generate a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# View current version
alembic current
```

The initial migration has been created and includes all models.

## Repository Pattern

Repository classes provide a clean abstraction for database operations:

```python
from app.repositories import PortfolioRepository
from app.dependencies import get_db_session

async def example(session: AsyncSession = Depends(get_db_session)):
    portfolio_repo = PortfolioRepository(session)
    
    # Get by ID
    portfolio = await portfolio_repo.get(1)
    
    # Get by name
    portfolio = await portfolio_repo.get_by_name("my_portfolio")
    
    # Create
    new_portfolio = Portfolio(name="test", initial_capital=100000)
    portfolio = await portfolio_repo.create(new_portfolio)
    
    # Update
    updated = await portfolio_repo.update(
        db_obj=portfolio,
        obj_in={"current_capital": 105000}
    )
    
    # Delete
    deleted = await portfolio_repo.delete(id=1)
```

Available repositories:
- `PortfolioRepository`
- `PositionRepository`
- `TradeRepository`
- `ExecutionRepository`
- `AgentConfigRepository`
- `VendorConfigRepository`
- `RunLogRepository`

Each repository extends `BaseRepository` with common CRUD operations and adds domain-specific query methods.

## Redis Caching

Redis integration is optional and configured via environment variables:

```bash
REDIS_ENABLED=true
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=your_password  # optional
```

### Cache Service

The `CacheService` provides high-level caching operations:

```python
from app.cache import CacheService
from app.dependencies import get_cache_service

async def example(cache: CacheService = Depends(get_cache_service)):
    if cache is None:
        # Redis not enabled
        return
    
    # Cache market data
    await cache.cache_market_data(
        symbol="AAPL",
        date="2024-01-01",
        data={"price": 150.0, "volume": 1000000},
        expire=3600  # 1 hour
    )
    
    # Retrieve cached data
    data = await cache.get_market_data("AAPL", "2024-01-01")
    
    # Cache session data
    await cache.cache_session_data(
        session_id="abc123",
        data={"status": "running"},
        expire=86400  # 24 hours
    )
    
    # Generic cache operations
    await cache.cache_value("my_key", {"some": "data"}, expire=300)
    data = await cache.get_cached("my_key")
    await cache.invalidate("my_key")
```

### Pub/Sub Placeholders

Redis pub/sub hooks are available for future implementation:

```python
from app.cache import get_redis_manager

redis_manager = get_redis_manager()

# Publish a message
await redis_manager.publish("trading_events", "order_filled")

# Subscribe to channels (placeholder for future implementation)
pubsub = await redis_manager.subscribe("trading_events")
```

## FastAPI Integration

### Dependencies

The application provides FastAPI dependencies for resource access:

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db_session, get_cache_service, get_settings
from app.config import Settings
from app.cache import CacheService

@app.get("/portfolios/{portfolio_id}")
async def get_portfolio(
    portfolio_id: int,
    session: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    settings: Settings = Depends(get_settings),
):
    # Use session for database operations
    # Use cache for caching (if enabled)
    # Use settings for configuration
    pass
```

### Lifecycle Management

Database and Redis connections are managed through FastAPI lifecycle events:

- **Startup**: Initialize database and Redis connections, optionally create tables in debug mode
- **Shutdown**: Close all connections gracefully

## Configuration

All configuration is managed through the `Settings` class in `app/config/settings.py`:

```python
from app.config import Settings

settings = Settings()

# Database
print(settings.database_url)
print(settings.is_sqlite)
print(settings.is_postgresql)

# Redis
print(settings.redis_enabled)
print(settings.redis_host)

# TradingAgents
print(settings.llm_provider)
print(settings.config_overrides())

# Application
print(settings.debug)
```

Settings are loaded from:
1. Environment variables
2. `.env` file (if present)
3. Default values

## Environment Variables

Complete list of environment variables:

```bash
# API Keys
OPENAI_API_KEY=your_key
ALPHA_VANTAGE_API_KEY=your_key

# TradingAgents Configuration
TRADINGAGENTS_LLM_PROVIDER=openai
TRADINGAGENTS_DEEP_THINK_LLM=o4-mini
TRADINGAGENTS_QUICK_THINK_LLM=gpt-4o-mini
TRADINGAGENTS_RESULTS_DIR=./results

# Database
DATABASE_URL=sqlite+aiosqlite:///./tradingagents.db
DATABASE_ECHO=false

# Redis
REDIS_ENABLED=false
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=optional_password

# Application
DEBUG=false
API_TITLE=TradingAgents Backend
API_VERSION=0.1.0
```

## Usage Examples

### Complete Example: Creating a Trade

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.db.models import Portfolio, Trade
from app.repositories import PortfolioRepository, TradeRepository
from app.dependencies import get_db_session

router = APIRouter()

@router.post("/portfolios/{portfolio_id}/trades")
async def create_trade(
    portfolio_id: int,
    symbol: str,
    action: str,
    quantity: float,
    session: AsyncSession = Depends(get_db_session),
):
    # Get portfolio
    portfolio_repo = PortfolioRepository(session)
    portfolio = await portfolio_repo.get(portfolio_id)
    
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    # Create trade
    trade = Trade(
        portfolio_id=portfolio_id,
        symbol=symbol,
        action=action,
        quantity=quantity,
        status="PENDING",
        created_at=datetime.utcnow(),
    )
    
    trade_repo = TradeRepository(session)
    created_trade = await trade_repo.create(trade)
    
    return {"trade_id": created_trade.id, "status": created_trade.status}
```

## Testing

To test the database layer:

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db import SQLModel

@pytest.fixture
async def test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    await engine.dispose()
```

## Next Steps

Potential enhancements:

1. **Connection Pooling**: Configure connection pool settings for production
2. **Redis Pub/Sub**: Implement full pub/sub event streaming
3. **Caching Strategies**: Add cache-aside, write-through patterns
4. **Query Optimization**: Add indexes, implement query optimization
5. **Monitoring**: Add database and cache performance monitoring
6. **Backup/Restore**: Implement automated backup strategies
7. **Data Encryption**: Add encryption for sensitive fields
8. **Multi-tenancy**: Support multiple isolated portfolios/users
