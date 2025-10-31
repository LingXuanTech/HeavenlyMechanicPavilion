"""Service layer for agent configuration management with hot-reload support."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import AgentConfig
from ..repositories.agent_config import AgentConfigRepository
from ..schemas.agent_config import AgentConfigCreate, AgentConfigUpdate


logger = logging.getLogger(__name__)


class AgentConfigService:
    """Service for managing agent configurations with hot-reload."""
    
    def __init__(self, session: AsyncSession):
        """Initialize the service.
        
        Args:
            session: Database session
        """
        self.session = session
        self.repository = AgentConfigRepository(session)
    
    async def create_agent(self, agent_data: AgentConfigCreate) -> AgentConfig:
        """Create a new agent configuration.
        
        Args:
            agent_data: Agent configuration data
            
        Returns:
            AgentConfig: Created agent configuration
            
        Raises:
            ValueError: If agent name already exists
        """
        # Check if agent already exists
        existing = await self.repository.get_by_name(agent_data.name)
        if existing:
            raise ValueError(f"Agent with name '{agent_data.name}' already exists")
        
        # Prepare data for database
        agent_dict = agent_data.model_dump(exclude_none=True)
        
        # Convert llm_config dict to JSON string
        if "llm_config" in agent_dict:
            agent_dict["llm_config_json"] = json.dumps(agent_dict.pop("llm_config"))
        
        # Convert lists to JSON
        if "capabilities" in agent_dict:
            agent_dict["capabilities_json"] = json.dumps(agent_dict.pop("capabilities"))
        if "required_tools" in agent_dict:
            agent_dict["required_tools_json"] = json.dumps(agent_dict.pop("required_tools"))
        if "config" in agent_dict:
            agent_dict["config_json"] = json.dumps(agent_dict.pop("config"))
        if "metadata" in agent_dict:
            agent_dict["metadata_json"] = json.dumps(agent_dict.pop("metadata"))
        
        # Create agent
        agent = AgentConfig(**agent_dict)
        created_agent = await self.repository.create(agent)
        
        # Trigger hot-reload
        await self._trigger_hot_reload()
        
        logger.info(f"Created agent configuration: {created_agent.name}")
        return created_agent
    
    async def get_agent(self, agent_id: int) -> Optional[AgentConfig]:
        """Get an agent configuration by ID.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            AgentConfig: Agent configuration or None
        """
        return await self.repository.get(agent_id)
    
    async def get_agent_by_name(self, name: str) -> Optional[AgentConfig]:
        """Get an agent configuration by name.
        
        Args:
            name: Agent name
            
        Returns:
            AgentConfig: Agent configuration or None
        """
        return await self.repository.get_by_name(name)
    
    async def list_agents(
        self,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AgentConfig]:
        """List agent configurations.
        
        Args:
            role: Optional role filter
            is_active: Optional active status filter
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List[AgentConfig]: List of agent configurations
        """
        if role:
            agents = await self.repository.get_by_type(role)
        elif is_active is not None:
            if is_active:
                agents = await self.repository.get_active()
            else:
                all_agents = await self.repository.list(skip=skip, limit=limit)
                agents = [a for a in all_agents if not a.is_active]
        else:
            agents = await self.repository.list(skip=skip, limit=limit)
        
        return agents
    
    async def update_agent(
        self,
        agent_id: int,
        agent_data: AgentConfigUpdate,
    ) -> Optional[AgentConfig]:
        """Update an agent configuration.
        
        Args:
            agent_id: Agent ID
            agent_data: Updated agent data
            
        Returns:
            AgentConfig: Updated agent configuration or None
        """
        agent = await self.repository.get(agent_id)
        if not agent:
            return None
        
        # Prepare update data
        update_dict = agent_data.model_dump(exclude_none=True, exclude_unset=True)
        
        # Convert llm_config dict to JSON string
        if "llm_config" in update_dict:
            update_dict["llm_config_json"] = json.dumps(update_dict.pop("llm_config"))
        
        # Convert lists to JSON
        if "capabilities" in update_dict:
            update_dict["capabilities_json"] = json.dumps(update_dict.pop("capabilities"))
        if "required_tools" in update_dict:
            update_dict["required_tools_json"] = json.dumps(update_dict.pop("required_tools"))
        if "config" in update_dict:
            update_dict["config_json"] = json.dumps(update_dict.pop("config"))
        if "metadata" in update_dict:
            update_dict["metadata_json"] = json.dumps(update_dict.pop("metadata"))
        
        # Update timestamp
        update_dict["updated_at"] = datetime.utcnow()
        
        # Update agent
        updated_agent = await self.repository.update(agent_id, update_dict)
        
        # Trigger hot-reload
        await self._trigger_hot_reload()
        
        logger.info(f"Updated agent configuration: {updated_agent.name}")
        return updated_agent
    
    async def delete_agent(self, agent_id: int) -> bool:
        """Delete an agent configuration.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            bool: True if deleted, False if not found
            
        Raises:
            ValueError: If trying to delete a reserved agent
        """
        agent = await self.repository.get(agent_id)
        if not agent:
            return False
        
        if agent.is_reserved:
            raise ValueError(f"Cannot delete reserved agent: {agent.name}")
        
        success = await self.repository.delete(agent_id)
        
        if success:
            # Trigger hot-reload
            await self._trigger_hot_reload()
            logger.info(f"Deleted agent configuration: {agent.name}")
        
        return success
    
    async def activate_agent(self, agent_id: int) -> Optional[AgentConfig]:
        """Activate an agent configuration.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            AgentConfig: Updated agent configuration or None
        """
        return await self.update_agent(agent_id, AgentConfigUpdate(is_active=True))
    
    async def deactivate_agent(self, agent_id: int) -> Optional[AgentConfig]:
        """Deactivate an agent configuration.
        
        Args:
            agent_id: Agent ID
            
        Returns:
            AgentConfig: Updated agent configuration or None
        """
        return await self.update_agent(agent_id, AgentConfigUpdate(is_active=False))
    
    async def _trigger_hot_reload(self) -> None:
        """Trigger hot-reload of agent registry.
        
        This method reloads the agent plugin registry to reflect changes
        in the database without restarting the service.
        """
        try:
            from tradingagents.agents import get_agent_registry
            from tradingagents.agents.plugin_loader import register_built_in_plugins
            
            # Get the registry
            registry = get_agent_registry()
            
            # Clear and re-register built-in plugins
            # Note: Custom plugins from DB would be loaded here
            logger.info("Reloading agent registry...")
            register_built_in_plugins(registry)
            
            # TODO: Load custom agents from database
            # This would involve dynamically creating plugin instances from DB configs
            
            logger.info("Agent registry reloaded successfully")
        except Exception as e:
            logger.error(f"Failed to reload agent registry: {e}")
