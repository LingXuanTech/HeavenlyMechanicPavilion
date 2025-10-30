"""Repository for AgentLLMUsage persistence operations."""

from __future__ import annotations

from typing import List, Optional
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models.agent_llm_usage import AgentLLMUsage
from .base import BaseRepository


class AgentLLMUsageRepository(BaseRepository[AgentLLMUsage]):
    """CRUD helpers for ``AgentLLMUsage`` records."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AgentLLMUsage, session)

    async def list_by_agent(
        self,
        agent_id: int,
        *,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AgentLLMUsage]:
        statement = select(AgentLLMUsage).where(AgentLLMUsage.agent_id == agent_id)

        if start is not None:
            statement = statement.where(AgentLLMUsage.created_at >= start)
        if end is not None:
            statement = statement.where(AgentLLMUsage.created_at <= end)

        statement = statement.order_by(AgentLLMUsage.created_at.desc()).limit(limit)

        result = await self.session.execute(statement)
        return list(result.scalars().all())
