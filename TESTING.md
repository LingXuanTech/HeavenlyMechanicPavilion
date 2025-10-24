# Testing Guide

This document provides comprehensive instructions for running tests across the TradingAgents codebase.

## Overview

The project uses a comprehensive testing strategy covering:
- **Backend (Python)**: pytest with fixtures for database/redis, unit and integration tests
- **Frontend (Next.js)**: Vitest for unit tests, Playwright for E2E tests
- **Shared package**: Vitest for utility function tests
- **Static Analysis**: mypy for type checking, ruff for linting

## Backend Testing

### Setup

```bash
cd packages/backend
uv sync
```

### Running Tests

```bash
# Run all tests
pnpm --filter @tradingagents/backend test

# Run with coverage
pnpm --filter @tradingagents/backend coverage

# Run specific test files
uv run pytest tests/unit/test_plugin_registry.py
uv run pytest tests/integration/test_api_endpoints.py

# Run tests by marker
uv run pytest -m unit           # Unit tests only
uv run pytest -m integration    # Integration tests only
```

### Test Structure

```
packages/backend/tests/
├── conftest.py                      # Shared fixtures
├── unit/                            # Unit tests
│   ├── test_plugin_registry.py      # Plugin system tests
│   ├── test_risk_management.py      # Risk management tests
│   ├── test_config_loader.py        # Configuration tests
│   └── test_trading_service.py      # Trading service tests
└── integration/                     # Integration tests
    └── test_api_endpoints.py        # API endpoint tests
```

### Available Fixtures

The `conftest.py` provides the following fixtures:

- `test_db`: In-memory SQLite database for testing
- `db_session`: Database session for tests
- `redis_client`: Fake Redis client
- `redis_manager`: Redis manager with fake client
- `mock_openai_client`: Mocked OpenAI client
- `mock_trading_graph`: Mocked TradingAgentsGraph
- `async_client`: Async HTTP client for API tests
- `sync_client`: Sync test client for API tests
- `sample_trading_config`: Sample trading configuration
- `sample_market_data`: Sample market data
- `sample_portfolio`: Sample portfolio data
- `sample_risk_params`: Sample risk parameters
- `mock_plugin_registry`: Mocked plugin registry

## Frontend Testing

### Setup

```bash
cd packages/frontend
pnpm install
```

### Unit Tests (Vitest)

```bash
# Run unit tests
pnpm --filter @tradingagents/frontend test

# Run with UI
pnpm --filter @tradingagents/frontend test:ui

# Run with coverage
pnpm --filter @tradingagents/frontend test:coverage
```

### E2E Tests (Playwright)

```bash
# Install Playwright browsers (first time only)
pnpm --filter @tradingagents/frontend exec playwright install

# Run E2E tests
pnpm --filter @tradingagents/frontend test:e2e

# Run E2E tests with UI
pnpm --filter @tradingagents/frontend test:e2e:ui
```

### Test Structure

```
packages/frontend/
├── src/test/
│   ├── setup.ts                     # Vitest setup
│   ├── components/                  # Component tests
│   │   └── Button.test.tsx
│   └── e2e/                         # E2E tests
│       └── home.spec.ts
├── vitest.config.ts                 # Vitest configuration
└── playwright.config.ts             # Playwright configuration
```

## Shared Package Testing

### Running Tests

```bash
# Run unit tests
pnpm --filter @tradingagents/shared test

# Run with coverage
pnpm --filter @tradingagents/shared test -- --coverage
```

## Static Analysis

### Linting (Ruff)

```bash
# Backend linting
pnpm --filter @tradingagents/backend lint

# Frontend linting
pnpm --filter @tradingagents/frontend lint

# Format code
pnpm --filter @tradingagents/backend format
```

### Type Checking

```bash
# Backend type check (mypy)
pnpm --filter @tradingagents/backend type-check

# Frontend type check (tsc)
pnpm --filter @tradingagents/frontend type-check
pnpm --filter @tradingagents/shared type-check
```

## Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality. Install them with:

