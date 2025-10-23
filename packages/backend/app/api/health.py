"""Health related API routes."""

from fastapi import APIRouter, Depends

from ..dependencies import get_graph_service
from ..schemas.health import HealthStatus
from ..services.graph import TradingGraphService

router = APIRouter()


@router.get("/health", response_model=HealthStatus)
async def get_health(service: TradingGraphService = Depends(get_graph_service)) -> HealthStatus:
    return HealthStatus(**service.health())
