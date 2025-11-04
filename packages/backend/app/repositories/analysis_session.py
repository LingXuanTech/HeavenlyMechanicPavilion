"""Repository for analysis session operations."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models.analysis_session import AnalysisSession
from .base import BaseRepository


class AnalysisSessionRepository(BaseRepository[AnalysisSession]):
    """Repository for analysis session CRUD operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(AnalysisSession, session)

    async def get_by_id(self, session_id: str) -> Optional[AnalysisSession]:
        """Get an analysis session by UUID string.

        Args:
            session_id: The session UUID string

        Returns:
            The analysis session if found, None otherwise
        """
        return await self.session.get(self.model, session_id)

    async def get_recent(
        self, *, skip: int = 0, limit: int = 50, status: Optional[str] = None
    ) -> List[AnalysisSession]:
        """Get recent analysis sessions ordered by creation date.

        Args:
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return
            status: Optional status filter (pending, running, completed, failed)

        Returns:
            List of analysis sessions ordered by created_at descending
        """
        statement = select(self.model).order_by(desc(self.model.created_at))

        if status:
            statement = statement.where(self.model.status == status)

        statement = statement.offset(skip).limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_ticker(
        self, ticker: str, *, skip: int = 0, limit: int = 50
    ) -> List[AnalysisSession]:
        """Get analysis sessions for a specific ticker.

        Args:
            ticker: The ticker symbol to filter by
            skip: Number of records to skip for pagination
            limit: Maximum number of records to return

        Returns:
            List of analysis sessions for the ticker ordered by created_at descending
        """
        statement = (
            select(self.model)
            .where(self.model.ticker == ticker)
            .order_by(desc(self.model.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
