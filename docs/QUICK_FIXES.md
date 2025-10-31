# Quick Fixes Implementation Guide

This guide provides step-by-step instructions to fix the critical issues (P0) identified in the improvement plan.

## Table of Contents

1. [Fix Missing AgentLLMConfig Model](#1-fix-missing-agentllmconfig-model)
2. [Fix Test Infrastructure](#2-fix-test-infrastructure)
3. [Update Deprecated UV Configuration](#3-update-deprecated-uv-configuration)
4. [Verification Steps](#verification-steps)

---

## 1. Fix Missing AgentLLMConfig Model

**Problem**: `app/db/models/agent_llm_config.py` is imported but doesn't exist.

### Step 1: Create the Model File

Create `packages/backend/app/db/models/agent_llm_config.py`:

```python
"""Agent LLM configuration model for storing per-agent LLM settings."""

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class AgentLLMConfig(SQLModel, table=True):
    """Model for storing LLM configuration per agent.
    
    This allows different agents to use different LLM providers and settings.
    """
    
    __tablename__ = "agent_llm_configs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Agent identification
    agent_name: str = Field(index=True, description="Name of the agent")
    agent_role: str = Field(description="Role of the agent (analyst, researcher, etc.)")
    
    # LLM configuration
    llm_provider: str = Field(description="LLM provider (openai, anthropic, google, etc.)")
    model_name: str = Field(description="Model name (gpt-4o, claude-3-opus, etc.)")
    
    # Model parameters
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, description="Max tokens for response")
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    frequency_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: Optional[float] = Field(default=0.0, ge=-2.0, le=2.0)
    
    # Cost management
    max_cost_per_request: Optional[float] = Field(
        default=None,
        description="Maximum cost per request in USD"
    )
    
    # API configuration
    api_key_ref: Optional[str] = Field(
        default=None,
        description="Reference to API key in secrets manager"
    )
    api_base_url: Optional[str] = Field(
        default=None,
        description="Custom API base URL if needed"
    )
    
    # Metadata
    is_active: bool = Field(default=True, description="Whether this config is active")
    priority: int = Field(default=0, description="Priority for selection (higher = preferred)")
    
    # Tracking
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Usage statistics
    total_requests: int = Field(default=0, description="Total number of requests")
    total_tokens: int = Field(default=0, description="Total tokens consumed")
    total_cost: float = Field(default=0.0, description="Total cost in USD")
    
    class Config:
        json_schema_extra = {
            "example": {
                "agent_name": "fundamental_analyst",
                "agent_role": "analyst",
                "llm_provider": "openai",
                "model_name": "gpt-4o",
                "temperature": 0.7,
                "max_tokens": 2000,
                "is_active": True,
                "priority": 1
            }
        }
```

### Step 2: Create Alembic Migration

Generate a new migration:

```bash
cd packages/backend
uv run alembic revision --autogenerate -m "Add agent_llm_configs table"
```

Review and edit the generated migration file if needed:

```python
# alembic/versions/XXXX_add_agent_llm_configs.py

def upgrade() -> None:
    op.create_table(
        'agent_llm_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_name', sa.String(), nullable=False),
        sa.Column('agent_role', sa.String(), nullable=False),
        sa.Column('llm_provider', sa.String(), nullable=False),
        sa.Column('model_name', sa.String(), nullable=False),
        sa.Column('temperature', sa.Float(), nullable=False),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('top_p', sa.Float(), nullable=True),
        sa.Column('frequency_penalty', sa.Float(), nullable=True),
        sa.Column('presence_penalty', sa.Float(), nullable=True),
        sa.Column('max_cost_per_request', sa.Float(), nullable=True),
        sa.Column('api_key_ref', sa.String(), nullable=True),
        sa.Column('api_base_url', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('total_requests', sa.Integer(), nullable=False),
        sa.Column('total_tokens', sa.Integer(), nullable=False),
        sa.Column('total_cost', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_agent_llm_configs_agent_name', 'agent_llm_configs', ['agent_name'])


def downgrade() -> None:
    op.drop_index('ix_agent_llm_configs_agent_name')
    op.drop_table('agent_llm_configs')
```

Apply the migration:

```bash
uv run alembic upgrade head
```

### Step 3: Create Repository (Optional)

Create `packages/backend/app/repositories/agent_llm_config.py`:

```python
"""Repository for agent LLM configuration management."""

from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db.models import AgentLLMConfig


class AgentLLMConfigRepository:
    """Repository for agent LLM configurations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_agent_name(self, agent_name: str) -> Optional[AgentLLMConfig]:
        """Get active LLM config for an agent by name."""
        result = await self.session.execute(
            select(AgentLLMConfig)
            .where(AgentLLMConfig.agent_name == agent_name)
            .where(AgentLLMConfig.is_active == True)
            .order_by(AgentLLMConfig.priority.desc())
        )
        return result.scalar_one_or_none()
    
    async def list_active(self) -> List[AgentLLMConfig]:
        """List all active configurations."""
        result = await self.session.execute(
            select(AgentLLMConfig)
            .where(AgentLLMConfig.is_active == True)
            .order_by(AgentLLMConfig.agent_name, AgentLLMConfig.priority.desc())
        )
        return list(result.scalars().all())
```

---

## 2. Fix Test Infrastructure

**Problem**: Tests cannot import modules due to path issues.

### Step 1: Add pytest Configuration

Update `packages/backend/pyproject.toml` to include the correct Python path:

```toml
[tool.pytest.ini_options]
pythonpath = [".", "app", "src"]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = [
    "--verbose",
    "--cov=src",
    "--cov=app",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-report=xml",
    "--asyncio-mode=auto",
]
asyncio_mode = "auto"
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "slow: Slow running tests",
]
```

### Step 2: Update Test Package Scripts

Update `packages/backend/package.json`:

```json
{
  "name": "@tradingagents/backend",
  "version": "0.1.0",
  "scripts": {
    "sync": "uv sync",
    "run": "uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000",
    "cli": "uv run python -m cli.main",
    "test": "PYTHONPATH=. uv run pytest tests/",
    "test:unit": "PYTHONPATH=. uv run pytest tests/unit -m unit",
    "test:integration": "PYTHONPATH=. uv run pytest tests/integration -m integration",
    "test:coverage": "PYTHONPATH=. uv run pytest tests/ --cov --cov-report=html",
    "lint": "uv run ruff check .",
    "format": "uv run ruff format .",
    "type-check": "uv run mypy src/ app/"
  }
}
```

### Step 3: Verify Test Structure

Ensure test directory structure is correct:

```
tests/
├── __init__.py              # Make tests a package
├── conftest.py              # Shared fixtures
├── unit/
│   ├── __init__.py
│   ├── test_services.py
│   └── test_plugins.py
├── integration/
│   ├── __init__.py
│   └── test_api.py
└── e2e/
    ├── __init__.py
    └── test_workflows.py
```

Add `__init__.py` files where missing:

```bash
cd packages/backend
touch tests/__init__.py
touch tests/unit/__init__.py
touch tests/integration/__init__.py
touch tests/e2e/__init__.py
```

---

## 3. Update Deprecated UV Configuration

**Problem**: Using deprecated `tool.uv.dev-dependencies`.

### Step 1: Update pyproject.toml

Replace the deprecated section in `packages/backend/pyproject.toml`:

**Before:**
```toml
[tool.uv]
dev-dependencies = [
    "ruff>=0.6.9",
    "pytest>=8.0.0",
    # ... other deps
]
```

**After:**
```toml
[dependency-groups]
dev = [
    "ruff>=0.6.9",
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
    "httpx>=0.27.0",
    "mypy>=1.8.0",
    "pre-commit>=3.6.0",
    "fakeredis>=2.21.0",
]
```

### Step 2: Reinstall Dependencies

```bash
cd packages/backend
uv sync
```

### Step 3: Verify Installation

```bash
uv run pytest --version
uv run ruff --version
uv run mypy --version
```

---

## Verification Steps

### 1. Verify Model Import

```bash
cd packages/backend
uv run python -c "from app.db.models import AgentLLMConfig; print('✓ Model import successful')"
```

### 2. Verify Database Migration

```bash
cd packages/backend
uv run alembic current
uv run alembic history
```

### 3. Run Tests

```bash
cd packages/backend

# Collect tests (should not error)
uv run pytest --collect-only

# Run specific test file
uv run pytest tests/unit/test_config.py -v

# Run all tests
pnpm test
```

### 4. Verify Backend Startup

```bash
cd packages/backend
uv run uvicorn app.main:app --reload
# Check http://localhost:8000/docs
```

### 5. Full System Check

```bash
# From project root
pnpm sync
pnpm lint
pnpm --filter @tradingagents/backend test
```

---

## Expected Results

After completing these fixes:

- ✅ All imports should work without errors
- ✅ Tests can be collected and run
- ✅ Database migrations apply successfully
- ✅ No deprecation warnings from UV
- ✅ Backend starts without import errors
- ✅ CI pipeline should pass

---

## Troubleshooting

### Issue: Still getting import errors

**Solution**: Ensure you're running commands from the correct directory and PYTHONPATH is set:

```bash
cd packages/backend
export PYTHONPATH=/home/engine/project/packages/backend:$PYTHONPATH
uv run pytest
```

### Issue: Migration fails

**Solution**: Check if the table already exists:

```bash
uv run python -c "from app.db.session import DatabaseManager; import asyncio; asyncio.run(DatabaseManager().create_tables())"
```

### Issue: UV sync fails

**Solution**: Clear the UV cache and reinstall:

```bash
uv cache clean
uv sync --reinstall
```

---

## Next Steps

After completing P0 fixes:

1. Review the full [IMPROVEMENT_PLAN.md](../IMPROVEMENT_PLAN.md)
2. Start P1 tasks (Error Handling, Testing, Authentication)
3. Set up monitoring for the metrics in the improvement plan
4. Schedule regular reviews to track progress

---

**Questions?** Open an issue on GitHub or ask in Discord.
