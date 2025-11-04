"""Streaming endpoints for sessions."""

from __future__ import annotations

import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse

from ..dependencies import get_event_manager, get_graph_service
from ..schemas.sessions import SessionEvent, SessionEventsHistoryResponse
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
):
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
) -> SessionEventsHistoryResponse:
    """Retrieve recent events buffered for a completed session.
    
    This endpoint allows REST clients to retrieve event history after a session
    has completed and the stream has closed. Events are stored in a bounded
    buffer with the most recent events preserved up to a configurable limit.
    
    Args:
        session_id: The session identifier
        event_manager: The session event manager instance
        
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
    service: TradingGraphService = Depends(get_graph_service),
) -> None:
    await websocket.accept()

    try:
        queue = await service.ensure_session_stream(session_id)
    except KeyError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
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
