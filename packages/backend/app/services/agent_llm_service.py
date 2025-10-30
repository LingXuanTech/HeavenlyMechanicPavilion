"""Higher-level service for agent LLM configuration API operations."""

from __future__ import annotations

from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.agent_llm_config import AgentLLMConfigResponse, AgentLLMConfigUpsert
from .agent_config import AgentConfigService
from .agent_llm_config import AgentLLMConfigService


class AgentNotFoundError(Exception):
    """Raised when an agent cannot be found."""


class AgentLLMConfigNotFoundError(Exception):
    """Raised when an agent does not yet have an LLM configuration."""


class AgentLLMService:
    """Service that coordinates agent existence checks with LLM config CRUD."""

    def __init__(self, session: AsyncSession):
        self._agent_service = AgentConfigService(session)
        self._llm_service = AgentLLMConfigService(session)

    async def _ensure_agent_exists(self, agent_id: int) -> None:
        agent = await self._agent_service.get_agent(agent_id)
        if not agent:
            raise AgentNotFoundError(f"Agent with ID {agent_id} not found")

    async def get_agent_config(self, agent_id: int) -> AgentLLMConfigResponse:
        """Return the primary LLM configuration for an agent."""
        await self._ensure_agent_exists(agent_id)
        config = await self._llm_service.get_primary_config(agent_id)
        if not config:
            raise AgentLLMConfigNotFoundError(
                f"LLM configuration not found for agent {agent_id}"
            )
        return config

    async def upsert_agent_config(
        self, agent_id: int, payload: AgentLLMConfigUpsert
    ) -> AgentLLMConfigResponse:
        """Create or update the primary LLM configuration for an agent."""
        await self._ensure_agent_exists(agent_id)
        return await self._llm_service.upsert_primary_config(agent_id, payload)

    async def list_configs(
        self, skip: int = 0, limit: int = 100
    ) -> List[AgentLLMConfigResponse]:
        """List LLM configurations across all agents."""
        return await self._llm_service.list_configs(skip=skip, limit=limit)
