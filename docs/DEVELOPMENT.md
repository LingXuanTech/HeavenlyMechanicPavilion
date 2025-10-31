# Development Guide

This document captures day-to-day workflows for contributing to TradingAgents: running tests, linting, type checking, using workspace tooling, and preparing pull requests.

## Table of Contents

1. [Workspace Overview](#workspace-overview)
2. [Common Commands](#common-commands)
3. [Testing Strategy](#testing-strategy)
4. [Static Analysis](#static-analysis)
5. [Pre-commit Hooks](#pre-commit-hooks)
6. [Continuous Integration](#continuous-integration)
7. [Contribution Checklist](#contribution-checklist)

## Workspace Overview

TradingAgents is managed via PNPM workspaces with language-specific tooling inside each package.

```
pnpm-workspace
├── packages/backend     # Python (LangGraph, FastAPI)
├── packages/frontend    # Next.js dashboard
└── packages/shared      # Shared TypeScript utilities & clients
```

`pnpm` scripts and `make` helpers wrap common workflows. Under the hood we rely on:

- `uv` for Python dependency and execution management
- `pytest`, `ruff`, and `mypy` for backend testing and static checks
- `vitest`, `playwright`, and `eslint` for frontend verification
- `pnpm` for TypeScript tooling across frontend/shared packages

## Common Commands

```bash
pnpm sync                # Install workspace deps and run uv sync for the backend
pnpm cli                 # Launch the interactive CLI
make cli                 # Same as pnpm cli (using uv under the hood)
make backend-dev         # Example helper for backend development (if defined)
```

From within `packages/backend` you can also run `uv` directly:

```bash
cd packages/backend
uv run python -m cli.main
uv run uvicorn app.main:app --reload
```

## Testing Strategy

TradingAgents embraces a multi-layer test suite spanning Python and TypeScript packages.

### Backend (Python)

```bash
# Run all backend tests
pnpm --filter @tradingagents/backend test

# Run with coverage reporting
pnpm --filter @tradingagents/backend coverage

# Target a specific file (direct pytest invocation)
cd packages/backend
uv run pytest tests/unit/test_plugin_registry.py
uv run pytest tests/integration/test_api_endpoints.py

# Use pytest markers
uv run pytest -m unit
uv run pytest -m integration
```

Backend tests rely on fixtures defined in `packages/backend/tests/conftest.py`, including in-memory databases, Redis fakes, and mock LLM clients.

#### Environment Setup for Tests

The test infrastructure requires proper Python path configuration to discover both the `app` module (FastAPI application) and `src` packages (tradingagents, cli, llm_providers). This is configured in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
pythonpath = [".", "src"]
```

If tests fail with `ModuleNotFoundError` for `app` or `tradingagents` modules, ensure you're running tests from the `packages/backend` directory and that `pyproject.toml` has the correct `pythonpath` configuration.

### Frontend (Next.js)

```bash
# Component and utility tests (Vitest)
pnpm --filter @tradingagents/frontend test
pnpm --filter @tradingagents/frontend test:ui
pnpm --filter @tradingagents/frontend test:coverage

# End-to-end browser tests (Playwright)
pnpm --filter @tradingagents/frontend exec playwright install  # First time only
pnpm --filter @tradingagents/frontend test:e2e
pnpm --filter @tradingagents/frontend test:e2e:ui
```

Vitest setup files live under `packages/frontend/src/test/`, while Playwright specifications live in `packages/frontend/src/test/e2e/`.

### Shared Package

```bash
pnpm --filter @tradingagents/shared test
pnpm --filter @tradingagents/shared test -- --coverage
```

## Static Analysis

### Linting

```bash
# Python (ruff)
pnpm --filter @tradingagents/backend lint

# Frontend & shared (eslint)
pnpm --filter @tradingagents/frontend lint
pnpm --filter @tradingagents/shared lint
```

### Formatting

```bash
pnpm --filter @tradingagents/backend format
pnpm --filter @tradingagents/frontend format
```

### Type Checking

```bash
# Python (mypy)
pnpm --filter @tradingagents/backend type-check

# TypeScript (tsc)
pnpm --filter @tradingagents/frontend type-check
pnpm --filter @tradingagents/shared type-check
```

## Pre-commit Hooks

Enable pre-commit to automatically run linting and type checks before each commit:

```bash
pip install pre-commit
pre-commit install
```

Useful invocations:

```bash
pre-commit run --all-files              # Run every hook
pre-commit run ruff --all-files         # Only Python linting
pre-commit run mypy --all-files         # Only Python type checking
```

The hook configuration covers trailing whitespace cleanup, formatting, Ruff, Mypy, and ESLint/TypeScript runs for the relevant paths.

## Continuous Integration

GitHub Actions enforce the same standards in CI:

1. **python-ci** – Ruff, Mypy, pytest (matrix on Python 3.10–3.12), plugin validation, coverage
2. **node-ci** – ESLint, type-checking, Vitest, Playwright, build verification
3. **ci** – Combined pipeline that executes the Node and Python jobs in parallel for faster feedback

Workflows trigger on pushes to `main`, `develop`, `ci-testing-*`, and on pull requests targeting those branches. Caching is configured for uv/virtualenv, pnpm, and Playwright assets to reduce runtime.

## Contribution Checklist

Before opening a pull request:

- [ ] Update or add tests covering your change
- [ ] Run the relevant test suites (backend, frontend, shared)
- [ ] Ensure Ruff, Mypy, ESLint, and TypeScript checks pass
- [ ] Run `pre-commit run --all-files`
- [ ] Update documentation when behaviour, configuration, or APIs change
- [ ] Provide clear commit messages and describe your change in the PR template

Need more detail on architecture or API surface? Consult [docs/ARCHITECTURE.md](./ARCHITECTURE.md) and [docs/API.md](./API.md).
