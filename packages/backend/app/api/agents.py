"""API endpoints for agent configuration management."""

from __future__ import annotations

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_session
from ..schemas.agent_config import (
    AgentConfigCreate,
    AgentConfigResponse,
    AgentConfigUpdate,
    AgentConfigList,
)
from ..services.agent_config import AgentConfigService


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


def _convert_db_to_response(agent) -> AgentConfigResponse:
    """Convert database model to response schema."""
    agent_dict = {
        "id": agent.id,
        "name": agent.name,
        "agent_type": agent.agent_type,
        "role": agent.role,
        "description": agent.description,
        "llm_provider": agent.llm_provider,
        "llm_model": agent.llm_model,
        "llm_type": agent.llm_type,
        "temperature": agent.temperature,
        "max_tokens": agent.max_tokens,
        "prompt_template": agent.prompt_template,
        "requires_memory": agent.requires_memory,
        "memory_name": agent.memory_name,
        "is_reserved": agent.is_reserved,
        "slot_name": agent.slot_name,
        "is_active": agent.is_active,
        "version": agent.version,
        "created_at": agent.created_at,
        "updated_at": agent.updated_at,
    }
    
    # Parse JSON fields
    if agent.capabilities_json:
        try:
            agent_dict["capabilities"] = json.loads(agent.capabilities_json)
        except json.JSONDecodeError:
            agent_dict["capabilities"] = []
    
    if agent.required_tools_json:
        try:
            agent_dict["required_tools"] = json.loads(agent.required_tools_json)
        except json.JSONDecodeError:
            agent_dict["required_tools"] = []
    
    if agent.config_json:
        try:
            agent_dict["config"] = json.loads(agent.config_json)
        except json.JSONDecodeError:
            agent_dict["config"] = {}
    
    if agent.metadata_json:
        try:
            agent_dict["metadata"] = json.loads(agent.metadata_json)
        except json.JSONDecodeError:
            agent_dict["metadata"] = {}
    
    return AgentConfigResponse(**agent_dict)


@router.get("/", response_model=AgentConfigList)
async def list_agents(
    role: Optional[str] = Query(None, description="Filter by agent role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
):
    """List all agent configurations.
    
    Args:
        role: Optional role filter
        is_active: Optional active status filter
        skip: Number of records to skip
        limit: Maximum number of records to return
        session: Database session
        
    Returns:
        AgentConfigList: List of agent configurations
    """
    service = AgentConfigService(session)
    agents = await service.list_agents(role=role, is_active=is_active, skip=skip, limit=limit)
    
    response_agents = [_convert_db_to_response(agent) for agent in agents]
    
    return AgentConfigList(agents=response_agents, total=len(response_agents))


@router.get("/{agent_id}", response_model=AgentConfigResponse)
async def get_agent(
    agent_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get an agent configuration by ID.
    
    Args:
        agent_id: Agent ID
        session: Database session
        
    Returns:
        AgentConfigResponse: Agent configuration
        
    Raises:
        HTTPException: If agent not found
    """
    service = AgentConfigService(session)
    agent = await service.get_agent(agent_id)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found",
        )
    
    return _convert_db_to_response(agent)


@router.get("/by-name/{agent_name}", response_model=AgentConfigResponse)
async def get_agent_by_name(
    agent_name: str,
    session: AsyncSession = Depends(get_session),
):
    """Get an agent configuration by name.
    
    Args:
        agent_name: Agent name
        session: Database session
        
    Returns:
        AgentConfigResponse: Agent configuration
        
    Raises:
        HTTPException: If agent not found
    """
    service = AgentConfigService(session)
    agent = await service.get_agent_by_name(agent_name)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with name '{agent_name}' not found",
        )
    
    return _convert_db_to_response(agent)


@router.post("/", response_model=AgentConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentConfigCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new agent configuration.
    
    Args:
        agent_data: Agent configuration data
        session: Database session
        
    Returns:
        AgentConfigResponse: Created agent configuration
        
    Raises:
        HTTPException: If agent name already exists
    """
    service = AgentConfigService(session)
    
    try:
        agent = await service.create_agent(agent_data)
        return _convert_db_to_response(agent)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.put("/{agent_id}", response_model=AgentConfigResponse)
async def update_agent(
    agent_id: int,
    agent_data: AgentConfigUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update an agent configuration.
    
    Args:
        agent_id: Agent ID
        agent_data: Updated agent data
        session: Database session
        
    Returns:
        AgentConfigResponse: Updated agent configuration
        
    Raises:
        HTTPException: If agent not found
    """
    service = AgentConfigService(session)
    agent = await service.update_agent(agent_id, agent_data)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found",
        )
    
    return _convert_db_to_response(agent)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Delete an agent configuration.
    
    Args:
        agent_id: Agent ID
        session: Database session
        
    Raises:
        HTTPException: If agent not found or is reserved
    """
    service = AgentConfigService(session)
    
    try:
        success = await service.delete_agent(agent_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {agent_id} not found",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.post("/{agent_id}/activate", response_model=AgentConfigResponse)
async def activate_agent(
    agent_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Activate an agent configuration.
    
    Args:
        agent_id: Agent ID
        session: Database session
        
    Returns:
        AgentConfigResponse: Updated agent configuration
        
    Raises:
        HTTPException: If agent not found
    """
    service = AgentConfigService(session)
    agent = await service.activate_agent(agent_id)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found",
        )
    
    return _convert_db_to_response(agent)


@router.post("/{agent_id}/deactivate", response_model=AgentConfigResponse)
async def deactivate_agent(
    agent_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Deactivate an agent configuration.
    
    Args:
        agent_id: Agent ID
        session: Database session
        
    Returns:
        AgentConfigResponse: Updated agent configuration
        
    Raises:
        HTTPException: If agent not found
    """
    service = AgentConfigService(session)
    agent = await service.deactivate_agent(agent_id)
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found",
        )
    
    return _convert_db_to_response(agent)


@router.post("/reload", status_code=status.HTTP_200_OK)
async def reload_agent_registry(
    session: AsyncSession = Depends(get_session),
):
    """Reload the agent plugin registry (hot-reload).
    
    This endpoint triggers a reload of the agent registry to pick up
    any changes in agent configurations without restarting the service.
    
    Args:
        session: Database session
        
    Returns:
        dict: Success message
    """
    service = AgentConfigService(session)
    await service._trigger_hot_reload()
    
    return {"message": "Agent registry reloaded successfully"}
