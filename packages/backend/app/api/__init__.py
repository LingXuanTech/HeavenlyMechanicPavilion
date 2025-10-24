"""API route definitions for the TradingAgents FastAPI backend."""

from fastapi import APIRouter

from .agents import router as agents_router
from .backtests import router as backtests_router
from .health import router as health_router
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
    api_router.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
    api_router.include_router(streams_router, prefix="/sessions", tags=["streams"])
    api_router.include_router(vendors_router, prefix="/vendors", tags=["vendors"])
    api_router.include_router(agents_router, tags=["agents"])
    api_router.include_router(trading_router, tags=["trading"])
    api_router.include_router(backtests_router, tags=["backtests"])
    api_router.include_router(streaming_router, prefix="/streaming", tags=["streaming"])
    api_router.include_router(streaming_config_router, prefix="/streaming/config", tags=["streaming-config"])
    return api_router
