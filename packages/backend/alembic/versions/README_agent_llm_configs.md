# Agent LLM Configs Migration

## Overview

This migration adds the `agent_llm_configs` table to support per-agent LLM provider configurations with multi-provider support (OpenAI, DeepSeek, Grok, Claude).

## Migration Details

- **Revision ID**: add_agent_llm_configs
- **Previous Revision**: add_trading_session_risk
- **Created**: 2025-01-15

## Changes

### New Table: agent_llm_configs

Stores LLM provider configurations for each agent with support for:
- Multiple providers per agent
- API key overrides (encrypted)
- Fallback configurations
- Cost tracking
- Enable/disable configs

### Schema

```sql
CREATE TABLE agent_llm_configs (
    id INTEGER PRIMARY KEY,
    agent_id INTEGER NOT NULL REFERENCES agent_configs(id),
    provider VARCHAR(50) NOT NULL,
    model_name VARCHAR(100) NOT NULL,
    temperature FLOAT DEFAULT 0.7,
    max_tokens INTEGER,
    top_p FLOAT,
    api_key_encrypted VARCHAR(500),
    fallback_provider VARCHAR(50),
    fallback_model VARCHAR(100),
    cost_per_1k_input_tokens FLOAT DEFAULT 0.0,
    cost_per_1k_output_tokens FLOAT DEFAULT 0.0,
    enabled BOOLEAN DEFAULT TRUE,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    metadata_json TEXT
);

CREATE INDEX ix_agent_llm_configs_agent_id ON agent_llm_configs(agent_id);
CREATE INDEX ix_agent_llm_configs_enabled ON agent_llm_configs(enabled);
CREATE INDEX ix_agent_llm_configs_provider ON agent_llm_configs(provider);
```

## Running the Migration

### Upgrade

```bash
cd packages/backend
alembic upgrade head
```

### Downgrade

```bash
cd packages/backend
alembic downgrade -1
```

## Related Components

### Models
- `app/db/models/agent_llm_config.py` - SQLModel definition

### Schemas
- `app/schemas/agent_llm_config.py` - Pydantic schemas

### Services
- `app/services/agent_llm_config.py` - Business logic
- `app/repositories/agent_llm_config.py` - Database operations

### LLM Providers
- `tradingagents/llm_providers/` - Provider abstraction layer

## Usage Example

```python
from app.services.agent_llm_config import AgentLLMConfigService
from app.schemas.agent_llm_config import AgentLLMConfigCreate

# Create LLM config for an agent
service = AgentLLMConfigService(db_session)

config = await service.create_config(
    AgentLLMConfigCreate(
        agent_id=1,
        provider="openai",
        model_name="gpt-4o-mini",
        temperature=0.7,
        max_tokens=1000,
        api_key="optional-override",  # Will be encrypted
        fallback_provider="claude",
        fallback_model="claude-3-haiku-20240307",
    )
)
```

## Security Notes

- API keys stored in `api_key_encrypted` field are encrypted using Fernet encryption
- Encryption key must be set in `ENCRYPTION_KEY` environment variable
- Global API keys are loaded from environment variables (OPENAI_API_KEY, etc.)
- Per-agent overrides take precedence over global keys

## Testing

Run tests with:

```bash
pytest tests/unit/test_agent_llm_config_service.py
```

## Rollback Considerations

Rolling back this migration will:
- Drop the `agent_llm_configs` table
- Remove all stored LLM configurations
- Agents will fall back to using the `llm_provider` and `llm_model` fields in `agent_configs` table

Ensure you have backups before rolling back in production.
