"""FastAPI routes for managing agent LLM configurations."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...db.session import get_session
from ...schemas.agent_llm_config import AgentLLMConfigResponse, AgentLLMConfigUpsert
from ...services.agent_llm_service import (
    AgentLLMConfigNotFoundError,
    AgentLLMService,
    AgentNotFoundError,
)

router = APIRouter(prefix="/agents", tags=["agent-llm-configs"])


@router.get("/{agent_id}/llm-config", response_model=AgentLLMConfigResponse)
async def get_agent_llm_config(
    agent_id: int,
    session: AsyncSession = Depends(get_session),
) -> AgentLLMConfigResponse:
    """Retrieve the primary LLM configuration for a given agent."""
    service = AgentLLMService(session)
    try:
        return await service.get_agent_config(agent_id)
    except AgentNotFoundError as exc:  # pragma: no cover - defensive guard
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except AgentLLMConfigNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.put("/{agent_id}/llm-config", response_model=AgentLLMConfigResponse)
async def upsert_agent_llm_config(
    agent_id: int,
    payload: AgentLLMConfigUpsert,
    session: AsyncSession = Depends(get_session),
) -> AgentLLMConfigResponse:
    """Create or update an agent's primary LLM configuration."""
    service = AgentLLMService(session)
    try:
        return await service.upsert_agent_config(agent_id, payload)
    except AgentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/llm-configs", response_model=List[AgentLLMConfigResponse])
async def list_agent_llm_configs(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of records to return"),
    session: AsyncSession = Depends(get_session),
) -> List[AgentLLMConfigResponse]:
    """List LLM configurations across all agents."""
    service = AgentLLMService(session)
    return await service.list_configs(skip=skip, limit=limit)
