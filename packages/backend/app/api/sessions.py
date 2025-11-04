"""Session control routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..dependencies import get_event_manager, get_graph_service
from ..schemas.config import GraphConfiguration
from ..schemas.sessions import (
    BufferedSessionEvent,
    RunSessionRequest,
    RunSessionResponse,
    SessionDetailResponse,
    SessionListResponse,
    SessionSummary,
)
from ..services.analysis_session import AnalysisSessionService
from ..services.events import SessionEventManager
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


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of records to return"),
    status: Optional[str] = Query(None, description="Filter by status"),
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    db: AsyncSession = Depends(get_session),
    event_manager: SessionEventManager = Depends(get_event_manager),
) -> SessionListResponse:
    """List recent analysis sessions with optional filters.
    
    Returns paginated list of analysis sessions ordered by creation date (newest first).
    Supports filtering by status (pending, running, completed, failed) and ticker.
    """
    analysis_service = AnalysisSessionService(db, event_manager)
    sessions = await analysis_service.list_sessions(
        skip=skip, limit=limit, status=status, ticker=ticker
    )
    
    summaries = [
        SessionSummary(
            id=session.id,
            ticker=session.ticker,
            asOfDate=session.trade_date,
            status=session.status,
            createdAt=session.created_at.isoformat(),
            updatedAt=session.updated_at.isoformat() if session.updated_at else None,
        )
        for session in sessions
    ]
    
    return SessionListResponse(
        sessions=summaries,
        total=len(summaries),
        skip=skip,
        limit=limit,
    )


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_session),
    event_manager: SessionEventManager = Depends(get_event_manager),
) -> SessionDetailResponse:
    """Get a single analysis session with its recent events.
    
    Returns the session metadata along with buffered events from the event manager.
    """
    analysis_service = AnalysisSessionService(db, event_manager)
    session = await analysis_service.get_session(session_id)
    
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {session_id} not found",
        )
    
    # Get recent events from the event buffer
    events_data = analysis_service.get_session_events(session_id)
    events = [
        BufferedSessionEvent(timestamp=e["timestamp"], event=e["event"])
        for e in events_data
    ]
    
    summary = SessionSummary(
        id=session.id,
        ticker=session.ticker,
        asOfDate=session.trade_date,
        status=session.status,
        createdAt=session.created_at.isoformat(),
        updatedAt=session.updated_at.isoformat() if session.updated_at else None,
    )
    
    return SessionDetailResponse(session=summary, events=events)
