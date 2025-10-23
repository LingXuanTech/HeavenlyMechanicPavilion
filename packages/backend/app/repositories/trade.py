"""Trade repository for database operations."""

from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Trade
from .base import BaseRepository


class TradeRepository(BaseRepository[Trade]):
    """Repository for Trade operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Trade, session)

    async def get_by_portfolio(
        self, portfolio_id: int, *, skip: int = 0, limit: int = 100
    ) -> List[Trade]:
        """Get all trades for a portfolio.
        
        Args:
            portfolio_id: The portfolio ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of trades
        """
        statement = (
            select(Trade)
            .where(Trade.portfolio_id == portfolio_id)
            .order_by(Trade.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_status(
        self, status: str, *, skip: int = 0, limit: int = 100
    ) -> List[Trade]:
        """Get trades by status.
        
        Args:
            status: The trade status
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of trades
        """
        statement = (
            select(Trade)
            .where(Trade.status == status)
            .order_by(Trade.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
