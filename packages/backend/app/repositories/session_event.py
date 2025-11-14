"""Repository for session event persistence."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models.session_event import SessionEvent
from .base import BaseRepository


class SessionEventRepository(BaseRepository[SessionEvent]):
    """Repository for session event CRUD operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(SessionEvent, session)

    async def get_by_session(
        self,
        session_id: str,
        skip: int = 0,
        limit: int = 100,
        order_by: str = "asc",
    ) -> List[SessionEvent]:
        """Get events for a session with pagination.
        
        Args:
            session_id: The session identifier
            skip: Number of events to skip
            limit: Maximum number of events to return
            order_by: Sort order, "asc" or "desc"
            
        Returns:
            List of session events
        """
        query = select(SessionEvent).where(SessionEvent.session_id == session_id)
        
        if order_by == "desc":
            query = query.order_by(SessionEvent.sequence_number.desc())
        else:
            query = query.order_by(SessionEvent.sequence_number.asc())
        
        query = query.offset(skip).limit(limit)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_session_and_type(
        self,
        session_id: str,
        event_type: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[SessionEvent]:
        """Get events for a session filtered by type.
        
        Args:
            session_id: The session identifier
            event_type: Event type to filter by
            skip: Number of events to skip
            limit: Maximum number of events to return
            
        Returns:
            List of session events matching the type
        """
        query = (
            select(SessionEvent)
            .where(SessionEvent.session_id == session_id)
            .where(SessionEvent.event_type == event_type)
            .order_by(SessionEvent.sequence_number.asc())
            .offset(skip)
            .limit(limit)
        )
        
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_by_session(self, session_id: str) -> int:
        """Count total events for a session.
        
        Args:
            session_id: The session identifier
            
        Returns:
            Total number of events
        """
        query = select(func.count()).select_from(SessionEvent).where(
            SessionEvent.session_id == session_id
        )
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_next_sequence_number(self, session_id: str) -> int:
        """Get the next sequence number for a session.
        
        Args:
            session_id: The session identifier
            
        Returns:
            Next sequence number (0 for first event)
        """
        query = select(func.max(SessionEvent.sequence_number)).where(
            SessionEvent.session_id == session_id
        )
        result = await self.session.execute(query)
        max_seq = result.scalar()
        return 0 if max_seq is None else max_seq + 1

    async def bulk_create(self, events: List[SessionEvent]) -> List[SessionEvent]:
        """Create multiple events in a single transaction.
        
        Args:
            events: List of session events to create
            
        Returns:
            List of created events
        """
        self.session.add_all(events)
        await self.session.commit()
        for event in events:
            await self.session.refresh(event)
        return events

    async def delete_by_session(self, session_id: str) -> int:
        """Delete all events for a session.
        
        Args:
            session_id: The session identifier
            
        Returns:
            Number of events deleted
        """
        query = select(SessionEvent).where(SessionEvent.session_id == session_id)
        result = await self.session.execute(query)
        events = result.scalars().all()
        
        count = len(events)
        for event in events:
            await self.session.delete(event)
        
        await self.session.commit()
        return count