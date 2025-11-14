"""Enhanced streaming endpoints with database persistence support."""

from __future__ import annotations

import json
from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse

from ..dependencies import get_event_manager, get_graph_service
from ..schemas.sessions import SessionEvent, SessionEventsHistoryResponse
from ..security.dependencies import get_current_active_user
from ..services.events_enhanced import EnhancedSessionEventManager
from ..services.graph import TradingGraphService

router = APIRouter()


async def _event_generator(queue) -> AsyncGenerator[str, None]:
    """Generate SSE events from queue."""
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
    current_user=Depends(get_current_active_user),
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
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Unknown session"
        ) from exc

    return StreamingResponse(
        _event_generator(queue),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/{session_id}/events-history")
async def session_events_history(
    session_id: str,
    skip: int = Query(0, ge=0, description="Number of events to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum events to return"),
    order_by: str = Query("asc", regex="^(asc|desc)$", description="Sort order"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    source: str = Query("db", regex="^(db|memory)$", description="Data source: 'db' for database, 'memory' for in-memory buffer"),
    event_manager: EnhancedSessionEventManager = Depends(get_event_manager),
    current_user=Depends(get_current_active_user),
):
    """Retrieve event history for a session with pagination.

    This endpoint supports two data sources:
    - 'db': Persistent database storage (default, survives restarts)
    - 'memory': In-memory buffer (fast, limited to recent events)

    Requires authentication.

    Args:
        session_id: Session identifier
        skip: Number of events to skip for pagination
        limit: Maximum number of events to return (1-1000)
        order_by: Sort order ('asc' for oldest first, 'desc' for newest first)
        event_type: Optional filter by event type
        source: Data source ('db' or 'memory')
        event_manager: Enhanced session event manager
        current_user: Authenticated user

    Returns:
        SessionEventsHistoryResponse with events and pagination metadata
    """
    if source == "memory":
        # Fast in-memory access (limited to buffer size)
        recent_events = event_manager.get_recent_events(session_id)
        
        # Apply client-side pagination to in-memory events
        total = len(recent_events)
        paginated_events = recent_events[skip : skip + limit]
        
        return {
            "session_id": session_id,
            "events": paginated_events,
            "count": len(paginated_events),
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": skip + len(paginated_events) < total,
            "source": "memory",
        }
    else:
        # Database access (complete history with efficient pagination)
        try:
            events, total = await event_manager.get_events_from_db(
                session_id=session_id,
                skip=skip,
                limit=limit,
                order_by=order_by,
                event_type=event_type,
            )
            
            # Convert DB models to response format
            event_dicts = [
                {
                    "timestamp": event.timestamp.isoformat(),
                    "event": {
                        "type": event.event_type,
                        "message": event.message,
                        "agent_name": event.agent_name,
                        "status": event.status,
                        "payload": event.payload,
                    },
                    "sequence_number": event.sequence_number,
                }
                for event in events
            ]
            
            return {
                "session_id": session_id,
                "events": event_dicts,
                "count": len(event_dicts),
                "total": total,
                "skip": skip,
                "limit": limit,
                "has_more": skip + len(event_dicts) < total,
                "source": "database",
                "filters": {
                    "event_type": event_type,
                    "order_by": order_by,
                },
            }
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to retrieve events from database: {str(e)}",
            )


@router.delete("/{session_id}/events")
async def delete_session_events(
    session_id: str,
    event_manager: EnhancedSessionEventManager = Depends(get_event_manager),
    current_user=Depends(get_current_active_user),
):
    """Delete all events for a session.

    This endpoint removes all persisted events from the database.
    In-memory buffers are not affected.

    Requires authentication.

    Args:
        session_id: Session identifier
        event_manager: Enhanced session event manager
        current_user: Authenticated user

    Returns:
        Deletion status and count
    """
    try:
        deleted_count = await event_manager.delete_session_events(session_id)
        return {
            "session_id": session_id,
            "deleted_count": deleted_count,
            "message": f"Successfully deleted {deleted_count} events",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete events: {str(e)}",
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
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION, reason="Missing authentication token"
        )
        return

    # Verify token
    try:
        from ..security.auth import verify_access_token

        payload = verify_access_token(token)
        if not payload:
            await websocket.close(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid authentication token",
            )
            return
    except Exception:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION, reason="Authentication failed"
        )
        return

    await websocket.accept()

    try:
        queue = await service.ensure_session_stream(session_id)
    except KeyError:
        await websocket.close(
            code=status.WS_1008_POLICY_VIOLATION, reason="Unknown session"
        )
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