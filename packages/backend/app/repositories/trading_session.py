"""Trading session repository for database operations."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import TradingSession
from .base import BaseRepository


class TradingSessionRepository(BaseRepository[TradingSession]):
    """Repository for TradingSession operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(TradingSession, session)

    async def get_by_portfolio(
        self, portfolio_id: int, *, skip: int = 0, limit: int = 100
    ) -> List[TradingSession]:
        """Get all trading sessions for a portfolio.
        
        Args:
            portfolio_id: The portfolio ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of trading sessions
        """
        statement = (
            select(TradingSession)
            .where(TradingSession.portfolio_id == portfolio_id)
            .order_by(TradingSession.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_active_sessions(
        self, *, skip: int = 0, limit: int = 100
    ) -> List[TradingSession]:
        """Get all active trading sessions.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of active trading sessions
        """
        statement = (
            select(TradingSession)
            .where(TradingSession.status == "ACTIVE")
            .order_by(TradingSession.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_status(
        self, status: str, *, skip: int = 0, limit: int = 100
    ) -> List[TradingSession]:
        """Get trading sessions by status.
        
        Args:
            status: The session status
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of trading sessions
        """
        statement = (
            select(TradingSession)
            .where(TradingSession.status == status)
            .order_by(TradingSession.started_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
