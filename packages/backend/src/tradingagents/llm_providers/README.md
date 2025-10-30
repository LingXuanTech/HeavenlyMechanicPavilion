# LLM Provider Abstraction Layer

This module provides a unified abstraction layer for multiple LLM providers, enabling seamless switching between OpenAI, DeepSeek, Grok, and Claude.

## Features

- **Unified Interface**: Common interface for all providers with `chat()`, `stream()`, and `count_tokens()` methods
- **Multiple Providers**: Support for OpenAI, DeepSeek, Grok (xAI), and Claude (Anthropic)
- **Error Handling**: Built-in retry logic, rate limiting, and error handling
- **Provider Registry**: Metadata including pricing, context windows, and capabilities
- **Factory Pattern**: Easy provider instantiation with `ProviderFactory`
- **Health Checks**: Validate provider connectivity

## Supported Providers

### OpenAI
- Models: gpt-4o, gpt-4o-mini, o4-mini, gpt-4-turbo
- Features: Streaming, function calling, vision (gpt-4o)
- API: https://platform.openai.com/

### DeepSeek
- Models: deepseek-chat, deepseek-coder
- Features: OpenAI-compatible API, cost-effective
- API: https://api.deepseek.com/

### Grok (xAI)
- Models: grok-beta, grok-vision-beta
- Features: Large context window (131K), vision support
- API: https://api.x.ai/

### Claude (Anthropic)
- Models: claude-3-5-sonnet, claude-3-opus, claude-3-sonnet, claude-3-haiku
- Features: 200K context window, function calling, vision
- API: https://www.anthropic.com/

## Usage

### Basic Usage

```python
from tradingagents.llm_providers import (
    ProviderFactory,
    ProviderType,
    LLMMessage,
)

# Create a provider
provider = ProviderFactory.create_provider(
    provider_type=ProviderType.OPENAI,
    api_key="your-api-key",
    model_name="gpt-4o-mini",
    temperature=0.7,
    max_tokens=1000,
)

# Chat completion
messages = [
    LLMMessage(role="system", content="You are a helpful assistant."),
    LLMMessage(role="user", content="What is the capital of France?"),
]
response = await provider.chat(messages)
print(response.content)
print(f"Tokens used: {response.usage['total_tokens']}")

# Streaming
async for chunk in provider.stream(messages):
    print(chunk, end="", flush=True)

# Token counting
token_count = provider.count_tokens("Some text to count")

# Health check
is_healthy = await provider.health_check()
```

### Using Provider Registry

```python
from tradingagents.llm_providers import (
    get_provider_info,
    get_model_info,
    calculate_cost,
    ProviderType,
)

# Get provider information
provider_info = get_provider_info(ProviderType.OPENAI)
print(f"Provider: {provider_info.name}")
print(f"Models: {list(provider_info.models.keys())}")

# Get model information
model_info = get_model_info(ProviderType.OPENAI, "gpt-4o-mini")
print(f"Context window: {model_info.context_window}")
print(f"Cost per 1K input: ${model_info.cost_per_1k_input_tokens}")

# Calculate request cost
cost = calculate_cost(
    provider_type=ProviderType.OPENAI,
    model_name="gpt-4o-mini",
    input_tokens=1000,
    output_tokens=500,
)
print(f"Request cost: ${cost:.4f}")
```

### Database Integration

The module integrates with the database through the `AgentLLMConfig` model:

```python
from app.services.agent_llm_config import AgentLLMConfigService
from app.schemas.agent_llm_config import AgentLLMConfigCreate

# Create LLM configuration for an agent
service = AgentLLMConfigService(db_session)

config_data = AgentLLMConfigCreate(
    agent_id=1,
    provider="openai",
    model_name="gpt-4o-mini",
    temperature=0.7,
    max_tokens=1000,
    api_key="optional-override-key",  # Optional: per-agent API key
    fallback_provider="claude",
    fallback_model="claude-3-haiku-20240307",
)

config = await service.create_config(config_data)
```

## Environment Variables

Set these environment variables for global API keys:

```bash
OPENAI_API_KEY=your_openai_key
DEEPSEEK_API_KEY=your_deepseek_key
GROK_API_KEY=your_grok_key
ANTHROPIC_API_KEY=your_anthropic_key
ENCRYPTION_KEY=your_encryption_key  # For encrypting per-agent API keys
```

## Error Handling

The module provides specific exceptions for different error cases:

```python
from tradingagents.llm_providers import (
    APIKeyMissingError,
    RateLimitExceededError,
    TokenLimitExceededError,
    ProviderAPIError,
)

try:
    response = await provider.chat(messages)
except RateLimitExceededError:
    # Handle rate limit
    await asyncio.sleep(60)
except TokenLimitExceededError:
    # Reduce message length
    messages = messages[-3:]
except ProviderAPIError as e:
    # Handle other API errors
    print(f"API error: {e}")
```

## Testing

The module includes comprehensive unit tests with mocked API calls:

```bash
pytest tests/unit/test_llm_providers.py
pytest tests/unit/test_provider_registry.py
pytest tests/unit/test_agent_llm_config_service.py
```

## Architecture

```
llm_providers/
├── base.py              # Base abstract class
├── openai_provider.py   # OpenAI implementation
├── deepseek_provider.py # DeepSeek implementation
├── grok_provider.py     # Grok implementation
├── claude_provider.py   # Claude implementation
├── factory.py           # Provider factory
├── registry.py          # Provider registry with metadata
├── exceptions.py        # Custom exceptions
└── __init__.py         # Package exports
```

## Adding New Providers

To add a new provider:

1. Create a new provider class extending `BaseLLMProvider`
2. Implement `chat()`, `stream()`, `count_tokens()`, and `health_check()` methods
3. Add provider to `ProviderType` enum in `registry.py`
4. Add provider metadata and models to `PROVIDER_REGISTRY`
5. Register provider in `ProviderFactory._provider_classes`
6. Add unit tests

## Database Schema

The `agent_llm_configs` table stores per-agent LLM configurations:

| Column | Type | Description |
|--------|------|-------------|
| id | int | Primary key |
| agent_id | int | Foreign key to agent_configs |
| provider | str | Provider name (openai, deepseek, grok, claude) |
| model_name | str | Model name |
| temperature | float | Sampling temperature |
| max_tokens | int | Maximum tokens to generate |
| top_p | float | Nucleus sampling parameter |
| api_key_encrypted | str | Encrypted API key override (optional) |
| fallback_provider | str | Fallback provider name |
| fallback_model | str | Fallback model name |
| cost_per_1k_input_tokens | float | Cost tracking |
| cost_per_1k_output_tokens | float | Cost tracking |
| enabled | bool | Whether config is active |
| created_at | datetime | Creation timestamp |
| updated_at | datetime | Update timestamp |

## Security

- API keys can be stored per-agent in the database (encrypted)
- Global API keys loaded from environment variables
- Encryption using `cryptography.fernet` with `ENCRYPTION_KEY`
- Keys stored encrypted in database, decrypted on use
- Never log or expose API keys in responses

## License

This module is part of the TradingAgents project.
