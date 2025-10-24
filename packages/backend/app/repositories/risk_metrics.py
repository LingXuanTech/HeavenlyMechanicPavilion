"""Risk metrics repository for database operations."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import RiskMetrics
from .base import BaseRepository


class RiskMetricsRepository(BaseRepository[RiskMetrics]):
    """Repository for RiskMetrics operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(RiskMetrics, session)

    async def get_by_portfolio(
        self, portfolio_id: int, *, skip: int = 0, limit: int = 100
    ) -> List[RiskMetrics]:
        """Get risk metrics for a portfolio.
        
        Args:
            portfolio_id: The portfolio ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of risk metrics
        """
        statement = (
            select(RiskMetrics)
            .where(RiskMetrics.portfolio_id == portfolio_id)
            .order_by(RiskMetrics.measured_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_latest_by_portfolio(
        self, portfolio_id: int
    ) -> Optional[RiskMetrics]:
        """Get the latest risk metrics for a portfolio.
        
        Args:
            portfolio_id: The portfolio ID
            
        Returns:
            Latest risk metrics if found, None otherwise
        """
        statement = (
            select(RiskMetrics)
            .where(RiskMetrics.portfolio_id == portfolio_id)
            .order_by(RiskMetrics.measured_at.desc())
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_session(
        self, session_id: int, *, skip: int = 0, limit: int = 100
    ) -> List[RiskMetrics]:
        """Get risk metrics for a trading session.
        
        Args:
            session_id: The trading session ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of risk metrics
        """
        statement = (
            select(RiskMetrics)
            .where(RiskMetrics.session_id == session_id)
            .order_by(RiskMetrics.measured_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
