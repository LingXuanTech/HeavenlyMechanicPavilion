"""RunLog repository for database operations."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import RunLog
from .base import BaseRepository


class RunLogRepository(BaseRepository[RunLog]):
    """Repository for RunLog operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(RunLog, session)

    async def get_by_session_id(self, session_id: str) -> Optional[RunLog]:
        """Get a run log by session ID.
        
        Args:
            session_id: The session ID
            
        Returns:
            The run log if found, None otherwise
        """
        statement = select(RunLog).where(RunLog.session_id == session_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_status(
        self, status: str, *, skip: int = 0, limit: int = 100
    ) -> List[RunLog]:
        """Get run logs by status.
        
        Args:
            status: The run status
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of run logs
        """
        statement = (
            select(RunLog)
            .where(RunLog.status == status)
            .order_by(RunLog.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_recent(
        self, *, skip: int = 0, limit: int = 100
    ) -> List[RunLog]:
        """Get recent run logs.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of run logs
        """
        statement = (
            select(RunLog)
            .order_by(RunLog.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
