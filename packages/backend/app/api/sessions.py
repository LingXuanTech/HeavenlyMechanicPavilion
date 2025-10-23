"""Session control routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from ..dependencies import get_graph_service
from ..schemas.config import GraphConfiguration
from ..schemas.sessions import RunSessionRequest, RunSessionResponse
from ..services.graph import TradingGraphService

router = APIRouter()


@router.get("/config", response_model=GraphConfiguration)
async def get_configuration(
    service: TradingGraphService = Depends(get_graph_service),
) -> GraphConfiguration:
    config = service.configuration()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TradingAgents configuration is unavailable",
        )

    return GraphConfiguration(
        llm_provider=config.get("llm_provider"),
        deep_think_llm=config.get("deep_think_llm"),
        quick_think_llm=config.get("quick_think_llm"),
        results_dir=config.get("results_dir"),
        data_vendors=config.get("data_vendors", {}),
        tool_vendors=config.get("tool_vendors", {}),
    )


@router.post("", response_model=RunSessionResponse, status_code=status.HTTP_202_ACCEPTED)
async def run_session(
    request: RunSessionRequest,
    service: TradingGraphService = Depends(get_graph_service),
) -> RunSessionResponse:
    metadata = await service.run_session(
        ticker=request.ticker,
        trade_date=request.trade_date,
        selected_analysts=request.selected_analysts,
    )
    return RunSessionResponse(**metadata)
