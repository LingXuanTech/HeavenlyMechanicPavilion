"""Integration tests for LLM provider and agent LLM configuration endpoints."""

from __future__ import annotations

from typing import List
from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from app.db import get_db_manager
from app.db.models.agent_config import AgentConfig


async def _create_agent(name: str, slot: str) -> int:
    db_manager = get_db_manager()
    async for session in db_manager.get_session():
        agent = AgentConfig(
            name=name,
            agent_type="analyst",
            role="analyst",
            description="Test agent",
            llm_provider="openai",
            llm_model="gpt-4o-mini",
            llm_type="quick",
            temperature=0.7,
            max_tokens=None,
            prompt_template=None,
            capabilities_json="[]",
            required_tools_json="[]",
            requires_memory=False,
            memory_name=None,
            is_reserved=False,
            slot_name=slot,
            is_active=True,
            version="1.0.0",
            config_json=None,
            metadata_json=None,
        )
        session.add(agent)
        await session.flush()
        agent_id = agent.id
        break
    return agent_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_llm_providers(async_client: AsyncClient):
    response = await async_client.get("/llm-providers")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert any(provider["provider"] == "openai" for provider in data)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_llm_configuration_flow(monkeypatch, async_client: AsyncClient):
    agent_id = await _create_agent("test_agent", "market")
    other_agent_id = await _create_agent("test_agent_b", "social")

    # Upsert primary config
    payload = {
        "provider": "openai",
        "model_name": "gpt-4o-mini",
        "temperature": 0.65,
        "max_tokens": 2048,
        "top_p": 0.9,
    }
    put_response = await async_client.put(f"/agents/{agent_id}/llm-config", json=payload)
    assert put_response.status_code == 200
    put_data = put_response.json()
    assert put_data["provider"] == "openai"
    assert put_data["model_name"] == "gpt-4o-mini"

    # Ensure agent detail reflects active config
    agent_response = await async_client.get(f"/agents/{agent_id}")
    assert agent_response.status_code == 200
    agent_data = agent_response.json()
    assert agent_data["active_llm_config"]["provider"] == "openai"

    # Bulk assign to both agents with different provider
    bulk_payload = {
        "agent_ids": [agent_id, other_agent_id],
        "config": {
            "provider": "deepseek",
            "model_name": "deepseek-chat",
            "temperature": 0.6,
            "max_tokens": 1024,
            "top_p": 0.8,
        },
    }
    bulk_response = await async_client.post("/agents/bulk-llm-config", json=bulk_payload)
    assert bulk_response.status_code == 200
    bulk_data = bulk_response.json()
    assert isinstance(bulk_data, list)
    assert len(bulk_data) == 2
    assert bulk_data[0]["provider"] == "deepseek"

    # List configurations
    list_response = await async_client.get(f"/agents/{agent_id}/llm-config")
    assert list_response.status_code == 200
    configs = list_response.json()
    assert isinstance(configs, list)
    assert any(cfg["provider"] == "deepseek" for cfg in configs)

    # Patch validation to avoid external call
    monkeypatch.setattr(
        "app.services.agent_llm_config.AgentLLMConfigService.validate_config",
        AsyncMock(return_value=(True, None)),
    )

    test_response = await async_client.post(f"/agents/{agent_id}/test-llm")
    assert test_response.status_code == 200
    test_data = test_response.json()
    assert test_data["valid"] is True

    # Usage should be empty summary
    usage_response = await async_client.get(f"/agents/{agent_id}/llm-usage")
    assert usage_response.status_code == 200
    usage_data = usage_response.json()
    assert usage_data["agent_id"] == agent_id
    assert usage_data["total_calls"] == 0
    assert usage_data["records"] == []
