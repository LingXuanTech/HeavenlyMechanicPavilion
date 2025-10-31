"""Streaming endpoints for sessions."""

from __future__ import annotations

import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse

from ..dependencies import get_graph_service
from ..schemas.sessions import SessionEvent
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
