# Agent LLM Configuration Integration

This document explains how agent-specific LLM configurations from the database are wired into the TradingAgentsGraph runtime.

## Overview

The system now supports configuring each agent with its own LLM provider and settings stored in the database. When agents are created, they automatically use their configured LLMs instead of the default settings.

## Architecture

### Components

1. **AgentLLMConfig Model** (`app/db/models/agent_llm_config.py`)
   - Stores LLM configuration per agent in the database
   - Fields: provider, model_name, temperature, max_tokens, etc.

2. **AgentLLMRuntime** (`app/services/llm_runtime.py`)
   - Loads agent LLM configurations from database
   - Creates and caches LLM instances
   - Provides ManagedLLM wrappers with usage tracking

3. **LLM Integration Helpers** (`src/tradingagents/graph/llm_integration.py`)
   - `create_agent_llm_runtime()`: Creates runtime from config
   - `create_trading_graph_with_llm_runtime()`: Creates graph with runtime

4. **TradingAgentsGraph** (`src/tradingagents/graph/trading_graph.py`)
   - Accepts optional `llm_runtime` parameter
   - Uses `_resolve_llm()` method to get LLM instances
   - Falls back to default LLMs if runtime not available

### Flow

```
Database (agent_llm_configs table)
    ↓
AgentLLMRuntime (loads configs, creates LLM instances)
    ↓
TradingAgentsGraph (uses runtime to resolve agent LLMs)
    ↓
Agents (market_analyst, bull_researcher, etc.)
```

## Usage

### Basic Usage with Database Configuration

```python
from tradingagents.graph import create_trading_graph_with_llm_runtime
from tradingagents.default_config import DEFAULT_CONFIG

# Initialize database first
from app.db import init_db
db_manager = init_db("postgresql://...")

# Create graph with LLM runtime
# This automatically loads agent configs from database
graph = create_trading_graph_with_llm_runtime(
    base_config=DEFAULT_CONFIG,
    selected_analysts=["market", "social", "news", "fundamentals"],
)

# Agents will use their configured LLMs from database
final_state, decision = graph.propagate("AAPL", "2024-01-15")
```

### Manual Configuration

```python
from tradingagents.graph import TradingAgentsGraph, create_agent_llm_runtime
from tradingagents.default_config import DEFAULT_CONFIG

# Create runtime manually
runtime = create_agent_llm_runtime(DEFAULT_CONFIG)

# Create graph with runtime
graph = TradingAgentsGraph(
    selected_analysts=["market", "fundamentals"],
    config=DEFAULT_CONFIG,
    llm_runtime=runtime,
)
```

### Without Database (Fallback)

```python
from tradingagents.graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

# Create graph without runtime - uses default LLMs
graph = TradingAgentsGraph(
    selected_analysts=["market"],
    config=DEFAULT_CONFIG,
    llm_runtime=None,  # or omit this parameter
)
```

## Configuring Agent LLMs

### Via API

```bash
# Create LLM config for an agent
curl -X POST http://localhost:8000/api/v1/agent-llm/config \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": 1,
    "provider": "openai",
    "model_name": "gpt-4o",
    "temperature": 0.8,
    "max_tokens": 2000,
    "enabled": true
  }'
```

### Via Database

```sql
INSERT INTO agent_llm_configs (
    agent_id,
    provider,
    model_name,
    temperature,
    max_tokens,
    enabled
) VALUES (
    1,  -- ID of the agent from agent_configs table
    'openai',
    'gpt-4o',
    0.8,
    2000,
    true
);
```

### Agent Name to ID Mapping

Agent names used in code (e.g., "market_analyst") correspond to entries in the `agent_configs` table:

| Agent Name | Agent Type | Role |
|------------|------------|------|
| market_analyst | analyst | market |
| social_analyst | analyst | social |
| news_analyst | analyst | news |
| fundamentals_analyst | analyst | fundamentals |
| bull_researcher | researcher | bull |
| bear_researcher | researcher | bear |
| research_manager | manager | research |
| trader | trader | trader |
| risk_manager | manager | risk |
| risky_analyst | risk_analyst | risky |
| safe_analyst | risk_analyst | safe |
| neutral_analyst | risk_analyst | neutral |

## Agent Factory Functions (Alternative)

For simpler use cases outside of TradingAgentsGraph, you can use the factory functions:

```python
from tradingagents.llm_providers import (
    get_llm_for_agent,
    get_llm_for_agent_by_name,
    clear_llm_cache,
)

# Get LLM for agent by database ID
llm = get_llm_for_agent(agent_id=1)

# Get LLM for agent by name
llm = get_llm_for_agent_by_name("market_analyst")

# Clear cache after updating configs
clear_llm_cache()
```

**Note:** These functions have limitations when called from async contexts and primarily use default settings. For production use, prefer the AgentLLMRuntime approach.

## Default Behavior

When no LLM configuration exists for an agent:
- The agent uses default OpenAI GPT-4 settings
- Temperature: 0.7
- No max_tokens limit

This ensures agents always work even without database configuration.

## Cache Management

LLM instances are cached to avoid recreating them on every use:

- **AgentLLMRuntime**: Automatically refreshes when database configs change
- **Factory functions**: Manual cache clearing with `clear_llm_cache()`

To force a reload after changing configs:
```python
runtime.refresh_if_needed(force=True)
```

## Testing

### Unit Tests

Located in `tests/unit/test_graph_llm_integration.py`:

```bash
pytest tests/unit/test_graph_llm_integration.py -v
```

### Integration Tests

Located in `tests/integration/test_llm_config_factory.py`:

```bash
pytest tests/integration/test_llm_config_factory.py -v
```

## Troubleshooting

### Agents Not Using Configured LLMs

1. Check if AgentLLMRuntime is being passed to TradingAgentsGraph
2. Verify agent_id in database matches agent name
3. Ensure LLM config is enabled in database
4. Check logs for runtime initialization errors

### Database Connection Issues

If database is not available:
- TradingAgentsGraph falls back to default LLMs
- Warning logged: "AgentLLMRuntime not available"
- Agents still work with default settings

### API Key Errors

Ensure environment variables are set:
```bash
export OPENAI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
export DEEPSEEK_API_KEY="your-key"
export GROK_API_KEY="your-key"
```

## Future Enhancements

- Hot-reload of configurations without restart
- Fallback provider support
- Usage tracking and cost monitoring
- Per-agent rate limiting
- Model performance metrics
