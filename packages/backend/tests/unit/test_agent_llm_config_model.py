"""Unit tests for AgentLLMConfig model."""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_config import AgentConfig
from app.db.models.agent_llm_config import AgentLLMConfig


@pytest.mark.asyncio
class TestAgentLLMConfigModel:
    """Tests for AgentLLMConfig model."""

    async def test_create_basic_model(self, db_session: AsyncSession):
        """Test creating a basic AgentLLMConfig model instance."""
        # First create an agent config
        agent = AgentConfig(
            name="test_agent",
            agent_type="analyst",
            role="market",
            llm_provider="openai",
            llm_model="gpt-4",
            temperature=0.7,
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        # Create LLM config
        llm_config = AgentLLMConfig(
            agent_id=agent.id,
            provider="openai",
            model_name="gpt-4",
            temperature=0.7,
            max_tokens=2000,
            enabled=True,
        )
        db_session.add(llm_config)
        await db_session.commit()
        await db_session.refresh(llm_config)

        # Verify the model was created with correct attributes
        assert llm_config.id is not None
        assert llm_config.agent_id == agent.id
        assert llm_config.provider == "openai"
        assert llm_config.model_name == "gpt-4"
        assert llm_config.temperature == 0.7
        assert llm_config.max_tokens == 2000
        assert llm_config.enabled is True
        assert llm_config.created_at is not None
        assert llm_config.updated_at is not None

    async def test_model_defaults(self, db_session: AsyncSession):
        """Test that model uses correct default values."""
        # Create an agent config
        agent = AgentConfig(
            name="test_agent_defaults",
            agent_type="analyst",
            role="market",
            llm_provider="openai",
            llm_model="gpt-4",
            temperature=0.7,
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        # Create LLM config with minimal fields
        llm_config = AgentLLMConfig(
            agent_id=agent.id,
            provider="openai",
            model_name="gpt-4",
        )
        db_session.add(llm_config)
        await db_session.commit()
        await db_session.refresh(llm_config)

        # Verify defaults
        assert llm_config.temperature == 0.7  # default from model
        assert llm_config.enabled is True  # default from model
        assert llm_config.cost_per_1k_input_tokens == 0.0  # default from model
        assert llm_config.cost_per_1k_output_tokens == 0.0  # default from model

    async def test_model_with_optional_fields(self, db_session: AsyncSession):
        """Test creating a model with optional fields."""
        # Create an agent config
        agent = AgentConfig(
            name="test_agent_optional",
            agent_type="analyst",
            role="market",
            llm_provider="openai",
            llm_model="gpt-4",
            temperature=0.7,
        )
        db_session.add(agent)
        await db_session.commit()
        await db_session.refresh(agent)

        # Create LLM config with optional fields
        llm_config = AgentLLMConfig(
            agent_id=agent.id,
            provider="openai",
            model_name="gpt-4",
            temperature=0.8,
            max_tokens=3000,
            top_p=0.9,
            fallback_provider="claude",
            fallback_model="claude-3-haiku-20240307",
            cost_per_1k_input_tokens=0.03,
            cost_per_1k_output_tokens=0.06,
            enabled=False,
            metadata_json='{"key": "value"}',
        )
        db_session.add(llm_config)
        await db_session.commit()
        await db_session.refresh(llm_config)

        # Verify all fields
        assert llm_config.temperature == 0.8
        assert llm_config.max_tokens == 3000
        assert llm_config.top_p == 0.9
        assert llm_config.fallback_provider == "claude"
        assert llm_config.fallback_model == "claude-3-haiku-20240307"
        assert llm_config.cost_per_1k_input_tokens == 0.03
        assert llm_config.cost_per_1k_output_tokens == 0.06
        assert llm_config.enabled is False
        assert llm_config.metadata_json == '{"key": "value"}'
