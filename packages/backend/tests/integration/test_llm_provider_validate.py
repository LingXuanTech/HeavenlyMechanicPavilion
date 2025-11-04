"""Integration tests for /llm-providers/validate-key endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.asyncio
class TestValidateProviderKey:
    """Test /llm-providers/validate-key endpoint."""

    async def test_validate_key_success(self, async_client: AsyncClient):
        """Test successful provider key validation."""
        mock_provider = AsyncMock()
        mock_provider.health_check = AsyncMock(return_value=True)
        
        with patch(
            "tradingagents.llm_providers.factory.ProviderFactory.create_provider",
            return_value=mock_provider,
        ):
            payload = {
                "provider": "openai",
                "api_key": "test-key-123",
                "model_name": "gpt-4o-mini",
                "temperature": 0.7,
            }
            
            response = await async_client.post(
                "/llm-providers/validate-key",
                json=payload
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["provider"] == "openai"
            assert data["model_name"] == "gpt-4o-mini"
            assert data["detail"] is None

    async def test_validate_key_health_check_fails(self, async_client: AsyncClient):
        """Test validation when provider health check returns False."""
        mock_provider = AsyncMock()
        mock_provider.health_check = AsyncMock(return_value=False)
        
        with patch(
            "tradingagents.llm_providers.factory.ProviderFactory.create_provider",
            return_value=mock_provider,
        ):
            payload = {
                "provider": "openai",
                "api_key": "invalid-key",
                "model_name": "gpt-4o-mini",
            }
            
            response = await async_client.post(
                "/llm-providers/validate-key",
                json=payload
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False
            assert data["provider"] == "openai"
            assert "health check failed" in data["detail"].lower()

    async def test_validate_key_provider_raises_exception(
        self, async_client: AsyncClient
    ):
        """Test validation when provider raises an exception."""
        with patch(
            "tradingagents.llm_providers.factory.ProviderFactory.create_provider",
            side_effect=Exception("Invalid API key format"),
        ):
            payload = {
                "provider": "openai",
                "api_key": "malformed-key",
                "model_name": "gpt-4o-mini",
            }
            
            response = await async_client.post(
                "/llm-providers/validate-key",
                json=payload
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False
            assert data["provider"] == "openai"
            assert "Invalid API key format" in data["detail"]

    async def test_validate_key_unknown_provider(self, async_client: AsyncClient):
        """Test validation with unknown provider returns 404."""
        payload = {
            "provider": "unknown-provider",
            "api_key": "test-key",
            "model_name": "some-model",
        }
        
        response = await async_client.post(
            "/llm-providers/validate-key",
            json=payload
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data

    async def test_validate_key_with_optional_parameters(
        self, async_client: AsyncClient
    ):
        """Test validation with all optional parameters."""
        mock_provider = AsyncMock()
        mock_provider.health_check = AsyncMock(return_value=True)
        
        with patch(
            "tradingagents.llm_providers.factory.ProviderFactory.create_provider",
            return_value=mock_provider,
        ) as mock_create:
            payload = {
                "provider": "openai",
                "api_key": "test-key",
                "model_name": "gpt-4o",
                "temperature": 1.5,
                "max_tokens": 2000,
                "top_p": 0.9,
            }
            
            response = await async_client.post(
                "/llm-providers/validate-key",
                json=payload
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["model_name"] == "gpt-4o"
            
            # Verify the factory was called with all parameters
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["api_key"] == "test-key"
            assert call_kwargs["model_name"] == "gpt-4o"
            assert call_kwargs["temperature"] == 1.5
            assert call_kwargs["max_tokens"] == 2000
            assert call_kwargs["top_p"] == 0.9

    async def test_validate_key_missing_api_key(self, async_client: AsyncClient):
        """Test validation with missing required api_key."""
        payload = {
            "provider": "openai",
            "model_name": "gpt-4o-mini",
        }
        
        response = await async_client.post(
            "/llm-providers/validate-key",
            json=payload
        )
        
        assert response.status_code == 422

    async def test_validate_key_missing_provider(self, async_client: AsyncClient):
        """Test validation with missing required provider."""
        payload = {
            "api_key": "test-key",
            "model_name": "gpt-4o-mini",
        }
        
        response = await async_client.post(
            "/llm-providers/validate-key",
            json=payload
        )
        
        assert response.status_code == 422

    async def test_validate_key_invalid_temperature(self, async_client: AsyncClient):
        """Test validation with invalid temperature value."""
        payload = {
            "provider": "openai",
            "api_key": "test-key",
            "model_name": "gpt-4o-mini",
            "temperature": 3.0,
        }
        
        response = await async_client.post(
            "/llm-providers/validate-key",
            json=payload
        )
        
        assert response.status_code == 422

    async def test_validate_key_invalid_top_p(self, async_client: AsyncClient):
        """Test validation with invalid top_p value."""
        payload = {
            "provider": "openai",
            "api_key": "test-key",
            "model_name": "gpt-4o-mini",
            "top_p": 1.5,
        }
        
        response = await async_client.post(
            "/llm-providers/validate-key",
            json=payload
        )
        
        assert response.status_code == 422

    async def test_validate_key_default_temperature(self, async_client: AsyncClient):
        """Test validation uses default temperature when not provided."""
        mock_provider = AsyncMock()
        mock_provider.health_check = AsyncMock(return_value=True)
        
        with patch(
            "tradingagents.llm_providers.factory.ProviderFactory.create_provider",
            return_value=mock_provider,
        ) as mock_create:
            payload = {
                "provider": "openai",
                "api_key": "test-key",
                "model_name": "gpt-4o-mini",
            }
            
            response = await async_client.post(
                "/llm-providers/validate-key",
                json=payload
            )
            
            assert response.status_code == 200
            
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["temperature"] == 0.0

    async def test_validate_key_provider_error_with_detail(
        self, async_client: AsyncClient
    ):
        """Test validation error includes exception message detail."""
        error_message = "API rate limit exceeded"
        
        with patch(
            "tradingagents.llm_providers.factory.ProviderFactory.create_provider",
            side_effect=Exception(error_message),
        ):
            payload = {
                "provider": "openai",
                "api_key": "test-key",
                "model_name": "gpt-4o-mini",
            }
            
            response = await async_client.post(
                "/llm-providers/validate-key",
                json=payload
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is False
            assert error_message in data["detail"]

    async def test_validate_key_case_insensitive_provider(
        self, async_client: AsyncClient
    ):
        """Test that provider names are case-insensitive."""
        mock_provider = AsyncMock()
        mock_provider.health_check = AsyncMock(return_value=True)
        
        with patch(
            "tradingagents.llm_providers.factory.ProviderFactory.create_provider",
            return_value=mock_provider,
        ):
            payload = {
                "provider": "OpenAI",
                "api_key": "test-key",
                "model_name": "gpt-4o-mini",
            }
            
            response = await async_client.post(
                "/llm-providers/validate-key",
                json=payload
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["valid"] is True
            assert data["provider"] == "openai"

    async def test_validate_key_response_model(self, async_client: AsyncClient):
        """Test that response matches ValidateKeyResponse model."""
        mock_provider = AsyncMock()
        mock_provider.health_check = AsyncMock(return_value=True)
        
        with patch(
            "tradingagents.llm_providers.factory.ProviderFactory.create_provider",
            return_value=mock_provider,
        ):
            payload = {
                "provider": "openai",
                "api_key": "test-key",
                "model_name": "gpt-4o-mini",
            }
            
            response = await async_client.post(
                "/llm-providers/validate-key",
                json=payload
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert "provider" in data
            assert "model_name" in data
            assert "valid" in data
            assert "detail" in data
            
            assert isinstance(data["provider"], str)
            assert isinstance(data["model_name"], str)
            assert isinstance(data["valid"], bool)
            assert data["detail"] is None or isinstance(data["detail"], str)
