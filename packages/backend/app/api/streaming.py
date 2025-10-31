"""Real-time data streaming endpoints."""

from __future__ import annotations

import json
import logging
from typing import AsyncGenerator, List, Optional

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse

from ..cache import RedisManager, get_redis_manager
from ..dependencies import get_settings
from ..schemas.streaming import DataType, StreamMessage, StreamSubscription

logger = logging.getLogger(__name__)

router = APIRouter()


async def _redis_event_generator(
    redis: RedisManager,
    channels: List[str],
    data_types: Optional[List[DataType]] = None,
    symbols: Optional[List[str]] = None,
) -> AsyncGenerator[str, None]:
    """Generate SSE events from Redis pub/sub.

    Args:
        redis: Redis manager
        channels: Redis channels to subscribe to
        data_types: Optional filter by data types
        symbols: Optional filter by symbols

    Yields:
        SSE formatted events
    """
    pubsub = await redis.subscribe(*channels)

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue

            try:
                # Parse message
                data = json.loads(message["data"])
                stream_msg = StreamMessage(**data)

                # Apply filters
                if data_types and stream_msg.data_type not in data_types:
                    continue

                if symbols and stream_msg.symbol not in symbols:
                    continue

                # Format as SSE
                yield f"event: {stream_msg.data_type.value}\n"
                yield f"data: {json.dumps(stream_msg.model_dump(), default=str)}\n\n"

            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                continue

    finally:
        await pubsub.unsubscribe(*channels)
        await pubsub.close()


@router.post("/subscribe/sse")
async def subscribe_sse(
    subscription: StreamSubscription,
    redis: Optional[RedisManager] = Depends(get_redis_manager),
    settings=Depends(get_settings),
):
    """Subscribe to real-time data streams via Server-Sent Events.

    Args:
        subscription: Subscription configuration
        redis: Redis manager
        settings: Application settings

    Returns:
        StreamingResponse with SSE events
    """
    if not settings.redis_enabled or not redis:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis streaming is not enabled",
        )

    if not subscription.channels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one channel must be specified",
        )

    return StreamingResponse(
        _redis_event_generator(
            redis,
            subscription.channels,
            subscription.data_types,
            subscription.symbols,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.websocket("/ws")
async def streaming_websocket(
    websocket: WebSocket,
    channels: str = "stream:market_data",
    data_types: Optional[str] = None,
    symbols: Optional[str] = None,
):
    """WebSocket endpoint for real-time data streaming.

    Args:
        websocket: WebSocket connection
        channels: Comma-separated list of channels
        data_types: Optional comma-separated list of data types to filter
        symbols: Optional comma-separated list of symbols to filter
    """
    await websocket.accept()

    # Get Redis manager
    redis = get_redis_manager()
    if not redis:
        await websocket.send_json(
            {
                "type": "error",
                "message": "Redis streaming is not enabled",
            }
        )
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        return

    # Parse parameters
    channel_list = [c.strip() for c in channels.split(",") if c.strip()]
    data_type_list = None
    if data_types:
        data_type_list = [DataType(dt.strip()) for dt in data_types.split(",") if dt.strip()]
    symbol_list = None
    if symbols:
        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]

    # Subscribe to channels
    pubsub = await redis.subscribe(*channel_list)

    try:
        # Send initial connection message
        await websocket.send_json(
            {
                "type": "connected",
                "channels": channel_list,
                "filters": {
                    "data_types": [dt.value for dt in data_type_list] if data_type_list else None,
                    "symbols": symbol_list,
                },
            }
        )

        # Listen for messages
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue

            try:
                # Parse message
                data = json.loads(message["data"])
                stream_msg = StreamMessage(**data)

                # Apply filters
                if data_type_list and stream_msg.data_type not in data_type_list:
                    continue

                if symbol_list and stream_msg.symbol not in symbol_list:
                    continue

                # Send to client
                await websocket.send_json(
                    {
                        "type": "data",
                        "message": stream_msg.model_dump(),
                    }
                )

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": str(e),
                    }
                )

    except WebSocketDisconnect:
        logger.info("Client disconnected from streaming WebSocket")

    finally:
        await pubsub.unsubscribe(*channel_list)
        await pubsub.close()
        await websocket.close()


@router.get("/channels")
async def list_channels(
    redis: Optional[RedisManager] = Depends(get_redis_manager),
    settings=Depends(get_settings),
):
    """List available streaming channels.

    Returns:
        List of available channels
    """
    if not settings.redis_enabled or not redis:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis streaming is not enabled",
        )

    # Return predefined channels
    channels = []
    for data_type in DataType:
        channels.append(
            {
                "channel": f"stream:{data_type.value}",
                "data_type": data_type.value,
                "pattern": f"stream:{data_type.value}:*",
            }
        )

    return {"channels": channels}


@router.get("/latest/{channel}")
async def get_latest(
    channel: str,
    redis: Optional[RedisManager] = Depends(get_redis_manager),
    settings=Depends(get_settings),
):
    """Get the latest cached message for a channel.

    Args:
        channel: Channel name
        redis: Redis manager
        settings: Application settings

    Returns:
        Latest message or null if not found
    """
    if not settings.redis_enabled or not redis:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis streaming is not enabled",
        )

    cache_key = f"latest:{channel}"
    data = await redis.get(cache_key)

    if not data:
        return {"message": None}

    try:
        message_data = json.loads(data)
        return {"message": message_data}
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to parse cached message",
        )
