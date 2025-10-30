# Agent LLM Configuration

This document describes the database schema and implementation for per-agent LLM configuration in the TradingAgents system.

## Overview

The Agent LLM Configuration feature provides a flexible system for configuring LLM providers and parameters on a per-agent basis. This allows different agents in the trading workflow to use different LLM providers, models, and settings optimized for their specific tasks.

## Database Schema

### Table: `agent_llm_configs`

The `agent_llm_configs` table stores LLM configuration settings for each agent.

#### Columns

| Column | Type | Description | Default |
|--------|------|-------------|---------|
| `id` | Integer | Primary key | Auto-increment |
| `agent_id` | Integer | Foreign key to `agent_configs.id` | Required |
| `provider` | String(50) | LLM provider (openai, deepseek, grok, claude) | Required |
| `model_name` | String(100) | Model name (e.g., gpt-4, claude-3-5-sonnet) | Required |
| `temperature` | Float | Sampling temperature (0.0-2.0) | 0.7 |
| `max_tokens` | Integer | Maximum tokens to generate | None |
| `top_p` | Float | Nucleus sampling parameter | None |
| `api_key_encrypted` | String(500) | Encrypted API key override | None |
| `fallback_provider` | String(50) | Fallback provider on failure | None |
| `fallback_model` | String(100) | Fallback model name | None |
| `cost_per_1k_input_tokens` | Float | Cost per 1K input tokens | 0.0 |
| `cost_per_1k_output_tokens` | Float | Cost per 1K output tokens | 0.0 |
| `enabled` | Boolean | Whether this config is active | True |
| `created_at` | DateTime | Creation timestamp | UTC now |
| `updated_at` | DateTime | Last update timestamp | UTC now |
| `metadata_json` | String | Additional metadata as JSON | None |

#### Indexes

- `ix_agent_llm_configs_agent_id` - Index on agent_id for fast lookups
- `ix_agent_llm_configs_provider` - Index on provider for filtering
- `ix_agent_llm_configs_enabled` - Index on enabled flag

#### Relationships

- **Foreign Key**: `agent_id` references `agent_configs.id`
- Each agent can have multiple LLM configurations
- Configurations can be enabled/disabled without deletion

## Data Models

### SQLModel (ORM)

**File**: `packages/backend/app/db/models/agent_llm_config.py`

```python
class AgentLLMConfig(SQLModel, table=True):
    """AgentLLMConfig model for storing LLM provider configurations per agent."""
    
    __tablename__ = "agent_llm_configs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    agent_id: int = Field(foreign_key="agent_configs.id", index=True)
    provider: str = Field(index=True, max_length=50)
    model_name: str = Field(max_length=100)
    temperature: float = Field(default=0.7)
    max_tokens: Optional[int] = Field(default=None)
    # ... additional fields
```

### Pydantic Schemas

**File**: `packages/backend/app/schemas/agent_llm_config.py`

#### AgentLLMConfigCreate

Schema for creating a new LLM configuration:
- `agent_id`: ID of the agent
- `provider`: LLM provider name
- `model_name`: Model identifier
- `temperature`: Sampling temperature (default: 0.7)
- `max_tokens`: Maximum tokens (optional)
- Additional optional fields

#### AgentLLMConfigUpdate

Schema for updating an existing configuration:
- All fields are optional
- Only provided fields will be updated

#### AgentLLMConfigResponse

Schema for API responses:
- Includes all fields from the model
- `has_api_key_override`: Boolean indicating if API key is set
- `created_at` and `updated_at` timestamps
- API key is never exposed in responses

## Database Migrations

### Migration Chain

The migrations are applied in the following order:

1. `ac7a9a8391bc` - Initial migration with all base models
2. `plugin_agent_fields` - Add agent plugin fields to agent_configs
3. `add_trading_session_risk` - Add trading sessions and risk metrics tables
4. `add_agent_llm_configs` - Add agent_llm_configs table

### Migration: add_agent_llm_configs

**File**: `packages/backend/alembic/versions/add_agent_llm_configs_table.py`

**Revision ID**: `add_agent_llm_configs`  
**Revises**: `add_trading_session_risk`  
**Created**: 2025-01-15

#### Upgrade

Creates the `agent_llm_configs` table with:
- All required columns
- Foreign key constraint to agent_configs
- Three indexes (agent_id, provider, enabled)
- Default values for temperature, enabled, and cost fields

#### Downgrade

Drops all indexes and the `agent_llm_configs` table.

### Running Migrations

```bash
cd packages/backend

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View current revision
alembic current

# View migration history
alembic history
```

## Seed Data

### Default Configurations

**File**: `packages/backend/alembic/seed_agent_llm_configs.py`

