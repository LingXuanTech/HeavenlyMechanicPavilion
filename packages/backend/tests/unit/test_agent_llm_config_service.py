"""Unit tests for AgentLLMConfig service."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_config import AgentConfig
from app.db.models.agent_llm_config import AgentLLMConfig
from app.schemas.agent_llm_config import AgentLLMConfigCreate, AgentLLMConfigUpdate
from app.services.agent_llm_config import AgentLLMConfigService


@pytest.fixture
async def sample_agent(db_session: AsyncSession) -> AgentConfig:
    """Create a sample agent for testing."""
    agent = AgentConfig(
        name="test_agent",
        agent_type="analyst",
        role="market",
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        temperature=0.7,
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)
    return agent


@pytest.fixture
def llm_config_service(db_session: AsyncSession) -> AgentLLMConfigService:
    """Create AgentLLMConfig service instance."""
    return AgentLLMConfigService(db_session)


@pytest.mark.asyncio
class TestAgentLLMConfigService:
    """Tests for AgentLLMConfig service."""

    async def test_create_config(
        self,
        llm_config_service: AgentLLMConfigService,
        sample_agent: AgentConfig,
    ):
        """Test creating LLM config."""
        config_data = AgentLLMConfigCreate(
            agent_id=sample_agent.id,
            provider="openai",
            model_name="gpt-4o-mini",
            temperature=0.7,
            max_tokens=1000,
        )

        config = await llm_config_service.create_config(config_data)

        assert config.id is not None
        assert config.agent_id == sample_agent.id
        assert config.provider == "openai"
        assert config.model_name == "gpt-4o-mini"
        assert config.temperature == 0.7
        assert config.max_tokens == 1000
        assert config.enabled is True

    async def test_create_config_with_api_key(
        self,
        llm_config_service: AgentLLMConfigService,
        sample_agent: AgentConfig,
    ):
        """Test creating LLM config with API key override."""
        config_data = AgentLLMConfigCreate(
            agent_id=sample_agent.id,
            provider="openai",
            model_name="gpt-4o-mini",
            api_key="test-api-key-123",
        )

        config = await llm_config_service.create_config(config_data)

        assert config.has_api_key_override is True

    async def test_create_config_invalid_provider(
        self,
        llm_config_service: AgentLLMConfigService,
        sample_agent: AgentConfig,
    ):
        """Test creating LLM config with invalid provider raises error."""
        config_data = AgentLLMConfigCreate(
            agent_id=sample_agent.id,
            provider="invalid_provider",
            model_name="some-model",
        )

        with pytest.raises(ValueError, match="Invalid provider"):
            await llm_config_service.create_config(config_data)

    async def test_create_config_invalid_model(
        self,
        llm_config_service: AgentLLMConfigService,
        sample_agent: AgentConfig,
    ):
        """Test creating LLM config with invalid model raises error."""
        config_data = AgentLLMConfigCreate(
            agent_id=sample_agent.id,
            provider="openai",
            model_name="invalid-model",
        )

        with pytest.raises(ValueError, match="Invalid provider or model"):
            await llm_config_service.create_config(config_data)

    async def test_get_config(
        self,
        llm_config_service: AgentLLMConfigService,
        sample_agent: AgentConfig,
    ):
        """Test getting LLM config by ID."""
        # Create config first
        config_data = AgentLLMConfigCreate(
            agent_id=sample_agent.id,
            provider="openai",
            model_name="gpt-4o-mini",
        )
        created_config = await llm_config_service.create_config(config_data)

        # Get config
        config = await llm_config_service.get_config(created_config.id)

        assert config is not None
        assert config.id == created_config.id
        assert config.provider == "openai"

    async def test_get_configs_by_agent(
        self,
        llm_config_service: AgentLLMConfigService,
        sample_agent: AgentConfig,
    ):
        """Test getting all LLM configs for an agent."""
        # Create multiple configs
        config_data1 = AgentLLMConfigCreate(
            agent_id=sample_agent.id,
            provider="openai",
            model_name="gpt-4o-mini",
        )
        config_data2 = AgentLLMConfigCreate(
            agent_id=sample_agent.id,
            provider="claude",
            model_name="claude-3-5-sonnet-20241022",
        )

        await llm_config_service.create_config(config_data1)
        await llm_config_service.create_config(config_data2)

        # Get configs
        configs = await llm_config_service.get_configs_by_agent(sample_agent.id)

        assert len(configs) == 2
        providers = {c.provider for c in configs}
        assert "openai" in providers
        assert "claude" in providers

    async def test_get_primary_config(
        self,
        llm_config_service: AgentLLMConfigService,
        sample_agent: AgentConfig,
    ):
        """Test getting primary LLM config."""
        # Create configs
        config_data = AgentLLMConfigCreate(
            agent_id=sample_agent.id,
            provider="openai",
            model_name="gpt-4o-mini",
        )
        created_config = await llm_config_service.create_config(config_data)

        # Get primary config
        primary = await llm_config_service.get_primary_config(sample_agent.id)

        assert primary is not None
        assert primary.id == created_config.id

    async def test_update_config(
        self,
        llm_config_service: AgentLLMConfigService,
        sample_agent: AgentConfig,
    ):
        """Test updating LLM config."""
        # Create config
        config_data = AgentLLMConfigCreate(
            agent_id=sample_agent.id,
            provider="openai",
            model_name="gpt-4o-mini",
            temperature=0.7,
        )
        created_config = await llm_config_service.create_config(config_data)

        # Update config
        update_data = AgentLLMConfigUpdate(temperature=0.9, max_tokens=2000)
        updated_config = await llm_config_service.update_config(
            created_config.id, update_data
        )

        assert updated_config is not None
        assert updated_config.temperature == 0.9
        assert updated_config.max_tokens == 2000

    async def test_delete_config(
        self,
        llm_config_service: AgentLLMConfigService,
        sample_agent: AgentConfig,
    ):
        """Test deleting LLM config."""
        # Create config
        config_data = AgentLLMConfigCreate(
            agent_id=sample_agent.id,
            provider="openai",
            model_name="gpt-4o-mini",
        )
        created_config = await llm_config_service.create_config(config_data)

        # Delete config
        success = await llm_config_service.delete_config(created_config.id)
        assert success is True

        # Verify deletion
        config = await llm_config_service.get_config(created_config.id)
        assert config is None

    async def test_validate_config(
        self,
        llm_config_service: AgentLLMConfigService,
        sample_agent: AgentConfig,
    ):
        """Test validating LLM config."""
        # Create config
        config_data = AgentLLMConfigCreate(
            agent_id=sample_agent.id,
            provider="openai",
            model_name="gpt-4o-mini",
            api_key="test-key",
        )
        created_config = await llm_config_service.create_config(config_data)

        # Mock health check
        with patch(
            "app.services.agent_llm_config.ProviderFactory.create_provider"
        ) as mock_factory:
            mock_provider = AsyncMock()
            mock_provider.health_check = AsyncMock(return_value=True)
            mock_factory.return_value = mock_provider

            # Validate config
            is_valid, error = await llm_config_service.validate_config(
                created_config.id
            )

            assert is_valid is True
            assert error is None

    async def test_validate_config_with_failure(
        self,
        llm_config_service: AgentLLMConfigService,
        sample_agent: AgentConfig,
    ):
        """Test validating LLM config with health check failure."""
        # Create config
        config_data = AgentLLMConfigCreate(
            agent_id=sample_agent.id,
            provider="openai",
            model_name="gpt-4o-mini",
            api_key="test-key",
        )
        created_config = await llm_config_service.create_config(config_data)

        # Mock health check failure
        with patch(
            "app.services.agent_llm_config.ProviderFactory.create_provider"
        ) as mock_factory:
            mock_provider = AsyncMock()
            mock_provider.health_check = AsyncMock(return_value=False)
            mock_factory.return_value = mock_provider

            # Validate config
            is_valid, error = await llm_config_service.validate_config(
                created_config.id
            )

            assert is_valid is False
            assert error is not None
