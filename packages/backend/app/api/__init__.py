"""API route definitions for the TradingAgents FastAPI backend."""

from fastapi import APIRouter

from .health import router as health_router
from .sessions import router as sessions_router
from .streams import router as streams_router


def get_api_router() -> APIRouter:
    """Construct the application router with all included endpoints."""
    api_router = APIRouter()
    api_router.include_router(health_router, tags=["health"])
    api_router.include_router(sessions_router, prefix="/sessions", tags=["sessions"])
    api_router.include_router(streams_router, prefix="/sessions", tags=["streams"])
    return api_router
