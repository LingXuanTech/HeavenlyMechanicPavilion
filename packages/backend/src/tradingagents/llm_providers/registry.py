"""Provider registry with metadata and pricing information."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class ProviderType(str, Enum):
    """Supported LLM provider types."""

    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    GROK = "grok"
    CLAUDE = "claude"


@dataclass
class ModelInfo:
    """Information about a specific LLM model."""

    name: str
    context_window: int
    cost_per_1k_input_tokens: float
    cost_per_1k_output_tokens: float
    supports_streaming: bool = True
    supports_function_calling: bool = False
    supports_vision: bool = False
    max_output_tokens: Optional[int] = None


@dataclass
class ProviderInfo:
    """Information about an LLM provider."""

    name: str
    provider_type: ProviderType
    models: Dict[str, ModelInfo]
    base_url: Optional[str] = None
    rate_limit_rpm: int = 3500
    rate_limit_tpm: int = 90000


# Provider registry with metadata
PROVIDER_REGISTRY: Dict[ProviderType, ProviderInfo] = {
    ProviderType.OPENAI: ProviderInfo(
        name="OpenAI",
        provider_type=ProviderType.OPENAI,
        base_url=None,
        rate_limit_rpm=3500,
        rate_limit_tpm=90000,
        models={
            "gpt-4o": ModelInfo(
                name="gpt-4o",
                context_window=128000,
                cost_per_1k_input_tokens=0.005,
                cost_per_1k_output_tokens=0.015,
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                max_output_tokens=4096,
            ),
            "gpt-4o-mini": ModelInfo(
                name="gpt-4o-mini",
                context_window=128000,
                cost_per_1k_input_tokens=0.00015,
                cost_per_1k_output_tokens=0.0006,
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                max_output_tokens=4096,
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
            "gpt-4": ModelInfo(
                name="gpt-4",
                context_window=8192,
                cost_per_1k_input_tokens=0.03,
                cost_per_1k_output_tokens=0.06,
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=False,
                max_output_tokens=4096,
            ),
        },
    ),
    ProviderType.DEEPSEEK: ProviderInfo(
        name="DeepSeek",
        provider_type=ProviderType.DEEPSEEK,
        base_url="https://api.deepseek.com/v1",
        rate_limit_rpm=3000,
        rate_limit_tpm=80000,
        models={
            "deepseek-chat": ModelInfo(
                name="deepseek-chat",
                context_window=64000,
                cost_per_1k_input_tokens=0.00014,
                cost_per_1k_output_tokens=0.00042,
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=False,
                max_output_tokens=4096,
            ),
            "deepseek-coder": ModelInfo(
                name="deepseek-coder",
                context_window=4096,
                cost_per_1k_input_tokens=0.00014,
                cost_per_1k_output_tokens=0.00042,
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=False,
                max_output_tokens=4096,
            ),
        },
    ),
    ProviderType.GROK: ProviderInfo(
        name="Grok",
        provider_type=ProviderType.GROK,
        base_url="https://api.x.ai/v1",
        rate_limit_rpm=3000,
        rate_limit_tpm=60000,
        models={
            "grok-beta": ModelInfo(
                name="grok-beta",
                context_window=131072,
                cost_per_1k_input_tokens=0.005,
                cost_per_1k_output_tokens=0.015,
                supports_streaming=True,
                supports_function_calling=False,
                supports_vision=False,
                max_output_tokens=8192,
            ),
            "grok-vision-beta": ModelInfo(
                name="grok-vision-beta",
                context_window=131072,
                cost_per_1k_input_tokens=0.005,
                cost_per_1k_output_tokens=0.015,
                supports_streaming=True,
                supports_function_calling=False,
                supports_vision=True,
                max_output_tokens=8192,
            ),
        },
    ),
    ProviderType.CLAUDE: ProviderInfo(
        name="Claude",
        provider_type=ProviderType.CLAUDE,
        base_url=None,
        rate_limit_rpm=3000,
        rate_limit_tpm=40000,
        models={
            "claude-3-5-sonnet-20241022": ModelInfo(
                name="claude-3-5-sonnet-20241022",
                context_window=200000,
                cost_per_1k_input_tokens=0.003,
                cost_per_1k_output_tokens=0.015,
                supports_streaming=True,
                supports_function_calling=True,
                supports_vision=True,
                max_output_tokens=4096,
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
    ),
}


def list_providers() -> list[ProviderType]:
    """List all supported providers."""
    return list(PROVIDER_REGISTRY.keys())


def get_provider_info(provider_type: ProviderType | str) -> ProviderInfo:
    """Get information about a provider."""
    if isinstance(provider_type, str):
        provider_type = ProviderType(provider_type.lower())

    if provider_type not in PROVIDER_REGISTRY:
        raise ValueError(f"Unknown provider: {provider_type}")

    return PROVIDER_REGISTRY[provider_type]


def list_models(provider_type: ProviderType | str) -> list[str]:
    """List models for a provider."""
    info = get_provider_info(provider_type)
    return list(info.models.keys())


def get_model_info(provider_type: ProviderType | str, model_name: str) -> ModelInfo:
    """Get information about a specific model."""
    info = get_provider_info(provider_type)

    if model_name not in info.models:
        raise ValueError(
            f"Model '{model_name}' not found in {info.name}. "
            f"Available models: {list(info.models.keys())}"
        )

    return info.models[model_name]


def calculate_cost(
    provider_type: ProviderType | str,
    model_name: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """Calculate the cost of a request."""
    model_info = get_model_info(provider_type, model_name)

    input_cost = (input_tokens / 1000) * model_info.cost_per_1k_input_tokens
    output_cost = (output_tokens / 1000) * model_info.cost_per_1k_output_tokens

    return input_cost + output_cost
