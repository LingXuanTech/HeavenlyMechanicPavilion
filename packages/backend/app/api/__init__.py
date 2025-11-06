"""API route definitions for the TradingAgents FastAPI backend."""

from fastapi import APIRouter

from .agents import router as agents_router
from .auth import router as auth_router
from .auto_trading import router as auto_trading_router
from .backtests import router as backtests_router
from .health import router as health_router
from .llm_providers import router as llm_providers_router
from .market import router as market_router
from .monitoring import router as monitoring_router

# NOTE: agent_llm schema/service not yet implemented
# from .routes.agent_llm import router as agent_llm_router
from .sessions import router as sessions_router
from .streaming import router as streaming_router
from .streaming_config import router as streaming_config_router
from .streams import router as streams_router
from .trading import router as trading_router
from .vendors import router as vendors_router


def get_api_router() -> APIRouter:
    """Construct the application router with all included endpoints."""
    api_router = APIRouter()
    api_router.include_router(health_router, tags=["health"])
    api_router.include_router(auth_router, tags=["authentication"])
    api_router.include_router(monitoring_router, prefix="/monitoring", tags=["monitoring"])
    api_router.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
    api_router.include_router(streams_router, prefix="/sessions", tags=["streams"])
    api_router.include_router(vendors_router, prefix="/vendors", tags=["vendors"])
    api_router.include_router(llm_providers_router, tags=["llm-providers"])
    api_router.include_router(agents_router, tags=["agents"])
    # api_router.include_router(agent_llm_router, tags=["agent-llm-configs"])
    api_router.include_router(trading_router, tags=["trading"])
    api_router.include_router(auto_trading_router, tags=["auto-trading"])
    api_router.include_router(market_router, tags=["market"])
    api_router.include_router(backtests_router, tags=["backtests"])
    api_router.include_router(streaming_router, prefix="/streaming", tags=["streaming"])
    api_router.include_router(
        streaming_config_router, prefix="/streaming/config", tags=["streaming-config"]
    )
    return api_router
