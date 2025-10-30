"""Provider registry with metadata, pricing, and capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional


class ProviderType(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    GROK = "grok"
    CLAUDE = "claude"


@dataclass
class ModelInfo:
    """Information about a specific model."""

    name: str
    context_window: int  # Maximum context window in tokens
    cost_per_1k_input_tokens: float  # Cost in USD
    cost_per_1k_output_tokens: float  # Cost in USD
    supports_streaming: bool = True
    supports_function_calling: bool = False
    supports_vision: bool = False
    max_output_tokens: Optional[int] = None


@dataclass
class ProviderInfo:
    """Information about a provider."""

    name: str
    provider_type: ProviderType
    base_url: Optional[str]
    models: Dict[str, ModelInfo]
    requires_api_key: bool = True
    rate_limits: Optional[Dict[str, int]] = None  # e.g., {"rpm": 500, "tpm": 100000}


# Provider registry with metadata
PROVIDER_REGISTRY: Dict[ProviderType, ProviderInfo] = {
    ProviderType.OPENAI: ProviderInfo(
        name="OpenAI",
        provider_type=ProviderType.OPENAI,
        base_url=None,  # Uses default OpenAI base URL
        models={
            "gpt-4o": ModelInfo(
                name="gpt-4o",
                context_window=128000,
                cost_per_1k_input_tokens=0.0025,
                cost_per_1k_output_tokens=0.01,
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                max_output_tokens=16384,
            ),
            "gpt-4o-mini": ModelInfo(
                name="gpt-4o-mini",
                context_window=128000,
                cost_per_1k_input_tokens=0.00015,
                cost_per_1k_output_tokens=0.0006,
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                max_output_tokens=16384,
            ),
            "o4-mini": ModelInfo(
                name="o4-mini",
                context_window=128000,
                cost_per_1k_input_tokens=0.00015,
                cost_per_1k_output_tokens=0.0006,
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=False,
                max_output_tokens=16384,
            ),
            "gpt-4-turbo": ModelInfo(
                name="gpt-4-turbo",
                context_window=128000,
                cost_per_1k_input_tokens=0.01,
                cost_per_1k_output_tokens=0.03,
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                max_output_tokens=4096,
            ),
        },
        rate_limits={"rpm": 500, "tpm": 100000},
    ),
    ProviderType.DEEPSEEK: ProviderInfo(
        name="DeepSeek",
        provider_type=ProviderType.DEEPSEEK,
        base_url="https://api.deepseek.com/v1",
        models={
            "deepseek-chat": ModelInfo(
                name="deepseek-chat",
                context_window=32000,
                cost_per_1k_input_tokens=0.00014,
                cost_per_1k_output_tokens=0.00028,
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=False,
                max_output_tokens=4096,
            ),
            "deepseek-coder": ModelInfo(
                name="deepseek-coder",
                context_window=16000,
                cost_per_1k_input_tokens=0.00014,
                cost_per_1k_output_tokens=0.00028,
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=False,
                max_output_tokens=4096,
            ),
        },
        rate_limits={"rpm": 100, "tpm": 50000},
    ),
    ProviderType.GROK: ProviderInfo(
        name="Grok (xAI)",
        provider_type=ProviderType.GROK,
        base_url="https://api.x.ai/v1",
        models={
            "grok-beta": ModelInfo(
                name="grok-beta",
                context_window=131072,
                cost_per_1k_input_tokens=0.005,
                cost_per_1k_output_tokens=0.015,
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=False,
                max_output_tokens=4096,
            ),
            "grok-vision-beta": ModelInfo(
                name="grok-vision-beta",
                context_window=131072,
                cost_per_1k_input_tokens=0.005,
                cost_per_1k_output_tokens=0.015,
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                max_output_tokens=4096,
            ),
        },
        rate_limits={"rpm": 60, "tpm": 60000},
    ),
    ProviderType.CLAUDE: ProviderInfo(
        name="Claude (Anthropic)",
        provider_type=ProviderType.CLAUDE,
        base_url=None,  # Uses default Anthropic base URL
        models={
            "claude-3-5-sonnet-20241022": ModelInfo(
                name="claude-3-5-sonnet-20241022",
                context_window=200000,
                cost_per_1k_input_tokens=0.003,
                cost_per_1k_output_tokens=0.015,
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                max_output_tokens=8192,
            ),
            "claude-3-opus-20240229": ModelInfo(
                name="claude-3-opus-20240229",
                context_window=200000,
                cost_per_1k_input_tokens=0.015,
                cost_per_1k_output_tokens=0.075,
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                max_output_tokens=4096,
            ),
            "claude-3-sonnet-20240229": ModelInfo(
                name="claude-3-sonnet-20240229",
                context_window=200000,
                cost_per_1k_input_tokens=0.003,
                cost_per_1k_output_tokens=0.015,
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                max_output_tokens=4096,
            ),
            "claude-3-haiku-20240307": ModelInfo(
                name="claude-3-haiku-20240307",
                context_window=200000,
                cost_per_1k_input_tokens=0.00025,
                cost_per_1k_output_tokens=0.00125,
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                max_output_tokens=4096,
            ),
        },
        rate_limits={"rpm": 50, "tpm": 40000},
    ),
}


def get_provider_info(provider_type: ProviderType) -> ProviderInfo:
    """Get provider information.

    Args:
        provider_type: The provider type

    Returns:
        ProviderInfo: Provider information

    Raises:
        ValueError: If provider not found
    """
    if provider_type not in PROVIDER_REGISTRY:
        raise ValueError(f"Provider {provider_type} not found in registry")
    return PROVIDER_REGISTRY[provider_type]


def get_model_info(provider_type: ProviderType, model_name: str) -> ModelInfo:
    """Get model information.

    Args:
        provider_type: The provider type
        model_name: The model name

    Returns:
        ModelInfo: Model information

    Raises:
        ValueError: If provider or model not found
    """
    provider_info = get_provider_info(provider_type)
    if model_name not in provider_info.models:
        raise ValueError(
            f"Model {model_name} not found for provider {provider_type}. "
            f"Available models: {list(provider_info.models.keys())}"
        )
    return provider_info.models[model_name]


def list_providers() -> List[ProviderType]:
    """List all available providers.

    Returns:
        List[ProviderType]: List of provider types
    """
    return list(PROVIDER_REGISTRY.keys())


def list_models(provider_type: ProviderType) -> List[str]:
    """List all models for a provider.

    Args:
        provider_type: The provider type

    Returns:
        List[str]: List of model names
    """
    provider_info = get_provider_info(provider_type)
    return list(provider_info.models.keys())


def calculate_cost(
    provider_type: ProviderType,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Calculate the cost of a request.

    Args:
        provider_type: The provider type
        model_name: The model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        float: Cost in USD
    """
    model_info = get_model_info(provider_type, model_name)
    input_cost = (input_tokens / 1000) * model_info.cost_per_1k_input_tokens
    output_cost = (output_tokens / 1000) * model_info.cost_per_1k_output_tokens
    return input_cost + output_cost
