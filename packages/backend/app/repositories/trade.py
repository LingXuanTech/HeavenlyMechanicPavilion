"""Trade repository for database operations."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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

    async def get_by_status(self, status: str, *, skip: int = 0, limit: int = 100) -> List[Trade]:
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
    
    async def get_by_session(
        self, session_id: int, *, skip: int = 0, limit: int = 100
    ) -> List[Trade]:
        """Get all trades for a trading session.
        
        Args:
            session_id: The trading session ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of trades
        """
        statement = (
            select(Trade)
            .where(Trade.session_id == session_id)
            .order_by(Trade.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
    
    async def get_with_executions(self, trade_id: int) -> Optional[Trade]:
        """Get a trade with its executions eagerly loaded.
        
        This method uses selectinload to avoid N+1 query problems.
        
        Args:
            trade_id: The trade ID
            
        Returns:
            The trade with executions loaded, None if not found
        """
        statement = (
            select(Trade)
            .where(Trade.id == trade_id)
            .options(selectinload(Trade.executions))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
    
    async def get_by_portfolio_with_executions(
        self, portfolio_id: int, *, skip: int = 0, limit: int = 100
    ) -> List[Trade]:
        """Get all trades for a portfolio with executions eagerly loaded.
        
        This method uses selectinload to avoid N+1 query problems when
        you need to access execution details for multiple trades.
        
        Args:
            portfolio_id: The portfolio ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of trades with executions loaded
        """
        statement = (
            select(Trade)
            .where(Trade.portfolio_id == portfolio_id)
            .options(selectinload(Trade.executions))
            .order_by(Trade.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
