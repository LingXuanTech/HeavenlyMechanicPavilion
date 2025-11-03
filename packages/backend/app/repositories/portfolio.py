"""Portfolio repository for database operations."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..db.models import Portfolio
from .base import BaseRepository


class PortfolioRepository(BaseRepository[Portfolio]):
    """Repository for Portfolio operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Portfolio, session)

    async def get_by_name(self, name: str) -> Optional[Portfolio]:
        """Get a portfolio by name.

        Args:
            name: The portfolio name

        Returns:
            The portfolio if found, None otherwise
        """
        statement = select(Portfolio).where(Portfolio.name == name)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
    
    async def get_with_positions(self, portfolio_id: int) -> Optional[Portfolio]:
        """Get a portfolio with its positions eagerly loaded.
        
        This method uses selectinload to avoid N+1 query problems.
        
        Args:
            portfolio_id: The portfolio ID
            
        Returns:
            The portfolio with positions loaded, None if not found
        """
        statement = (
            select(Portfolio)
            .where(Portfolio.id == portfolio_id)
            .options(selectinload(Portfolio.positions))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
    
    async def get_with_trades(self, portfolio_id: int) -> Optional[Portfolio]:
        """Get a portfolio with its trades eagerly loaded.
        
        This method uses selectinload to avoid N+1 query problems.
        
        Args:
            portfolio_id: The portfolio ID
            
        Returns:
            The portfolio with trades loaded, None if not found
        """
        statement = (
            select(Portfolio)
            .where(Portfolio.id == portfolio_id)
            .options(selectinload(Portfolio.trades))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
    
    async def get_with_all_relations(self, portfolio_id: int) -> Optional[Portfolio]:
        """Get a portfolio with all its relationships eagerly loaded.
        
        This method uses selectinload to avoid N+1 query problems.
        
        Args:
            portfolio_id: The portfolio ID
            
        Returns:
            The portfolio with all relationships loaded, None if not found
        """
        statement = (
            select(Portfolio)
            .where(Portfolio.id == portfolio_id)
            .options(
                selectinload(Portfolio.positions),
                selectinload(Portfolio.trades),
            )
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
