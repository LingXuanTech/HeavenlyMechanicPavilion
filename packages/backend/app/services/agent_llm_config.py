"""Service layer for agent LLM configuration management."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from tradingagents.llm_providers import (
    ProviderFactory,
    ProviderType,
    get_model_info,
    get_provider_info,
)

from ..db.models.agent_llm_config import AgentLLMConfig
from ..repositories.agent_llm_config import AgentLLMConfigRepository
from ..schemas.agent_llm_config import (
    AgentLLMConfigCreate,
    AgentLLMConfigResponse,
    AgentLLMConfigUpdate,
    AgentLLMConfigUpsert,
)
from ..security.encryption import decrypt_api_key, encrypt_api_key

logger = logging.getLogger(__name__)


class AgentLLMConfigService:
    """Service for managing agent LLM configurations."""

    def __init__(self, session: AsyncSession):
        """Initialize the service.

        Args:
            session: Database session
        """
        self.session = session
        self.repository = AgentLLMConfigRepository(session)

    async def create_config(
        self, config_data: AgentLLMConfigCreate
    ) -> AgentLLMConfigResponse:
        """Create a new LLM configuration for an agent.

        Args:
            config_data: LLM configuration data

        Returns:
            AgentLLMConfigResponse: Created LLM configuration

        Raises:
            ValueError: If provider or model is invalid
        """
        # Validate provider and model
        try:
            provider_type = ProviderType(config_data.provider.lower())
            provider_info = get_provider_info(provider_type)
            model_info = get_model_info(provider_type, config_data.model_name)
        except ValueError as e:
            raise ValueError(f"Invalid provider or model: {e}")

        # Prepare data for database
        config_dict = config_data.model_dump(exclude={"api_key", "metadata"})

        # Encrypt API key if provided
        if config_data.api_key:
            config_dict["api_key_encrypted"] = encrypt_api_key(config_data.api_key)

        # Add cost information from registry if not provided
        if config_data.cost_per_1k_input_tokens == 0.0:
            config_dict["cost_per_1k_input_tokens"] = model_info.cost_per_1k_input_tokens
        if config_data.cost_per_1k_output_tokens == 0.0:
            config_dict["cost_per_1k_output_tokens"] = model_info.cost_per_1k_output_tokens

        # Convert metadata to JSON
        if config_data.metadata:
            config_dict["metadata_json"] = json.dumps(config_data.metadata)

        # Create config
        config = AgentLLMConfig(**config_dict)
        created_config = await self.repository.create(config)

        logger.info(
            f"Created LLM config for agent {config_data.agent_id}: "
            f"{config_data.provider}/{config_data.model_name}"
        )

        return self._to_response(created_config)

    async def get_config(self, config_id: int) -> Optional[AgentLLMConfigResponse]:
        """Get an LLM configuration by ID.

        Args:
            config_id: Config ID

        Returns:
            AgentLLMConfigResponse: LLM configuration or None
        """
        config = await self.repository.get(config_id)
        if config:
            return self._to_response(config)
        return None

    async def get_configs_by_agent(
        self, agent_id: int, enabled_only: bool = False
    ) -> List[AgentLLMConfigResponse]:
        """Get all LLM configurations for an agent.

        Args:
            agent_id: Agent ID
            enabled_only: If True, only return enabled configs

        Returns:
            List[AgentLLMConfigResponse]: List of LLM configurations
        """
        if enabled_only:
            configs = await self.repository.get_enabled_by_agent_id(agent_id)
        else:
            configs = await self.repository.get_by_agent_id(agent_id)

        return [self._to_response(config) for config in configs]

    async def get_primary_config(
        self, agent_id: int
    ) -> Optional[AgentLLMConfigResponse]:
        """Get the primary LLM configuration for an agent.

        Args:
            agent_id: Agent ID

        Returns:
            AgentLLMConfigResponse: Primary LLM configuration or None
        """
        config = await self.repository.get_primary_config(agent_id)
        if config:
            return self._to_response(config)
        return None

    async def list_configs(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AgentLLMConfigResponse]:
        """List LLM configurations across all agents.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List[AgentLLMConfigResponse]: List of LLM configurations
        """
        configs = await self.repository.get_multi(skip=skip, limit=limit)
        return [self._to_response(config) for config in configs]

    async def update_config(
        self, config_id: int, config_data: AgentLLMConfigUpdate
    ) -> Optional[AgentLLMConfigResponse]:
        """Update an LLM configuration.

        Args:
            config_id: Config ID
            config_data: Updated config data

        Returns:
            AgentLLMConfigResponse: Updated LLM configuration or None
        """
        config = await self.repository.get(config_id)
        if not config:
            return None

        # Prepare update data
        update_dict = config_data.model_dump(exclude_none=True, exclude_unset=True)

        # Validate provider and model if changed
        if "provider" in update_dict or "model_name" in update_dict:
            provider = update_dict.get("provider", config.provider)
            model_name = update_dict.get("model_name", config.model_name)

            try:
                provider_type = ProviderType(provider.lower())
                model_info = get_model_info(provider_type, model_name)

                # Update cost information
                if "cost_per_1k_input_tokens" not in update_dict:
                    update_dict["cost_per_1k_input_tokens"] = (
                        model_info.cost_per_1k_input_tokens
                    )
                if "cost_per_1k_output_tokens" not in update_dict:
                    update_dict["cost_per_1k_output_tokens"] = (
                        model_info.cost_per_1k_output_tokens
                    )
            except ValueError as e:
                raise ValueError(f"Invalid provider or model: {e}")

        # Encrypt API key if provided
        if "api_key" in update_dict:
            if update_dict["api_key"]:
                update_dict["api_key_encrypted"] = encrypt_api_key(update_dict["api_key"])
            else:
                update_dict["api_key_encrypted"] = None
            del update_dict["api_key"]

        # Convert metadata to JSON
        if "metadata" in update_dict:
            if update_dict["metadata"]:
                update_dict["metadata_json"] = json.dumps(update_dict["metadata"])
            else:
                update_dict["metadata_json"] = None
            del update_dict["metadata"]

        # Update timestamp
        update_dict["updated_at"] = datetime.utcnow()

        # Update config
        updated_config = await self.repository.update(db_obj=config, obj_in=update_dict)

        logger.info(f"Updated LLM config {config_id}")
        return self._to_response(updated_config)

    async def delete_config(self, config_id: int) -> bool:
        """Delete an LLM configuration.

        Args:
            config_id: Config ID

        Returns:
            bool: True if deleted, False if not found
        """
        success = await self.repository.delete(id=config_id)
        if success:
            logger.info(f"Deleted LLM config {config_id}")
        return success

    async def validate_config(
        self, config_id: int
    ) -> tuple[bool, Optional[str]]:
        """Validate an LLM configuration by checking API connectivity.

        Args:
            config_id: Config ID

        Returns:
            tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        config = await self.repository.get(config_id)
        if not config:
            return False, "Configuration not found"

        # Get API key
        api_key = await self._get_api_key(config)
        if not api_key:
            return False, f"No API key available for provider {config.provider}"

        # Create provider instance
        try:
            provider = ProviderFactory.create_provider(
                provider_type=config.provider,
                api_key=api_key,
                model_name=config.model_name,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                top_p=config.top_p,
            )

            # Run health check
            is_healthy = await provider.health_check()
            if is_healthy:
                return True, None
            else:
                return False, "Provider health check failed"

        except Exception as e:
            logger.error(f"Error validating config {config_id}: {e}")
            return False, str(e)

    async def upsert_primary_config(
        self, agent_id: int, payload: AgentLLMConfigUpsert
    ) -> AgentLLMConfigResponse:
        """Create or update the primary LLM configuration for an agent."""
        existing = await self.get_primary_config(agent_id)
        data = payload.model_dump(exclude_unset=True)

        provider = data.get("provider")
        model_name = data.get("model_name")
        if not provider or not model_name:
            raise ValueError("provider and model_name are required for LLM configuration")

        if existing:
            update_payload = AgentLLMConfigUpdate(**data)
            return await self.update_config(existing.id, update_payload)

        create_payload = AgentLLMConfigCreate(
            agent_id=agent_id,
            provider=provider,
            model_name=model_name,
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens"),
            top_p=data.get("top_p"),
            fallback_provider=data.get("fallback_provider"),
            fallback_model=data.get("fallback_model"),
            enabled=data.get("enabled", True),
            api_key=data.get("api_key"),
            cost_per_1k_input_tokens=data.get("cost_per_1k_input_tokens", 0.0) or 0.0,
            cost_per_1k_output_tokens=data.get("cost_per_1k_output_tokens", 0.0) or 0.0,
            metadata=data.get("metadata"),
        )
        return await self.create_config(create_payload)

    async def bulk_assign_config(
        self, agent_ids: List[int], payload: AgentLLMConfigUpsert
    ) -> List[AgentLLMConfigResponse]:
        """Bulk assign or update LLM configurations for multiple agents."""
        results: List[AgentLLMConfigResponse] = []
        for agent_id in agent_ids:
            try:
                result = await self.upsert_primary_config(agent_id, payload)
                results.append(result)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error("Failed to assign LLM config to agent %s: %s", agent_id, exc)
        return results

    async def _get_api_key(self, config: AgentLLMConfig) -> Optional[str]:
        """Get API key for a configuration.

        Args:
            config: The LLM configuration

        Returns:
            Optional[str]: The API key or None
        """
        # First check if there's an encrypted override
        if config.api_key_encrypted:
            return decrypt_api_key(config.api_key_encrypted)

        # Otherwise, get from environment
        env_key = f"{config.provider.upper()}_API_KEY"
        return os.getenv(env_key)

    def _to_response(self, config: AgentLLMConfig) -> AgentLLMConfigResponse:
        """Convert database model to response schema.

        Args:
            config: The database model

        Returns:
            AgentLLMConfigResponse: The response schema
        """
        # Parse metadata
        metadata = None
        if config.metadata_json:
            try:
                metadata = json.loads(config.metadata_json)
            except Exception:
                pass

        return AgentLLMConfigResponse(
            id=config.id,
            agent_id=config.agent_id,
            provider=config.provider,
            model_name=config.model_name,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
            fallback_provider=config.fallback_provider,
            fallback_model=config.fallback_model,
            cost_per_1k_input_tokens=config.cost_per_1k_input_tokens,
            cost_per_1k_output_tokens=config.cost_per_1k_output_tokens,
            enabled=config.enabled,
            has_api_key_override=bool(config.api_key_encrypted),
            created_at=config.created_at,
            updated_at=config.updated_at,
            metadata=metadata,
        )
