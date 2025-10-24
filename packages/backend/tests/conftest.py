"""Pytest configuration and shared fixtures."""

import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import fakeredis.aioredis
import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis_client import RedisManager
from app.db.session import DatabaseManager


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db() -> AsyncGenerator[DatabaseManager, None]:
    """Create a test database with in-memory SQLite."""
    database_url = "sqlite+aiosqlite:///:memory:"
    db_manager = DatabaseManager(database_url, echo=False)
    
    await db_manager.create_tables()
    
    yield db_manager
    
    await db_manager.drop_tables()
    await db_manager.close()


@pytest.fixture
async def db_session(test_db: DatabaseManager) -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for tests."""
    async for session in test_db.get_session():
        yield session


@pytest.fixture
async def redis_client() -> AsyncGenerator[fakeredis.aioredis.FakeRedis, None]:
    """Provide a fake Redis client for testing."""
    client = fakeredis.aioredis.FakeRedis()
    yield client
    await client.aclose()


@pytest.fixture
def redis_manager(redis_client: fakeredis.aioredis.FakeRedis) -> RedisManager:
    """Provide a Redis manager instance for testing."""
    manager = RedisManager()
    manager._client = redis_client
    return manager


@pytest.fixture
def mock_openai_client() -> MagicMock:
    """Mock OpenAI client for testing."""
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock()
    return mock_client


@pytest.fixture
def mock_trading_graph() -> MagicMock:
    """Mock TradingAgentsGraph for testing."""
    mock_graph = MagicMock()
    mock_graph.propagate = AsyncMock(return_value=(
        {"status": "completed"},
        {"action": "BUY", "quantity": 100, "confidence": 0.85}
    ))
    return mock_graph


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client for testing FastAPI endpoints."""
    from app.main import app
    
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client


@pytest.fixture
def sync_client() -> Generator[TestClient, None, None]:
    """Provide a sync test client for FastAPI endpoints."""
    from app.main import app
    
    with TestClient(app) as client:
        yield client


@pytest.fixture
def sample_trading_config() -> dict[str, Any]:
    """Provide a sample trading configuration."""
    return {
        "ticker": "AAPL",
        "date": "2024-01-15",
        "deep_think_llm": "gpt-4o",
        "quick_think_llm": "gpt-4o-mini",
        "max_debate_rounds": 2,
        "data_vendors": {
            "core_stock_apis": "yfinance",
            "technical_indicators": "yfinance",
            "fundamental_data": "alpha_vantage",
            "news_data": "alpha_vantage",
        }
    }


@pytest.fixture
def sample_market_data() -> dict[str, Any]:
    """Provide sample market data for testing."""
    return {
        "ticker": "AAPL",
        "date": "2024-01-15",
        "open": 180.5,
        "high": 182.3,
        "low": 179.8,
        "close": 181.7,
        "volume": 58000000,
        "adj_close": 181.7,
    }


@pytest.fixture
def sample_portfolio() -> dict[str, Any]:
    """Provide a sample portfolio for testing."""
    return {
        "cash": 100000.0,
        "positions": [
            {
                "ticker": "AAPL",
                "quantity": 50,
                "avg_price": 175.0,
                "current_price": 181.7,
            }
        ],
        "total_value": 109085.0,
    }


@pytest.fixture
def sample_risk_params() -> dict[str, Any]:
    """Provide sample risk management parameters."""
    return {
        "max_position_size": 0.2,
        "max_portfolio_risk": 0.15,
        "stop_loss_pct": 0.05,
        "take_profit_pct": 0.15,
        "max_drawdown": 0.20,
    }


@pytest.fixture(autouse=True)
def reset_env_vars() -> Generator[None, None, None]:
    """Reset environment variables after each test."""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_plugin_registry() -> MagicMock:
    """Mock plugin registry for testing."""
    from tradingagents.plugins.base import DataVendorPlugin, PluginCapability
    
    mock_registry = MagicMock()
    
    mock_plugin = MagicMock(spec=DataVendorPlugin)
    mock_plugin.name = "test_vendor"
    mock_plugin.provider = "test"
    mock_plugin.capabilities = [PluginCapability.STOCK_DATA]
    
    mock_registry.list_plugins.return_value = [mock_plugin]
    mock_registry.get_plugin.return_value = mock_plugin
    mock_registry.get_plugins_with_capability.return_value = [mock_plugin]
    
    return mock_registry
