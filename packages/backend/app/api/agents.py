"""API endpoints for agent configuration management."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.session import get_session
from ..schemas.agent_config import (
    AgentConfigCreate,
    AgentConfigList,
    AgentConfigResponse,
    AgentConfigUpdate,
)

# NOTE: AgentLLMConfig schema/service not yet implemented
# from ..schemas.agent_llm_config import AgentLLMConfigResponse
from ..schemas.agent_llm_usage import AgentLLMUsageQuery, AgentLLMUsageSummary
from ..services.agent_config import AgentConfigService

# from ..services.agent_llm_config import AgentLLMConfigService
from ..services.agent_llm_usage import AgentLLMUsageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


def _convert_db_to_response(agent, active_llm: Optional[dict] = None) -> AgentConfigResponse:
    """Convert database model to response schema."""
    # Parse LLM config from JSON string
    llm_config = {}
    if agent.llm_config_json:
        try:
            llm_config = json.loads(agent.llm_config_json)
        except json.JSONDecodeError:
            llm_config = {"provider": "openai", "model": "gpt-4o-mini"}

    agent_dict = {
        "id": agent.id,
        "name": agent.name,
        "agent_type": agent.agent_type,
        "role": agent.role,
        "description": agent.description,
        "llm_config": llm_config,
        "prompt_template": agent.prompt_template,
        "requires_memory": agent.requires_memory,
        "memory_name": agent.memory_name,
        "is_reserved": agent.is_reserved,
        "slot_name": agent.slot_name,
        "is_active": agent.is_active,
        "version": agent.version,
        "created_at": agent.created_at,
        "updated_at": agent.updated_at,
        "active_llm_config": active_llm,
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
    """List all agent configurations."""
    service = AgentConfigService(session)
    # NOTE: AgentLLMConfigService not yet implemented
    # llm_service = AgentLLMConfigService(session)
    agents = await service.list_agents(role=role, is_active=is_active, skip=skip, limit=limit)
    response_agents = []
    for agent in agents:
        # primary_llm = await llm_service.get_primary_config(agent.id)
        primary_llm = None
        response_agents.append(_convert_db_to_response(agent, primary_llm))
    return AgentConfigList(agents=response_agents, total=len(response_agents))


@router.get("/{agent_id}", response_model=AgentConfigResponse)
async def get_agent(
    agent_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get an agent configuration by ID."""
    service = AgentConfigService(session)
    agent = await service.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found",
        )
    # NOTE: AgentLLMConfigService not yet implemented
    # primary_llm = await AgentLLMConfigService(session).get_primary_config(agent_id)
    primary_llm = None
    return _convert_db_to_response(agent, primary_llm)


@router.get("/by-name/{agent_name}", response_model=AgentConfigResponse)
async def get_agent_by_name(
    agent_name: str,
    session: AsyncSession = Depends(get_session),
):
    """Get an agent configuration by name."""
    service = AgentConfigService(session)
    agent = await service.get_agent_by_name(agent_name)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with name '{agent_name}' not found",
        )
    # NOTE: AgentLLMConfigService not yet implemented
    # primary_llm = await AgentLLMConfigService(session).get_primary_config(agent.id)
    primary_llm = None
    return _convert_db_to_response(agent, primary_llm)


@router.post("/", response_model=AgentConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    agent_data: AgentConfigCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new agent configuration."""
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
    """Update an agent configuration."""
    service = AgentConfigService(session)
    agent = await service.update_agent(agent_id, agent_data)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found",
        )
    # NOTE: AgentLLMConfigService not yet implemented
    # primary_llm = await AgentLLMConfigService(session).get_primary_config(agent_id)
    primary_llm = None
    return _convert_db_to_response(agent, primary_llm)


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Delete an agent configuration."""
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
    """Activate an agent configuration."""
    service = AgentConfigService(session)
    agent = await service.activate_agent(agent_id)
    if not agent:
        raise HTTPException(
            status=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found",
        )
    # NOTE: AgentLLMConfigService not yet implemented
    # primary_llm = await AgentLLMConfigService(session).get_primary_config(agent_id)
    primary_llm = None
    return _convert_db_to_response(agent, primary_llm)


@router.post("/{agent_id}/deactivate", response_model=AgentConfigResponse)
async def deactivate_agent(
    agent_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Deactivate an agent configuration."""
    service = AgentConfigService(session)
    agent = await service.deactivate_agent(agent_id)
    if not agent:
        raise HTTPException(
            status=status.HTTP_404_NOT_FOUND,
            detail=f"Agent with ID {agent_id} not found",
        )
    # NOTE: AgentLLMConfigService not yet implemented
    # primary_llm = await AgentLLMConfigService(session).get_primary_config(agent_id)
    primary_llm = None
    return _convert_db_to_response(agent, primary_llm)


@router.post("/reload", status_code=status.HTTP_200_OK)
async def reload_agent_registry(
    session: AsyncSession = Depends(get_session),
):
    """Reload the agent plugin registry (hot-reload)."""
    service = AgentConfigService(session)
    await service._trigger_hot_reload()
    return {"message": "Agent registry reloaded successfully"}


@router.get("/{agent_id}/llm-usage", response_model=AgentLLMUsageSummary)
async def get_agent_llm_usage(
    agent_id: int,
    start: Optional[datetime] = Query(None, description="Filter usage at or after this timestamp"),
    end: Optional[datetime] = Query(None, description="Filter usage before this timestamp"),
    limit: int = Query(100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
):
    usage_service = AgentLLMUsageService(session)
    query = AgentLLMUsageQuery(start=start, end=end, limit=limit)
    return await usage_service.get_usage(agent_id, query)
