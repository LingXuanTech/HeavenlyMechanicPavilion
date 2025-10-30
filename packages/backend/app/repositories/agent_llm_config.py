"""Repository for managing AgentLLMConfig records."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import AgentLLMConfig
from .base import BaseRepository


class AgentLLMConfigRepository(BaseRepository[AgentLLMConfig]):
    """Data access layer for agent-level LLM configuration."""

    def __init__(self, session: AsyncSession):
        super().__init__(AgentLLMConfig, session)

    async def get_by_agent_id(self, agent_id: int) -> Optional[AgentLLMConfig]:
        """Fetch the LLM configuration for a specific agent."""
        statement = (
            select(AgentLLMConfig)
            .where(AgentLLMConfig.agent_id == agent_id)
            .options(selectinload(AgentLLMConfig.agent))
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_enabled(self) -> List[AgentLLMConfig]:
        """List all enabled LLM configurations."""
        statement = (
            select(AgentLLMConfig)
            .where(AgentLLMConfig.enabled == True)
            .options(selectinload(AgentLLMConfig.agent))
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_by_provider(self, provider: str) -> List[AgentLLMConfig]:
        """List configurations filtered by provider name."""
        statement = (
            select(AgentLLMConfig)
            .where(AgentLLMConfig.provider == provider)
            .options(selectinload(AgentLLMConfig.agent))
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())