A seed data script is provided to create default LLM configurations for all existing agents.

Default values:
- Provider: `openai`
- Model: `gpt-4`
- Temperature: `0.7`
- Max Tokens: `2000`
- Enabled: `true`

#### Running Seed Script

```bash
cd packages/backend
python alembic/seed_agent_llm_configs.py
```

The script will:
1. Connect to the database
2. Find all agents without LLM configurations
3. Create default OpenAI configurations
4. Skip agents that already have configurations

## Usage Examples

### Creating an LLM Configuration

```python
from app.services.agent_llm_config import AgentLLMConfigService
from app.schemas.agent_llm_config import AgentLLMConfigCreate

async def configure_agent_llm(agent_id: int):
    service = AgentLLMConfigService(db_session)
    
    config = await service.create_config(
        AgentLLMConfigCreate(
            agent_id=agent_id,
            provider="openai",
            model_name="gpt-4",
            temperature=0.7,
            max_tokens=2000,
            fallback_provider="claude",
            fallback_model="claude-3-haiku-20240307",
        )
    )
    return config
```

### Updating an LLM Configuration

```python
from app.schemas.agent_llm_config import AgentLLMConfigUpdate

async def update_agent_temperature(config_id: int, new_temp: float):
    service = AgentLLMConfigService(db_session)
    
    updated = await service.update_config(
        config_id,
        AgentLLMConfigUpdate(temperature=new_temp)
    )
    return updated
```

### Querying Agent Configurations

```python
# Get all configs for an agent
configs = await service.get_configs_by_agent(agent_id)

# Get primary config (first enabled config)
primary = await service.get_primary_config(agent_id)

# Get specific config by ID
config = await service.get_config(config_id)
```

## Security Considerations

### API Key Encryption

- API keys stored in `api_key_encrypted` are encrypted using Fernet encryption
- Encryption key must be set via `ENCRYPTION_KEY` environment variable
- Keys are never returned in API responses
- Use `has_api_key_override` flag to check if a key is set

### Environment Variables

Default API keys are loaded from environment:
- `OPENAI_API_KEY` - OpenAI API key
- `ANTHROPIC_API_KEY` - Anthropic/Claude API key
- `DEEPSEEK_API_KEY` - DeepSeek API key
- `GROK_API_KEY` - Grok API key
- `ENCRYPTION_KEY` - Encryption key for API key overrides

Per-agent overrides take precedence over global environment keys.

## Testing

### Unit Tests

**File**: `packages/backend/tests/unit/test_agent_llm_config_model.py`

Tests for the SQLModel:
- `test_create_basic_model` - Verify basic model creation
- `test_model_defaults` - Verify default values
- `test_model_with_optional_fields` - Verify optional fields

**File**: `packages/backend/tests/unit/test_agent_llm_config_service.py`

Tests for the service layer (comprehensive):
- Configuration creation and retrieval
- Provider and model validation
- API key encryption
- Configuration updates and deletion
- Health check validation

### Running Tests

```bash
cd packages/backend

# Run all tests
pytest

# Run only agent LLM config tests
pytest tests/unit/test_agent_llm_config_model.py
pytest tests/unit/test_agent_llm_config_service.py

# Run with verbose output
pytest -v tests/unit/test_agent_llm_config_model.py
```

## Future Enhancements

This initial database schema lays the foundation for:

1. **API Endpoints** - RESTful endpoints for managing configurations
2. **Runtime Integration** - Using configs to instantiate LLM clients
3. **Provider Factory** - Dynamic provider selection based on configs
4. **Cost Tracking** - Recording and analyzing LLM usage costs
5. **A/B Testing** - Testing different models/settings per agent
6. **Auto-fallback** - Automatic failover to backup providers

## Related Files

### Models
- `app/db/models/agent_llm_config.py` - SQLModel definition
- `app/db/models/agent_config.py` - Parent agent model

### Schemas
- `app/schemas/agent_llm_config.py` - Pydantic schemas

### Services
- `app/services/agent_llm_config.py` - Business logic layer

### Repositories
- `app/repositories/agent_llm_config.py` - Database operations

### Migrations
- `alembic/versions/add_agent_llm_configs_table.py` - Migration file
- `alembic/versions/README_agent_llm_configs.md` - Migration documentation

### Tests
- `tests/unit/test_agent_llm_config_model.py` - Model tests
- `tests/unit/test_agent_llm_config_service.py` - Service tests

### Seed Data
- `alembic/seed_agent_llm_configs.py` - Default configuration seeding

## Support

For issues or questions about Agent LLM Configuration:

1. Check the migration README: `alembic/versions/README_agent_llm_configs.md`
2. Review test cases for usage examples
3. Check service implementation for business logic details