```bash
# Install pre-commit
pip install pre-commit

# Install the hooks
pre-commit install
```

Pre-commit will automatically run:
- Trailing whitespace removal
- File ending fixes
- YAML/JSON validation
- Ruff linting and formatting
- Mypy type checking
- ESLint for frontend code

### Running Pre-commit Manually

```bash
# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files
pre-commit run mypy --all-files
```

## Continuous Integration

### GitHub Actions Workflows

The project includes three CI workflows:

1. **`python-ci.yml`**: Comprehensive Python testing
   - Linting with ruff
   - Type checking with mypy
   - Tests on Python 3.10, 3.11, 3.12
   - Plugin system verification
   - Coverage reporting

2. **`node-ci.yml`**: Comprehensive Node testing
   - Linting and type checking
   - Vitest unit tests for shared and frontend
   - Playwright E2E tests
   - Build verification

3. **`ci.yml`**: Combined workflow running both in parallel
   - Faster feedback for common changes
   - Parallel execution with caching

### Workflow Triggers

Workflows run on:
- Push to `main`, `develop`, or `ci-testing-*` branches
- Pull requests to `main` or `develop`

### Caching Strategy

All workflows use caching to speed up execution:
- Python: uv cache and virtualenv
- Node: pnpm store
- Playwright: Browser binaries

## Coverage Reports

### Backend Coverage

```bash
cd packages/backend
uv run pytest --cov=src --cov=app --cov-report=html

# Open coverage report
open htmlcov/index.html
```

### Frontend Coverage

```bash
cd packages/frontend
pnpm test:coverage

# Open coverage report
open coverage/index.html
```

### Coverage Thresholds

The project aims for:
- Unit tests: >80% coverage
- Integration tests: >60% coverage
- Overall: >70% coverage

## Writing Tests

### Backend Test Example

```python
import pytest
from app.services.risk_management import RiskConstraints

@pytest.mark.unit
def test_risk_constraints():
    """Test risk constraints initialization."""
    constraints = RiskConstraints(max_position_weight=0.15)
    assert constraints.max_position_weight == 0.15

@pytest.mark.asyncio
async def test_api_endpoint(async_client):
    """Test API endpoint."""
    response = await async_client.get("/health")
    assert response.status_code == 200
```

### Frontend Test Example

```typescript
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent />)
    expect(screen.getByText('Hello')).toBeInTheDocument()
  })
})
```

### E2E Test Example

```typescript
import { test, expect } from '@playwright/test'

test('home page loads', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveTitle(/TradingAgents/)
})
```

## Troubleshooting

### Common Issues

#### Import Errors in Tests

Make sure you've installed all dependencies:
```bash
cd packages/backend
uv sync
```

#### Async Test Failures

Ensure tests are marked with `@pytest.mark.asyncio`:
```python
@pytest.mark.asyncio
async def test_my_async_function():
    result = await my_async_function()
    assert result is not None
```

#### Playwright Browser Not Installed

Install Playwright browsers:
```bash
pnpm --filter @tradingagents/frontend exec playwright install
```

#### Redis Connection Errors

Tests use fake Redis by default. If you see connection errors, check that `fakeredis` is installed:
```bash
uv pip install fakeredis
```

## Best Practices

1. **Test Naming**: Use descriptive names that explain what is being tested
2. **Fixtures**: Leverage fixtures for common test setup
3. **Markers**: Use pytest markers to categorize tests (`unit`, `integration`, `e2e`, `slow`)
4. **Mocking**: Mock external dependencies (APIs, databases) in unit tests
5. **Coverage**: Aim for high coverage but focus on meaningful tests
6. **Fast Tests**: Keep unit tests fast (<1s each)
7. **Isolation**: Tests should not depend on each other
8. **Cleanup**: Use fixtures and context managers for proper cleanup

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [Vitest documentation](https://vitest.dev/)
- [Playwright documentation](https://playwright.dev/)
- [Testing Library](https://testing-library.com/)
- [Ruff documentation](https://docs.astral.sh/ruff/)
- [mypy documentation](https://mypy.readthedocs.io/)
