"""Service layer for agent LLM configuration management."""

from __future__ import annotations

import logging
from typing import List, Optional

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tradingagents.llm_providers import (
    ProviderFactory,
    ProviderType,
    get_model_info,
    list_models,
)

from ..config.settings import get_settings
from ..db.models.agent_config import AgentConfig
from ..db.models.agent_llm_config import AgentLLMConfig
from ..schemas.agent_llm_config import (
    AgentLLMConfigCreate,
    AgentLLMConfigResponse,
    AgentLLMConfigUpdate,
    AgentLLMConfigUpsert,
)

logger = logging.getLogger(__name__)


class AgentNotFoundError(Exception):
    """Raised when agent is not found."""
    pass


class AgentLLMConfigNotFoundError(Exception):
    """Raised when agent LLM config is not found."""
    pass


class AgentLLMService:
    """Service for managing agent LLM configurations."""

    def __init__(self, session: AsyncSession):
        """Initialize the service with a database session."""
        self.session = session
        self._cipher: Optional[Fernet] = None
        self._init_encryption()

    def _init_encryption(self):
        """Initialize encryption cipher if encryption key is available."""
        try:
            settings = get_settings()
            encryption_key = getattr(settings, "encryption_key", None)
            if encryption_key:
                self._cipher = Fernet(encryption_key.encode())
        except Exception as e:
            logger.warning(f"Failed to initialize encryption: {e}")

    def _encrypt_api_key(self, api_key: str) -> Optional[str]:
        """Encrypt an API key."""
        if not api_key or not self._cipher:
            return None
        try:
            return self._cipher.encrypt(api_key.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt API key: {e}")
            return None

    def _decrypt_api_key(self, encrypted_key: str) -> Optional[str]:
        """Decrypt an API key."""
        if not encrypted_key or not self._cipher:
            return None
        try:
            return self._cipher.decrypt(encrypted_key.encode()).decode()
        except Exception as e:
            logger.error(f"Failed to decrypt API key: {e}")
            return None

    def _coerce_provider_type(self, provider: str) -> ProviderType:
        """Coerce provider string to ProviderType, handling legacy aliases."""
        # Handle legacy "anthropic" alias for "claude"
        if provider.lower() == "anthropic":
            provider = "claude"
        
        try:
            return ProviderType(provider.lower())
        except ValueError:
            supported = [pt.value for pt in ProviderType]
            raise ValueError(
                f"Invalid provider: {provider}. Supported providers: {supported}"
            )

    def _validate_provider_and_model(self, provider: str, model_name: str):
        """Validate provider and model combination using registry."""
        # Coerce to ProviderType
        try:
            provider_type = self._coerce_provider_type(provider)
        except ValueError as e:
            raise e
        
        # Validate model exists for this provider
        available_models = list_models(provider_type)
        if model_name not in available_models:
            raise ValueError(
                f"Invalid model: {model_name} for provider {provider}. "
                f"Available models: {available_models}"
            )

    def _get_cost_defaults(self, provider: str, model_name: str) -> tuple[float, float]:
        """Get default cost values from registry for a provider/model combination."""
        try:
            provider_type = self._coerce_provider_type(provider)
            model_info = get_model_info(provider_type, model_name)
            return (
                model_info.cost_per_1k_input_tokens,
                model_info.cost_per_1k_output_tokens,
            )
        except ValueError as e:
            logger.warning(f"Failed to get cost defaults from registry: {e}")
            # Return sensible defaults if registry lookup fails
            return (0.0, 0.0)

    async def _agent_exists(self, agent_id: int) -> bool:
        """Check if agent exists."""
        result = await self.session.execute(
            select(AgentConfig).where(AgentConfig.id == agent_id)
        )
        return result.scalar_one_or_none() is not None

    def _to_response(self, config: AgentLLMConfig) -> AgentLLMConfigResponse:
        """Convert database model to response schema."""
        return AgentLLMConfigResponse(
            id=config.id,
            agent_id=config.agent_id,
            provider=config.provider,
            model_name=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
            has_api_key_override=bool(config.api_key_encrypted),
            fallback_provider=config.fallback_provider,
            fallback_model=config.fallback_model,
            cost_per_1k_input_tokens=config.cost_per_1k_input_tokens,
            cost_per_1k_output_tokens=config.cost_per_1k_output_tokens,
            enabled=config.enabled,
            created_at=config.created_at,
            updated_at=config.updated_at,
            metadata_json=config.metadata_json,
        )

    async def get_agent_config(self, agent_id: int) -> AgentLLMConfigResponse:
        """Get the primary LLM configuration for an agent."""
        # Check if agent exists
        if not await self._agent_exists(agent_id):
            raise AgentNotFoundError(f"Agent with ID {agent_id} not found")

        # Get the primary (enabled) config for the agent
        config = await self.get_primary_config(agent_id)
        if not config:
            raise AgentLLMConfigNotFoundError(f"No LLM configuration found for agent {agent_id}")

        return self._to_response(config)

    async def upsert_agent_config(
        self, agent_id: int, payload: AgentLLMConfigUpsert
    ) -> AgentLLMConfigResponse:
        """Create or update an agent's primary LLM configuration."""
        # Check if agent exists
        if not await self._agent_exists(agent_id):
            raise AgentNotFoundError(f"Agent with ID {agent_id} not found")

        # Validate provider and model
        self._validate_provider_and_model(payload.provider, payload.model_name)

        # Default cost values from registry if not provided
        input_cost = payload.cost_per_1k_input_tokens
        output_cost = payload.cost_per_1k_output_tokens
        
        if input_cost is None or output_cost is None:
            default_input, default_output = self._get_cost_defaults(
                payload.provider, payload.model_name
            )
            if input_cost is None:
                input_cost = default_input
            if output_cost is None:
                output_cost = default_output

        # Check if config exists
        result = await self.session.execute(
            select(AgentLLMConfig).where(AgentLLMConfig.agent_id == agent_id)
        )
        existing_config = result.scalar_one_or_none()

        if existing_config:
            # Update existing config
            existing_config.provider = payload.provider
            existing_config.model_name = payload.model_name
            existing_config.temperature = payload.temperature
            existing_config.max_tokens = payload.max_tokens
            existing_config.top_p = payload.top_p
            existing_config.fallback_provider = payload.fallback_provider
            existing_config.fallback_model = payload.fallback_model
            existing_config.cost_per_1k_input_tokens = input_cost
            existing_config.cost_per_1k_output_tokens = output_cost
            existing_config.enabled = payload.enabled
            existing_config.metadata_json = payload.metadata_json

            if payload.api_key:
                existing_config.api_key_encrypted = self._encrypt_api_key(payload.api_key)

            self.session.add(existing_config)
            await self.session.commit()
            await self.session.refresh(existing_config)
            return self._to_response(existing_config)
        else:
            # Create new config
            create_data = AgentLLMConfigCreate(
                agent_id=agent_id,
                provider=payload.provider,
                model_name=payload.model_name,
                temperature=payload.temperature,
                max_tokens=payload.max_tokens,
                top_p=payload.top_p,
                api_key=payload.api_key,
                fallback_provider=payload.fallback_provider,
                fallback_model=payload.fallback_model,
                cost_per_1k_input_tokens=input_cost,
                cost_per_1k_output_tokens=output_cost,
                enabled=payload.enabled,
                metadata_json=payload.metadata_json,
            )
            return await self.create_config(create_data)

    async def list_configs(self, skip: int = 0, limit: int = 100) -> List[AgentLLMConfigResponse]:
        """List all LLM configurations."""
        result = await self.session.execute(
            select(AgentLLMConfig).offset(skip).limit(limit)
        )
        configs = result.scalars().all()
        return [self._to_response(config) for config in configs]

    async def create_config(self, config_data: AgentLLMConfigCreate) -> AgentLLMConfigResponse:
        """Create a new LLM configuration."""
        # Validate provider and model
        self._validate_provider_and_model(config_data.provider, config_data.model_name)

        # Check if agent exists
        if not await self._agent_exists(config_data.agent_id):
            raise ValueError(f"Agent with ID {config_data.agent_id} not found")

        # Encrypt API key if provided
        encrypted_key = None
        if config_data.api_key:
            encrypted_key = self._encrypt_api_key(config_data.api_key)

        # Default cost values from registry if not provided
        input_cost = config_data.cost_per_1k_input_tokens
        output_cost = config_data.cost_per_1k_output_tokens
        
        if input_cost is None or output_cost is None:
            default_input, default_output = self._get_cost_defaults(
                config_data.provider, config_data.model_name
            )
            if input_cost is None:
                input_cost = default_input
            if output_cost is None:
                output_cost = default_output

        # Create new config
        new_config = AgentLLMConfig(
            agent_id=config_data.agent_id,
            provider=config_data.provider,
            model_name=config_data.model_name,
            temperature=config_data.temperature,
            max_tokens=config_data.max_tokens,
            top_p=config_data.top_p,
            api_key_encrypted=encrypted_key,
            fallback_provider=config_data.fallback_provider,
            fallback_model=config_data.fallback_model,
            cost_per_1k_input_tokens=input_cost,
            cost_per_1k_output_tokens=output_cost,
            enabled=config_data.enabled,
            metadata_json=config_data.metadata_json,
        )

        self.session.add(new_config)
        await self.session.commit()
        await self.session.refresh(new_config)

        return self._to_response(new_config)

    async def get_config(self, config_id: int) -> Optional[AgentLLMConfig]:
        """Get a specific LLM configuration by ID."""
        result = await self.session.execute(
            select(AgentLLMConfig).where(AgentLLMConfig.id == config_id)
        )
        return result.scalar_one_or_none()

    async def get_configs_by_agent(self, agent_id: int) -> List[AgentLLMConfig]:
        """Get all LLM configurations for a specific agent."""
        result = await self.session.execute(
            select(AgentLLMConfig).where(AgentLLMConfig.agent_id == agent_id)
        )
        return list(result.scalars().all())

    async def get_primary_config(self, agent_id: int) -> Optional[AgentLLMConfig]:
        """Get the primary (enabled) LLM configuration for an agent."""
        result = await self.session.execute(
            select(AgentLLMConfig)
            .where(AgentLLMConfig.agent_id == agent_id)
            .where(AgentLLMConfig.enabled == True)  # noqa: E712
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def update_config(
        self, config_id: int, update_data: AgentLLMConfigUpdate
    ) -> Optional[AgentLLMConfig]:
        """Update an LLM configuration."""
        config = await self.get_config(config_id)
        if not config:
            return None

        # Validate provider and model if being updated
        provider = update_data.provider if update_data.provider is not None else config.provider
        model_name = update_data.model_name if update_data.model_name is not None else config.model_name
        self._validate_provider_and_model(provider, model_name)

        # Update fields if provided
        if update_data.provider is not None:
            config.provider = update_data.provider
        if update_data.model_name is not None:
            config.model_name = update_data.model_name
        if update_data.temperature is not None:
            config.temperature = update_data.temperature
        if update_data.max_tokens is not None:
            config.max_tokens = update_data.max_tokens
        if update_data.top_p is not None:
            config.top_p = update_data.top_p
        if update_data.api_key is not None:
            config.api_key_encrypted = self._encrypt_api_key(update_data.api_key)
        if update_data.fallback_provider is not None:
            config.fallback_provider = update_data.fallback_provider
        if update_data.fallback_model is not None:
            config.fallback_model = update_data.fallback_model
        if update_data.cost_per_1k_input_tokens is not None:
            config.cost_per_1k_input_tokens = update_data.cost_per_1k_input_tokens
        if update_data.cost_per_1k_output_tokens is not None:
            config.cost_per_1k_output_tokens = update_data.cost_per_1k_output_tokens
        if update_data.enabled is not None:
            config.enabled = update_data.enabled
        if update_data.metadata_json is not None:
            config.metadata_json = update_data.metadata_json

        self.session.add(config)
        await self.session.commit()
        await self.session.refresh(config)

        return config

    async def delete_config(self, config_id: int) -> bool:
        """Delete an LLM configuration."""
        config = await self.get_config(config_id)
        if not config:
            return False

        await self.session.delete(config)
        await self.session.commit()
        return True

    async def validate_config(self, config_id: int) -> tuple[bool, Optional[str]]:
        """Validate an LLM configuration by performing a health check."""
        config = await self.get_config(config_id)
        if not config:
            return False, "Configuration not found"

        # Validate provider and model structure
        try:
            self._validate_provider_and_model(config.provider, config.model_name)
        except ValueError as e:
            return False, str(e)

        # Attempt to create provider instance and perform health check
        try:
            provider_type = self._coerce_provider_type(config.provider)
            
            # Decrypt API key if available
            api_key = None
            if config.api_key_encrypted:
                api_key = self._decrypt_api_key(config.api_key_encrypted)
            
            # Create provider instance using factory
            provider = ProviderFactory.create_provider(
                provider_type=provider_type,
                api_key=api_key,
                model_name=config.model_name,
            )
            
            # Perform health check
            health_ok = await provider.health_check()
            if not health_ok:
                return False, "Provider health check failed"
            
            return True, None
        except Exception as e:
            logger.warning(f"Failed to validate provider config {config_id}: {e}")
            return False, f"Provider validation failed: {str(e)}"
