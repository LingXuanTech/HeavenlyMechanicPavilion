"""Execution repository for database operations."""

from __future__ import annotations

from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Execution
from .base import BaseRepository


class ExecutionRepository(BaseRepository[Execution]):
    """Repository for Execution operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(Execution, session)

    async def get_by_trade(self, trade_id: int) -> List[Execution]:
        """Get all executions for a trade.

        Args:
            trade_id: The trade ID

        Returns:
            List of executions
        """
        statement = (
            select(Execution)
            .where(Execution.trade_id == trade_id)
            .order_by(Execution.executed_at.desc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
