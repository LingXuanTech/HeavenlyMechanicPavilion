"""
Pytest 配置和共享 Fixtures

提供：
1. 内存数据库会话
2. FastAPI 测试客户端
3. Mock 数据源工厂
4. 常用测试数据
"""
import pytest
from datetime import datetime
from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

# 确保在导入 app 之前设置环境变量
import os
os.environ.setdefault("ENV", "testing")
os.environ.setdefault("DATABASE_MODE", "sqlite")
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy-key-for-testing-only")
os.environ.setdefault("GOOGLE_API_KEY", "")
os.environ.setdefault("ALPHA_VANTAGE_API_KEY", "")

# 导入所有模型以确保 SQLModel.metadata 包含所有表
from db.models import (
    Watchlist, AnalysisResult, ChatHistory,
    AIProvider, AIModelConfig,
    AgentPrompt, PromptVersion
)


# =============================================================================
# 数据库 Fixtures
# =============================================================================

@pytest.fixture(scope="function")
def test_engine():
    """创建内存 SQLite 引擎（每个测试函数独立）"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """创建数据库会话"""
    with Session(test_engine) as session:
        yield session


@pytest.fixture(scope="function")
def override_get_session(db_session):
    """用于覆盖 FastAPI 依赖的会话工厂"""
    def _get_session():
        yield db_session
    return _get_session


# =============================================================================
# FastAPI 测试客户端
# =============================================================================

@pytest.fixture(scope="function")
def client(override_get_session) -> Generator[TestClient, None, None]:
    """创建 FastAPI 测试客户端（使用内存数据库）"""
    # 在导入 main 之前，先确保生产数据库表存在（用于 prompt_config_service 初始化）
    from db.models import engine as production_engine
    SQLModel.metadata.create_all(production_engine)

    from main import app
    from db.models import get_session

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def async_client(override_get_session):
    """创建异步 httpx 测试客户端"""
    import httpx

    # 确保生产数据库表存在
    from db.models import engine as production_engine
    SQLModel.metadata.create_all(production_engine)

    from main import app
    from db.models import get_session

    app.dependency_overrides[get_session] = override_get_session

    transport = httpx.ASGITransport(app=app)
    return httpx.AsyncClient(transport=transport, base_url="http://test")


# =============================================================================
# Mock 数据源
# =============================================================================

@pytest.fixture
def mock_yfinance():
    """Mock yfinance 模块"""
    with patch("services.data_router.yf") as mock_yf:
        mock_ticker = MagicMock()
        mock_ticker.fast_info = {
            "last_price": 150.0,
            "previous_close": 148.0,
            "last_volume": 1000000,
        }
        mock_ticker.info = {
            "longName": "Apple Inc.",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "trailingPE": 25.5,
            "marketCap": 2500000000000,
            "dividendYield": 0.005,
            "revenueGrowth": 0.08,
            "profitMargins": 0.25,
            "longBusinessSummary": "Apple Inc. designs, manufactures, and markets smartphones.",
        }
        mock_yf.Ticker.return_value = mock_ticker
        yield mock_yf


@pytest.fixture
def mock_akshare():
    """Mock akshare 模块"""
    import pandas as pd

    with patch("services.data_router.ak") as mock_ak:
        # Mock A股实时数据
        mock_ak.stock_zh_a_spot_em.return_value = pd.DataFrame({
            "代码": ["600519", "000001"],
            "名称": ["贵州茅台", "平安银行"],
            "最新价": [1800.0, 10.5],
            "涨跌额": [20.0, 0.15],
            "涨跌幅": [1.12, 1.45],
            "成交量": [5000000, 80000000],
        })

        # Mock A股历史数据
        mock_ak.stock_zh_a_hist.return_value = pd.DataFrame({
            "日期": pd.date_range(end=datetime.now(), periods=30),
            "开盘": [1780.0] * 30,
            "最高": [1810.0] * 30,
            "最低": [1770.0] * 30,
            "收盘": [1800.0] * 30,
            "成交量": [5000000] * 30,
        })

        yield mock_ak


@pytest.fixture
def mock_alpha_vantage(mocker):
    """Mock Alpha Vantage API 响应 (通过 httpx)"""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "Global Quote": {
            "05. price": "150.00",
            "08. previous close": "148.00",
            "10. change percent": "1.35%",
            "06. volume": "1000000",
        }
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_response)
    mocker.patch("services.data_router.get_http_client", return_value=mock_client)


# =============================================================================
# Mock LLM
# =============================================================================

@pytest.fixture
def mock_llm():
    """Mock LangChain LLM"""
    mock = AsyncMock()
    mock.ainvoke.return_value = MagicMock(content="Mock LLM response")
    return mock


@pytest.fixture
def mock_langchain_google():
    """Mock Google Gemini LLM"""
    with patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_class:
        mock_instance = AsyncMock()
        mock_instance.ainvoke.return_value = MagicMock(content="Mock Gemini response")
        mock_class.return_value = mock_instance
        yield mock_class


@pytest.fixture
def mock_langchain_openai():
    """Mock OpenAI LLM"""
    with patch("langchain_openai.ChatOpenAI") as mock_class:
        mock_instance = AsyncMock()
        mock_instance.ainvoke.return_value = MagicMock(content="Mock OpenAI response")
        mock_class.return_value = mock_instance
        yield mock_class


# =============================================================================
# 测试数据 Fixtures
# =============================================================================

@pytest.fixture
def sample_watchlist_item():
    """示例关注列表项"""
    from db.models import Watchlist
    return Watchlist(
        symbol="AAPL",
        name="Apple Inc.",
        market="US",
    )


@pytest.fixture
def sample_analysis_result():
    """示例分析结果"""
    from db.models import AnalysisResult
    import json

    return AnalysisResult(
        symbol="AAPL",
        date="2026-01-28",
        signal="Strong Buy",
        confidence=85,
        full_report_json=json.dumps({
            "signal": "Strong Buy",
            "confidence": 85,
            "summary": "Test analysis summary",
        }),
        anchor_script="Today we analyzed Apple Inc...",
        task_id="test-task-123",
        status="completed",
        elapsed_seconds=45.2,
    )


@pytest.fixture
def sample_stock_price():
    """示例股票价格"""
    from services.models import StockPrice
    return StockPrice(
        symbol="AAPL",
        price=150.0,
        change=2.0,
        change_percent=1.35,
        volume=1000000,
        timestamp=datetime.now(),
        market="US",
    )


# =============================================================================
# 工具函数
# =============================================================================

@pytest.fixture
def clear_price_cache():
    """清除价格缓存"""
    from services.data_router import MarketRouter
    MarketRouter.clear_cache()
    yield
    MarketRouter.clear_cache()
