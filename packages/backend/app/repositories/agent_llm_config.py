"""Repository for AgentLLMConfig database operations."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models.agent_llm_config import AgentLLMConfig
from .base import BaseRepository


class AgentLLMConfigRepository(BaseRepository[AgentLLMConfig]):
    """Repository for AgentLLMConfig CRUD operations."""

    def __init__(self, session: AsyncSession):
        """Initialize the repository.

        Args:
            session: The async database session
        """
        super().__init__(AgentLLMConfig, session)

    async def get_by_agent_id(self, agent_id: int) -> List[AgentLLMConfig]:
        """Get all LLM configs for a specific agent.

        Args:
            agent_id: The agent ID

        Returns:
            List of LLM configs for the agent
        """
        statement = select(AgentLLMConfig).where(AgentLLMConfig.agent_id == agent_id)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_enabled_by_agent_id(self, agent_id: int) -> List[AgentLLMConfig]:
        """Get all enabled LLM configs for a specific agent.

        Args:
            agent_id: The agent ID

        Returns:
            List of enabled LLM configs
        """
        statement = (
            select(AgentLLMConfig)
            .where(AgentLLMConfig.agent_id == agent_id)
            .where(AgentLLMConfig.enabled == True)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_by_provider(self, provider: str) -> List[AgentLLMConfig]:
        """Get all LLM configs for a specific provider.

        Args:
            provider: The provider name

        Returns:
            List of LLM configs for the provider
        """
        statement = select(AgentLLMConfig).where(AgentLLMConfig.provider == provider)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_primary_config(self, agent_id: int) -> Optional[AgentLLMConfig]:
        """Get the primary (first enabled) LLM config for an agent.

        Args:
            agent_id: The agent ID

        Returns:
            The primary LLM config, or None if not found
        """
        statement = (
            select(AgentLLMConfig)
            .where(AgentLLMConfig.agent_id == agent_id)
            .where(AgentLLMConfig.enabled == True)
            .limit(1)
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
