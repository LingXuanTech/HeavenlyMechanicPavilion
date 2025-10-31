"""Integration tests for agent LLM configuration API endpoints."""

from __future__ import annotations

from uuid import uuid4

import pytest
from app.schemas.agent_llm_config import AgentLLMConfigCreate
from app.services.agent_llm_config import AgentLLMConfigService
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_config import AgentConfig
from app.db.session import get_session


@pytest.fixture
async def api_client(async_client: AsyncClient, db_session: AsyncSession):
    """Test client that uses the in-memory test database."""
    from app.main import app

    async def override_get_session():
        try:
            yield db_session
            await db_session.commit()
        except Exception:  # pragma: no cover - defensive rollback
            await db_session.rollback()
            raise

    app.dependency_overrides[get_session] = override_get_session
    try:
        yield async_client
    finally:
        app.dependency_overrides.pop(get_session, None)


async def create_agent(db_session: AsyncSession, name: str | None = None) -> AgentConfig:
    """Create and persist a test agent."""
    agent = AgentConfig(
        name=name or f"agent-{uuid4().hex}",
        agent_type="analyst",
        role="analyst",
        description="Test agent",
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        llm_type="quick",
        temperature=0.7,
        requires_memory=False,
        is_reserved=False,
        is_active=True,
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)
    return agent


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_agent_llm_config_returns_primary(
    api_client: AsyncClient, db_session: AsyncSession
):
    agent = await create_agent(db_session)
    service = AgentLLMConfigService(db_session)
    await service.create_config(
        AgentLLMConfigCreate(
            agent_id=agent.id,
            provider="openai",
            model_name="gpt-4o-mini",
            temperature=0.55,
            max_tokens=512,
        )
    )

    response = await api_client.get(f"/agents/{agent.id}/llm-config")

    assert response.status_code == 200
    data = response.json()
    assert data["agent_id"] == agent.id
    assert data["provider"] == "openai"
    assert data["model_name"] == "gpt-4o-mini"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_agent_llm_config_missing_agent_returns_404(api_client: AsyncClient):
    response = await api_client.get("/agents/9999/llm-config")
    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_agent_llm_config_without_config_returns_404(
    api_client: AsyncClient, db_session: AsyncSession
):
    agent = await create_agent(db_session)

    response = await api_client.get(f"/agents/{agent.id}/llm-config")

    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_put_agent_llm_config_creates_and_updates(
    api_client: AsyncClient, db_session: AsyncSession
):
    agent = await create_agent(db_session)

    create_payload = {
        "provider": "openai",
        "model_name": "gpt-4o-mini",
        "temperature": 0.6,
        "max_tokens": 1024,
    }
    create_response = await api_client.put(
        f"/agents/{agent.id}/llm-config", json=create_payload
    )
    assert create_response.status_code == 200
    created = create_response.json()
    assert created["temperature"] == pytest.approx(0.6)
    assert created["max_tokens"] == 1024

    update_payload = {
        "provider": "openai",
        "model_name": "gpt-4o-mini",
        "temperature": 0.85,
        "max_tokens": 2048,
    }
    update_response = await api_client.put(
        f"/agents/{agent.id}/llm-config", json=update_payload
    )
    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["temperature"] == pytest.approx(0.85)
    assert updated["max_tokens"] == 2048
    assert updated["id"] == created["id"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_put_agent_llm_config_invalid_provider_returns_400(
    api_client: AsyncClient, db_session: AsyncSession
):
    agent = await create_agent(db_session)
    payload = {
        "provider": "invalid-provider",
        "model_name": "not-a-model",
    }

    response = await api_client.put(f"/agents/{agent.id}/llm-config", json=payload)

    assert response.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_agent_llm_configs_returns_configs(
    api_client: AsyncClient, db_session: AsyncSession
):
    agent_a = await create_agent(db_session, name="agent-a")
    agent_b = await create_agent(db_session, name="agent-b")

    service = AgentLLMConfigService(db_session)
    await service.create_config(
        AgentLLMConfigCreate(
            agent_id=agent_a.id,
            provider="openai",
            model_name="gpt-4o-mini",
            temperature=0.5,
        )
    )
    await service.create_config(
        AgentLLMConfigCreate(
            agent_id=agent_b.id,
            provider="claude",
            model_name="claude-3-5-sonnet-20241022",
            temperature=0.6,
        )
    )

    response = await api_client.get("/agents/llm-configs")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    agent_ids = {item["agent_id"] for item in data}
    assert agent_a.id in agent_ids
    assert agent_b.id in agent_ids
