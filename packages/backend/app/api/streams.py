"""Streaming endpoints for sessions."""

from __future__ import annotations

import json
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status, Query
from fastapi.responses import StreamingResponse

from ..dependencies import get_event_manager, get_graph_service
from ..schemas.sessions import SessionEvent, SessionEventsHistoryResponse
from ..security.dependencies import get_current_active_user
from ..services.events import SessionEventManager
from ..services.graph import TradingGraphService

router = APIRouter()


async def _event_generator(queue) -> AsyncGenerator[str, None]:
    while True:
        event = await queue.get()
        if event is None:
            yield "event: end\n\n"
            break

        payload = SessionEvent.from_raw(event).model_dump()
        yield f"data: {json.dumps(payload)}\n\n"


@router.get("/{session_id}/events")
async def session_sse(
    session_id: str,
    service: TradingGraphService = Depends(get_graph_service),
    current_user = Depends(get_current_active_user),
):
    """Server-Sent Events stream for session events.
    
    Requires authentication. Returns real-time events for the specified session.
    
    Args:
        session_id: Session identifier
        service: Trading graph service
        current_user: Authenticated user (from JWT token)
        
    Returns:
        StreamingResponse with SSE events
    """
    try:
        queue = await service.ensure_session_stream(session_id)
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown session"
        ) from exc

    return StreamingResponse(
        _event_generator(queue),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/{session_id}/events-history", response_model=SessionEventsHistoryResponse)
async def session_recent_events(
    session_id: str,
    event_manager: SessionEventManager = Depends(get_event_manager),
    current_user = Depends(get_current_active_user),
) -> SessionEventsHistoryResponse:
    """Retrieve recent events buffered for a completed session.
    
    Requires authentication. This endpoint allows REST clients to retrieve event
    history after a session has completed and the stream has closed. Events are
    stored in a bounded buffer with the most recent events preserved up to a
    configurable limit.
    
    Args:
        session_id: The session identifier
        event_manager: The session event manager instance
        current_user: Authenticated user (from JWT token)
        
    Returns:
        A response containing the session_id and a list of recent events with timestamps
    """
    recent_events = event_manager.get_recent_events(session_id)
    
    return SessionEventsHistoryResponse(
        session_id=session_id,
        events=recent_events,
        count=len(recent_events),
    )


@router.websocket("/{session_id}/ws")
async def session_ws(
    websocket: WebSocket,
    session_id: str,
    token: Optional[str] = Query(None),
    service: TradingGraphService = Depends(get_graph_service),
) -> None:
    """WebSocket endpoint for session events.
    
    Requires authentication via query parameter 'token' (JWT token).
    Example: ws://host/api/streams/{session_id}/ws?token=your_jwt_token
    
    Args:
        websocket: WebSocket connection
        session_id: Session identifier
        token: JWT authentication token (query parameter)
        service: Trading graph service
    """
    # Authenticate WebSocket connection
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication token")
        return
    
    # Verify token
    try:
        from ..security.auth import verify_access_token
        payload = verify_access_token(token)
        if not payload:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid authentication token")
            return
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed")
        return
    
    await websocket.accept()

    try:
        queue = await service.ensure_session_stream(session_id)
    except KeyError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Unknown session")
        return

    try:
        while True:
            event = await queue.get()
            if event is None:
                await websocket.send_json({"type": "end"})
                break
            await websocket.send_json(SessionEvent.from_raw(event).model_dump())
    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()
