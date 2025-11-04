"""Event streaming utilities backed by in-memory queues.

These helpers mimic the interface that will eventually be backed by Redis
pub/sub. For now they maintain per-session asyncio queues that allow both SSE
and WebSocket transports to consume the same stream of events.
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from threading import RLock
from typing import Any, Deque, Dict, List


@dataclass
class SessionStream:
    """Container linking a queue with the event loop that owns it."""

    queue: "asyncio.Queue[Any]"
    loop: asyncio.AbstractEventLoop


@dataclass
class TimestampedEvent:
    """Container for an event with its enqueue timestamp."""

    timestamp: datetime
    event: Any


class SessionEventManager:
    """Simple in-memory session event manager.

    The manager keeps an asyncio queue per session and exposes helpers to
    publish structured events to those queues. The queues are designed to be
    consumed by SSE or WebSocket endpoints. Once Redis is introduced, this
    manager can be swapped with a pub/sub implementation while keeping the API
    surface stable for the FastAPI routes.

    Additionally, the manager maintains a bounded buffer of recent events per
    session to enable REST clients to retrieve event history after the stream
    has completed.
    """

    def __init__(self, max_buffer_size: int = 100) -> None:
        self._streams: Dict[str, SessionStream] = {}
        self._event_buffers: Dict[str, Deque[TimestampedEvent]] = {}
        self._lock = RLock()
        self._max_buffer_size = max_buffer_size

    async def create_stream(self, session_id: str) -> "asyncio.Queue[Any]":
        """Create a new queue for the session and register it."""

        queue: "asyncio.Queue[Any]" = asyncio.Queue()
        loop = asyncio.get_running_loop()
        with self._lock:
            self._streams[session_id] = SessionStream(queue=queue, loop=loop)
            self._event_buffers[session_id] = deque(maxlen=self._max_buffer_size)
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
        
        The event is also added to the session's event buffer with a timestamp.
        """

        stream = self._streams.get(session_id)
        if not stream:
            return False

        with self._lock:
            buffer = self._event_buffers.get(session_id)
            if buffer is not None:
                buffer.append(TimestampedEvent(timestamp=datetime.now(), event=event))

        asyncio.run_coroutine_threadsafe(stream.queue.put(event), stream.loop)
        return True

    def close(self, session_id: str) -> None:
        """Signal the consumer that the session has ended and drop the queue.
        
        The event buffer is preserved for later retrieval via get_recent_events.
        """

        with self._lock:
            stream = self._streams.pop(session_id, None)
        if not stream:
            return

        asyncio.run_coroutine_threadsafe(stream.queue.put(None), stream.loop)

    def get_recent_events(self, session_id: str) -> List[dict]:
        """Retrieve the buffered events for a session.

        Returns a list of dicts with 'timestamp' and 'event' keys, ordered from
        oldest to most recent. Returns an empty list if the session has no buffer.
        
        This method is thread-safe and can be called after the stream closes.
        """

        with self._lock:
            buffer = self._event_buffers.get(session_id)
            if not buffer:
                return []
            return [
                {
                    "timestamp": te.timestamp.isoformat(),
                    "event": te.event,
                }
                for te in buffer
            ]
