import asyncio
import json
from typing import AsyncGenerator
from sse_starlette.sse import EventSourceResponse

class SSEManager:
    @staticmethod
    async def create_event(event_type: str, data: dict) -> str:
        return json.dumps({
            "event": event_type,
            "data": data
        })

    @staticmethod
    async def stream_events(generator: AsyncGenerator) -> EventSourceResponse:
        return EventSourceResponse(generator)

sse_manager = SSEManager()
