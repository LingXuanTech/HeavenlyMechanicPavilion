"""Portfolio repository for database operations."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
