# LLM Providers

Clean provider adapters for Large Language Models with configuration support.

## Overview

This package provides simple, clean adapters for LLM providers with proper configuration management and error handling. Currently supports OpenAI with plans to expand to other providers.

## OpenAI Provider

The `OpenAIProvider` class provides a clean interface to the OpenAI API with:

- **Multiple model support**: GPT-4, GPT-4 Turbo, GPT-3.5 Turbo, and more
- **Configuration validation**: Temperature range, token limits
- **Token counting**: Accurate token counting using tiktoken
- **Error handling**: Proper exception hierarchy for different error types
- **Environment variable support**: Load API keys from environment

### Installation

The required dependencies are already included in the project:
- `openai` (via langchain-openai)
- `tiktoken>=0.5.0`

### Quick Start

```python
from llm_providers import OpenAIProvider

# Initialize with API key
provider = OpenAIProvider(
    model_name="gpt-4o-mini",
    temperature=0.7,
    max_tokens=1000,
    api_key="your-api-key"  # or set OPENAI_API_KEY env var
)

# Send a chat completion request
messages = [
    {"role": "user", "content": "Hello, how are you?"}
]
response = await provider.chat(messages)

print(response["content"])
print(f"Tokens used: {response['usage']['total_tokens']}")
```

### Configuration

#### Model Selection

Supported models with their token limits:

| Model | Token Limit |
|-------|-------------|
| gpt-4 | 8,192 |
| gpt-4-turbo | 128,000 |
| gpt-4o | 128,000 |
| gpt-4o-mini | 128,000 |
| gpt-3.5-turbo | 16,385 |

```python
# Use GPT-4
provider = OpenAIProvider(model_name="gpt-4", api_key="...")

# Use GPT-3.5 Turbo for faster, cheaper responses
provider = OpenAIProvider(model_name="gpt-3.5-turbo", api_key="...")
```

#### Temperature

Controls randomness in responses (0.0 to 2.0):
- **0.0**: Deterministic, focused responses
- **0.7**: Balanced (default)
- **2.0**: Maximum creativity

```python
provider = OpenAIProvider(
    model_name="gpt-4o-mini",
    temperature=0.3,  # More focused
    api_key="..."
)
```

#### Max Tokens

Limit the number of tokens generated:

```python
provider = OpenAIProvider(
    model_name="gpt-4o-mini",
    max_tokens=500,  # Limit response length
    api_key="..."
)
```

### Usage Examples

#### Basic Chat

```python
import asyncio
from llm_providers import OpenAIProvider

async def main():
    provider = OpenAIProvider(api_key="your-key")
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is the capital of France?"}
    ]
    
    response = await provider.chat(messages)
    print(response["content"])
    # Output: "The capital of France is Paris."

asyncio.run(main())
```

#### Multi-turn Conversation

```python
async def conversation():
    provider = OpenAIProvider(api_key="your-key")
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
    ]
    
    # First turn
    response = await provider.chat(messages)
    messages.append({"role": "assistant", "content": response["content"]})
    
    # Second turn
    messages.append({"role": "user", "content": "What's your purpose?"})
    response = await provider.chat(messages)
    print(response["content"])
```

#### Token Counting

```python
provider = OpenAIProvider(api_key="your-key")

# Count tokens in a text
text = "This is a sample text for token counting."
token_count = provider.count_tokens(text)
print(f"Tokens: {token_count}")

# Check model token limit
limit = provider.get_model_limit()
print(f"Model token limit: {limit}")
```

#### With Additional Parameters

```python
response = await provider.chat(
    messages=[{"role": "user", "content": "Hello"}],
    top_p=0.9,  # Nucleus sampling
    frequency_penalty=0.5,  # Reduce repetition
    presence_penalty=0.5  # Encourage topic diversity
)
```

### Error Handling

The provider includes a proper exception hierarchy:

```python
from llm_providers import (
    OpenAIProvider,
    APIKeyMissingError,
    RateLimitExceededError,
    TokenLimitExceededError,
    OpenAIProviderError
)

try:
    provider = OpenAIProvider(api_key="your-key")
    response = await provider.chat(messages)
except APIKeyMissingError:
    print("API key is missing or invalid")
except RateLimitExceededError:
    print("Rate limit exceeded, try again later")
except TokenLimitExceededError:
    print("Token limit exceeded, reduce message size")
except OpenAIProviderError as e:
    print(f"Provider error: {e}")
```

### Environment Variables

Load API key from environment:

```bash
export OPENAI_API_KEY="sk-..."
```

```python
# No need to pass api_key parameter
provider = OpenAIProvider(model_name="gpt-4o-mini")
```

## Testing

Unit tests are provided with mocked API calls:

```bash
cd packages/backend
uv run pytest tests/unit/test_openai_provider.py -v
```

### Test Coverage

- ✅ Initialization with various configurations
- ✅ API key handling (parameter and environment)
- ✅ Parameter validation (temperature, max_tokens)
- ✅ Chat completion with mocked responses
- ✅ Error handling (rate limits, token limits, API errors)
- ✅ Token counting
- ✅ Multiple model configurations

## Architecture

### Design Principles

1. **Simple and Clean**: Focus on clarity and ease of use
2. **Configuration-First**: All parameters validated at initialization
3. **Proper Error Handling**: Specific exceptions for different error types
4. **Testable**: All external dependencies can be mocked
5. **Type-Safe**: Full type hints for better IDE support

### Class Structure

```
OpenAIProvider
├── __init__()          # Initialize with configuration
├── chat()              # Send chat completion request
├── count_tokens()      # Count tokens in text
├── get_model_limit()   # Get model's token limit
└── __repr__()          # String representation
```

### Exception Hierarchy

```
OpenAIProviderError (base)
├── APIKeyMissingError
├── RateLimitExceededError
└── TokenLimitExceededError
```

## Future Enhancements

This is the initial OpenAI-only implementation to prove the concept. Future additions may include:

- [ ] Streaming support for real-time responses
- [ ] Retry logic with exponential backoff
- [ ] Additional providers (Claude, DeepSeek, Grok)
- [ ] Cost tracking and budgeting
- [ ] Response caching
- [ ] Batch request support

## Development

### Adding New Features

1. Update `openai_provider.py` with new functionality
2. Add corresponding tests in `tests/unit/test_openai_provider.py`
3. Update this README with usage examples
4. Run tests to ensure everything works

### Code Style

- Follow PEP 8 style guide
- Use type hints for all parameters and return values
- Add docstrings for all public methods
- Keep methods focused and single-purpose

## License

Part of the TradingAgents project.
