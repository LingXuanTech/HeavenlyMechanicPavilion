"""Enhanced event streaming utilities with database persistence.

This module extends the original in-memory event manager to support database
persistence while maintaining backward compatibility with the existing API.
"""

from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from threading import RLock
from typing import Any, Deque, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models.session_event import SessionEvent
from ..repositories.session_event import SessionEventRepository


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


class EnhancedSessionEventManager:
    """Session event manager with database persistence support.

    This manager extends the original in-memory approach by optionally persisting
    events to the database. It maintains backward compatibility by keeping the
    in-memory buffer for fast access while asynchronously writing to the database.

    Features:
    - In-memory buffer for fast real-time access
    - Asynchronous database persistence
    - Paginated event history retrieval
    - Thread-safe operations
    - Configurable persistence behavior
    """

    def __init__(
        self,
        db_session_factory: callable,
        max_buffer_size: int = 100,
        persist_to_db: bool = True,
    ) -> None:
        """Initialize the enhanced event manager.

        Args:
            db_session_factory: Factory function to create database sessions
            max_buffer_size: Maximum number of events to keep in memory per session
            persist_to_db: Whether to persist events to database
        """
        self._streams: Dict[str, SessionStream] = {}
        self._event_buffers: Dict[str, Deque[TimestampedEvent]] = {}
        self._sequence_numbers: Dict[str, int] = {}
        self._lock = RLock()
        self._max_buffer_size = max_buffer_size
        self._persist_to_db = persist_to_db
        self._db_session_factory = db_session_factory

    async def create_stream(self, session_id: str) -> "asyncio.Queue[Any]":
        """Create a new queue for the session and register it.

        Args:
            session_id: Session identifier

        Returns:
            AsyncIO queue for the session
        """
        queue: "asyncio.Queue[Any]" = asyncio.Queue()
        loop = asyncio.get_running_loop()
        with self._lock:
            self._streams[session_id] = SessionStream(queue=queue, loop=loop)
            self._event_buffers[session_id] = deque(maxlen=self._max_buffer_size)
            self._sequence_numbers[session_id] = 0
        return queue

    async def get_stream(self, session_id: str) -> "asyncio.Queue[Any]":
        """Return the queue associated with the session.

        Args:
            session_id: Session identifier

        Returns:
            AsyncIO queue for the session

        Raises:
            KeyError: If session not found
        """
        with self._lock:
            stream = self._streams.get(session_id)
        if not stream:
            raise KeyError(session_id)
        return stream.queue

    def publish(
        self,
        session_id: str,
        event: Any,
        event_type: Optional[str] = None,
        message: Optional[str] = None,
        agent_name: Optional[str] = None,
        status: Optional[str] = None,
    ) -> bool:
        """Publish an event to the session queue and optionally persist to database.

        Args:
            session_id: Session identifier
            event: Event payload (must be JSON serializable)
            event_type: Type of event (e.g., "agent_start", "agent_complete")
            message: Human-readable event message
            agent_name: Name of the agent generating the event
            status: Event status ("success", "error", "pending")

        Returns:
            True if event was enqueued, False otherwise
        """
        stream = self._streams.get(session_id)
        if not stream:
            return False

        # Add to in-memory buffer with timestamp
        with self._lock:
            buffer = self._event_buffers.get(session_id)
            if buffer is not None:
                buffer.append(TimestampedEvent(timestamp=datetime.utcnow(), event=event))

        # Enqueue to asyncio queue for real-time streaming
        asyncio.run_coroutine_threadsafe(stream.queue.put(event), stream.loop)

        # Persist to database asynchronously (non-blocking)
        if self._persist_to_db:
            asyncio.run_coroutine_threadsafe(
                self._persist_event(
                    session_id=session_id,
                    event=event,
                    event_type=event_type or "generic",
                    message=message,
                    agent_name=agent_name,
                    status=status,
                ),
                stream.loop,
            )

        return True

    async def _persist_event(
        self,
        session_id: str,
        event: Any,
        event_type: str,
        message: Optional[str],
        agent_name: Optional[str],
        status: Optional[str],
    ) -> None:
        """Persist an event to the database.

        Args:
            session_id: Session identifier
            event: Event payload
            event_type: Type of event
            message: Event message
            agent_name: Agent name
            status: Event status
        """
        try:
            async with self._db_session_factory() as db_session:
                repo = SessionEventRepository(db_session)

                # Get next sequence number
                with self._lock:
                    seq_num = self._sequence_numbers.get(session_id, 0)
                    self._sequence_numbers[session_id] = seq_num + 1

                # Create event record
                db_event = SessionEvent(
                    session_id=session_id,
                    event_type=event_type,
                    message=message,
                    payload=event if isinstance(event, dict) else {"data": str(event)},
                    sequence_number=seq_num,
                    timestamp=datetime.utcnow(),
                    agent_name=agent_name,
                    status=status,
                )

                await repo.create(db_event)
        except Exception as e:
            # Log error but don't fail the event publishing
            print(f"Failed to persist event to database: {e}")

    def close(self, session_id: str) -> None:
        """Signal the consumer that the session has ended and drop the queue.

        The event buffer is preserved for later retrieval via get_recent_events.

        Args:
            session_id: Session identifier
        """
        with self._lock:
            stream = self._streams.pop(session_id, None)
        if not stream:
            return

        asyncio.run_coroutine_threadsafe(stream.queue.put(None), stream.loop)

    def get_recent_events(self, session_id: str) -> List[dict]:
        """Retrieve the buffered events for a session from memory.

        This is a fast, synchronous method for accessing recent events.
        For full event history, use get_events_from_db.

        Args:
            session_id: Session identifier

        Returns:
            List of dicts with 'timestamp' and 'event' keys
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

    async def get_events_from_db(
        self,
        session_id: str,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "asc",
        event_type: Optional[str] = None,
    ) -> tuple[List[SessionEvent], int]:
        """Retrieve events from the database with pagination.

        Args:
            session_id: Session identifier
            skip: Number of events to skip
            limit: Maximum number of events to return
            order_by: Sort order ("asc" or "desc")
            event_type: Filter by event type (optional)

        Returns:
            Tuple of (events list, total count)
        """
        async with self._db_session_factory() as db_session:
            repo = SessionEventRepository(db_session)

            if event_type:
                events = await repo.get_by_session_and_type(
                    session_id=session_id,
                    event_type=event_type,
                    skip=skip,
                    limit=limit,
                )
            else:
                events = await repo.get_by_session(
                    session_id=session_id,
                    skip=skip,
                    limit=limit,
                    order_by=order_by,
                )

            total = await repo.count_by_session(session_id)

            return events, total

    async def delete_session_events(self, session_id: str) -> int:
        """Delete all events for a session from the database.

        Args:
            session_id: Session identifier

        Returns:
            Number of events deleted
        """
        async with self._db_session_factory() as db_session:
            repo = SessionEventRepository(db_session)
            return await repo.delete_by_session(session_id)