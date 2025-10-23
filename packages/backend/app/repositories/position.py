"""Position repository for database operations."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Position
from .base import BaseRepository


class PositionRepository(BaseRepository[Position]):
    """Repository for Position operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Position, session)

    async def get_by_portfolio(self, portfolio_id: int) -> List[Position]:
        """Get all positions for a portfolio.
        
        Args:
            portfolio_id: The portfolio ID
            
        Returns:
            List of positions
        """
        statement = select(Position).where(Position.portfolio_id == portfolio_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_symbol(
        self, portfolio_id: int, symbol: str
    ) -> Optional[Position]:
        """Get a position by portfolio and symbol.
        
        Args:
            portfolio_id: The portfolio ID
            symbol: The symbol
            
        Returns:
            The position if found, None otherwise
        """
        statement = select(Position).where(
            Position.portfolio_id == portfolio_id,
            Position.symbol == symbol,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
