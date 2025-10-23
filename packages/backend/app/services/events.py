"""Event streaming utilities backed by in-memory queues.

These helpers mimic the interface that will eventually be backed by Redis
pub/sub. For now they maintain per-session asyncio queues that allow both SSE
and WebSocket transports to consume the same stream of events.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from threading import RLock
from typing import Any, Dict


@dataclass
class SessionStream:
    """Container linking a queue with the event loop that owns it."""

    queue: "asyncio.Queue[Any]"
    loop: asyncio.AbstractEventLoop


class SessionEventManager:
    """Simple in-memory session event manager.

    The manager keeps an asyncio queue per session and exposes helpers to
    publish structured events to those queues. The queues are designed to be
    consumed by SSE or WebSocket endpoints. Once Redis is introduced, this
    manager can be swapped with a pub/sub implementation while keeping the API
    surface stable for the FastAPI routes.
    """

    def __init__(self) -> None:
        self._streams: Dict[str, SessionStream] = {}
        self._lock = RLock()

    async def create_stream(self, session_id: str) -> "asyncio.Queue[Any]":
        """Create a new queue for the session and register it."""

        queue: "asyncio.Queue[Any]" = asyncio.Queue()
        loop = asyncio.get_running_loop()
        with self._lock:
            self._streams[session_id] = SessionStream(queue=queue, loop=loop)
        return queue

    async def get_stream(self, session_id: str) -> "asyncio.Queue[Any]":
        """Return the queue associated with the session."""

        with self._lock:
            stream = self._streams.get(session_id)
        if not stream:
            raise KeyError(session_id)
        return stream.queue

    def publish(self, session_id: str, event: Any) -> bool:
        """Publish an event to the session queue.

        Returns ``True`` if the event was enqueued. Thread-safe by proxy when
        called from worker threads thanks to ``run_coroutine_threadsafe``.
        """

        stream = self._streams.get(session_id)
        if not stream:
            return False

        asyncio.run_coroutine_threadsafe(stream.queue.put(event), stream.loop)
        return True

    def close(self, session_id: str) -> None:
        """Signal the consumer that the session has ended and drop the queue."""

        with self._lock:
            stream = self._streams.pop(session_id, None)
        if not stream:
            return

        asyncio.run_coroutine_threadsafe(stream.queue.put(None), stream.loop)
