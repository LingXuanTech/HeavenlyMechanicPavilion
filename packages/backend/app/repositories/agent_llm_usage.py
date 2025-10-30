"""Repository for recording AgentLLMUsage metrics."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import AgentLLMUsage
from .base import BaseRepository


class AgentLLMUsageRepository(BaseRepository[AgentLLMUsage]):
    """Provides CRUD helpers for LLM usage records."""

    def __init__(self, session: AsyncSession):
        super().__init__(AgentLLMUsage, session)

    async def create_many(self, usage_events: Iterable[AgentLLMUsage]) -> None:
        """Bulk insert multiple usage events."""
        self.session.add_all(list(usage_events))
        await self.session.commit()

    async def recent_usage(
        self,
        *,
        agent_id: Optional[int] = None,
        provider: Optional[str] = None,
        window_hours: int = 24,
    ) -> List[AgentLLMUsage]:
        """Return usage records for a recent time window."""
        cutoff = datetime.utcnow() - timedelta(hours=window_hours)
        statement = select(AgentLLMUsage).where(AgentLLMUsage.created_at >= cutoff)

        if agent_id is not None:
            statement = statement.where(AgentLLMUsage.agent_id == agent_id)
        if provider is not None:
            statement = statement.where(AgentLLMUsage.provider == provider)

        statement = statement.order_by(AgentLLMUsage.created_at.desc())
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def aggregate_totals(
        self,
        *,
        agent_id: Optional[int] = None,
        provider: Optional[str] = None,
    ) -> dict[str, float]:
        """Aggregate cost and token counts for filters."""
        statement = select(
            func.coalesce(func.sum(AgentLLMUsage.prompt_tokens), 0),
            func.coalesce(func.sum(AgentLLMUsage.completion_tokens), 0),
            func.coalesce(func.sum(AgentLLMUsage.total_tokens), 0),
            func.coalesce(func.sum(AgentLLMUsage.cost), 0.0),
            func.count(AgentLLMUsage.id),
        )

        if agent_id is not None:
            statement = statement.where(AgentLLMUsage.agent_id == agent_id)
        if provider is not None:
            statement = statement.where(AgentLLMUsage.provider == provider)

        result = await self.session.execute(statement)
        prompt_tokens, completion_tokens, total_tokens, total_cost, calls = result.one()

        return {
            "prompt_tokens": float(prompt_tokens or 0),
            "completion_tokens": float(completion_tokens or 0),
            "total_tokens": float(total_tokens or 0),
            "total_cost": float(total_cost or 0.0),
            "api_calls": float(calls or 0),
        }
