"""AgentConfig repository for database operations."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import AgentConfig
from .base import BaseRepository


class AgentConfigRepository(BaseRepository[AgentConfig]):
    """Repository for AgentConfig operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(AgentConfig, session)

    async def get_by_name(self, name: str) -> Optional[AgentConfig]:
        """Get an agent config by name.
        
        Args:
            name: The config name
            
        Returns:
            The agent config if found, None otherwise
        """
        statement = select(AgentConfig).where(AgentConfig.name == name)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_type(self, agent_type: str) -> List[AgentConfig]:
        """Get agent configs by type.
        
        Args:
            agent_type: The agent type
            
        Returns:
            List of agent configs
        """
        statement = select(AgentConfig).where(
            AgentConfig.agent_type == agent_type,
            AgentConfig.is_active == True,
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_active(self) -> List[AgentConfig]:
        """Get all active agent configs.
        
        Returns:
            List of active agent configs
        """
        statement = select(AgentConfig).where(AgentConfig.is_active == True)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
