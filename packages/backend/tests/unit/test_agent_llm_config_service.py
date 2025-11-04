"""Unit tests for AgentLLMConfig service."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.agent_config import AgentConfig
from app.schemas.agent_llm_config import AgentLLMConfigCreate, AgentLLMConfigUpdate
from app.services.agent_llm_config import AgentLLMConfigService
from tradingagents.llm_providers import ModelInfo, ProviderInfo, ProviderType


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


@pytest.fixture
def mock_registry_funcs():
    """Mock registry functions used by the service."""
    # Create mock model info
    mock_model = ModelInfo(
        name="gpt-4o-mini",
        context_window=128000,
        cost_per_1k_input_tokens=0.00015,
        cost_per_1k_output_tokens=0.0006,
        supports_streaming=True,
        supports_function_calling=True,
        supports_vision=True,
        max_output_tokens=4096,
    )
    
    # Create mock provider info
    mock_provider = ProviderInfo(
        name="OpenAI",
        provider_type=ProviderType.OPENAI,
        models={"gpt-4o-mini": mock_model},
        base_url=None,
        rate_limit_rpm=3500,
        rate_limit_tpm=90000,
    )
    
    with patch("app.services.agent_llm_service.get_provider_info") as mock_get_provider, \
         patch("app.services.agent_llm_service.list_models") as mock_list_models, \
         patch("app.services.agent_llm_service.get_model_info") as mock_get_model:
        
        mock_get_provider.return_value = mock_provider
        mock_list_models.return_value = ["gpt-4o-mini"]
        mock_get_model.return_value = mock_model
        
        yield {
            "get_provider_info": mock_get_provider,
            "list_models": mock_list_models,
            "get_model_info": mock_get_model,
        }


@pytest.mark.asyncio
class TestAgentLLMConfigService:
    """Tests for AgentLLMConfig service."""

    async def test_create_config(
        self,
        llm_config_service: AgentLLMConfigService,
        sample_agent: AgentConfig,
        mock_registry_funcs,
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
        # Cost defaults from registry
        assert config.cost_per_1k_input_tokens == 0.00015
        assert config.cost_per_1k_output_tokens == 0.0006

    async def test_create_config_with_api_key(
        self,
        llm_config_service: AgentLLMConfigService,
        sample_agent: AgentConfig,
        mock_registry_funcs,
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
        mock_registry_funcs,
    ):
        """Test creating LLM config with invalid model raises error."""
        # Mock list_models to return specific models
        mock_registry_funcs["list_models"].return_value = ["gpt-4o-mini", "gpt-4o"]
        
        config_data = AgentLLMConfigCreate(
            agent_id=sample_agent.id,
            provider="openai",
            model_name="invalid-model",
        )

        with pytest.raises(ValueError, match="Invalid model"):
            await llm_config_service.create_config(config_data)

    async def test_get_config(
        self,
        llm_config_service: AgentLLMConfigService,
        sample_agent: AgentConfig,
        mock_registry_funcs,
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
        mock_registry_funcs,
    ):
        """Test getting all LLM configs for an agent."""
        # Setup mock for both openai and claude
        mock_claude_model = ModelInfo(
            name="claude-3-5-sonnet-20241022",
            context_window=200000,
            cost_per_1k_input_tokens=0.003,
            cost_per_1k_output_tokens=0.015,
            supports_streaming=True,
            supports_function_calling=True,
            supports_vision=True,
            max_output_tokens=4096,
        )
        
        def get_model_info_side_effect(provider_type, model_name):
            if model_name == "claude-3-5-sonnet-20241022":
                return mock_claude_model
            return mock_registry_funcs["get_model_info"].return_value
        
        mock_registry_funcs["get_model_info"].side_effect = get_model_info_side_effect
        mock_registry_funcs["list_models"].return_value = ["gpt-4o-mini", "claude-3-5-sonnet-20241022"]
        
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
        mock_registry_funcs,
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
        mock_registry_funcs,
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
        mock_registry_funcs,
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
        mock_registry_funcs,
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
            "app.services.agent_llm_service.ProviderFactory.create_provider"
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
            # Verify factory was called with correct parameters
            mock_factory.assert_called_once()

    async def test_validate_config_with_failure(
        self,
        llm_config_service: AgentLLMConfigService,
        sample_agent: AgentConfig,
        mock_registry_funcs,
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
            "app.services.agent_llm_service.ProviderFactory.create_provider"
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
            assert "health check failed" in error.lower()

    async def test_anthropic_alias_maps_to_claude(
        self,
        llm_config_service: AgentLLMConfigService,
        sample_agent: AgentConfig,
        mock_registry_funcs,
    ):
        """Test that 'anthropic' provider is treated as an alias for 'claude'."""
        mock_claude_model = ModelInfo(
            name="claude-3-5-sonnet-20241022",
            context_window=200000,
            cost_per_1k_input_tokens=0.003,
            cost_per_1k_output_tokens=0.015,
            supports_streaming=True,
            supports_function_calling=True,
            supports_vision=True,
            max_output_tokens=4096,
        )
        
        mock_registry_funcs["get_model_info"].return_value = mock_claude_model
        mock_registry_funcs["list_models"].return_value = ["claude-3-5-sonnet-20241022"]
        
        config_data = AgentLLMConfigCreate(
            agent_id=sample_agent.id,
            provider="anthropic",  # Using legacy alias
            model_name="claude-3-5-sonnet-20241022",
        )

        config = await llm_config_service.create_config(config_data)

        # Should accept "anthropic" as valid provider
        assert config.id is not None
        assert config.provider == "anthropic"
        assert config.model_name == "claude-3-5-sonnet-20241022"
        # Should get cost defaults from registry
        assert config.cost_per_1k_input_tokens == 0.003
        assert config.cost_per_1k_output_tokens == 0.015

    async def test_cost_defaults_from_registry(
        self,
        llm_config_service: AgentLLMConfigService,
        sample_agent: AgentConfig,
        mock_registry_funcs,
    ):
        """Test that cost values are automatically populated from registry."""
        config_data = AgentLLMConfigCreate(
            agent_id=sample_agent.id,
            provider="openai",
            model_name="gpt-4o-mini",
            # Not providing cost fields
        )

        config = await llm_config_service.create_config(config_data)

        # Should have cost defaults from registry
        assert config.cost_per_1k_input_tokens == 0.00015
        assert config.cost_per_1k_output_tokens == 0.0006

    async def test_explicit_cost_overrides_registry(
        self,
        llm_config_service: AgentLLMConfigService,
        sample_agent: AgentConfig,
        mock_registry_funcs,
    ):
        """Test that explicit cost values override registry defaults."""
        config_data = AgentLLMConfigCreate(
            agent_id=sample_agent.id,
            provider="openai",
            model_name="gpt-4o-mini",
            cost_per_1k_input_tokens=0.001,
            cost_per_1k_output_tokens=0.002,
        )

        config = await llm_config_service.create_config(config_data)

        # Should use explicit values, not registry defaults
        assert config.cost_per_1k_input_tokens == 0.001
        assert config.cost_per_1k_output_tokens == 0.002
