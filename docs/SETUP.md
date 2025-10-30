# Setup Guide

This guide walks through preparing a local development environment for TradingAgents, installing dependencies, configuring API keys, and launching the CLI, backend, and frontend services.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Clone the Repository](#clone-the-repository)
3. [Python Environment](#python-environment)
4. [Install Backend Dependencies](#install-backend-dependencies)
5. [Install Frontend Dependencies](#install-frontend-dependencies)
6. [Configure Environment Variables](#configure-environment-variables)
7. [Run the CLI](#run-the-cli)
8. [Start the FastAPI Backend](#start-the-fastapi-backend)
9. [Launch the Frontend Control Center](#launch-the-frontend-control-center)
10. [Next Steps](#next-steps)

## Prerequisites

| Tool | Minimum Version | Notes |
| --- | --- | --- |
| Python | 3.10 | Tested with 3.10–3.13 |
| Node.js | 20.x | Install via `nvm`, `asdf`, or your OS package manager |
| pnpm | 9.x | Used for workspace orchestration |
| uv | latest | Optional (installed automatically via `pnpm sync`) |
| Docker | 20.10+ | Only required for containerised deployment |

> **Tip:** If you prefer to manage Python environments manually, ensure `pip`, `venv`, or `conda` is available.

## Clone the Repository

```bash
git clone https://github.com/TauricResearch/TradingAgents.git
cd TradingAgents
```

TradingAgents is a PNPM workspace. All packages live under `packages/`, and helper tooling lives in `scripts/`.

## Python Environment

Create and activate an isolated Python environment using your preferred tool. Examples:

<details>
<summary>uv</summary>

```bash
uv venv .venv
source .venv/bin/activate
```

</details>

<details>
<summary>python -m venv</summary>

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\activate
```

</details>

<details>
<summary>conda</summary>

```bash
conda create -n tradingagents python=3.13
conda activate tradingagents
```

</details>

## Install Backend Dependencies

From the repository root, run the workspace synchronisation helper:

```bash
pnpm sync
```

This command installs all PNPM workspace dependencies and executes `uv sync` inside `packages/backend`, ensuring Python requirements are resolved. If you prefer to manage the backend manually:

```bash
cd packages/backend
uv sync  # or: pip install -r requirements.txt
```

## Install Frontend Dependencies

The frontend shares the workspace toolchain. To install only the frontend dependencies:

```bash
pnpm --filter @tradingagents/frontend install
```

For development builds, pnpm will install the necessary tooling automatically when you run the frontend dev server.

## Configure Environment Variables

Create a local `.env` file based on the provided template:

```bash
cp .env.example .env
```

Populate the required keys. At minimum:

```env
OPENAI_API_KEY=sk-your-openai-key
ALPHA_VANTAGE_API_KEY=your-alpha-vantage-key
```

You can add optional providers (Anthropic, Google, Finnhub, etc.) later. See [docs/CONFIGURATION.md](./CONFIGURATION.md) for a full catalogue of environment variables, defaults, and tuning tips.

## Run the CLI

The CLI coordinates the full LangGraph workflow interactively:

```bash
pnpm cli
# or
make cli
```

Both commands invoke `uv run python -m cli.main` inside `packages/backend`. You will be prompted for ticker symbols, trade date, LLM providers, debate depth, and other options. Results stream live in the terminal.

## Start the FastAPI Backend

To expose REST, SSE, and WebSocket endpoints, start the FastAPI application:

```bash
cd packages/backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Useful URLs:

- API root: [http://localhost:8000/](http://localhost:8000/)
- Interactive docs (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)
- Health check: [http://localhost:8000/health](http://localhost:8000/health)

Workers and streaming endpoints require Redis. Enable them by setting the relevant environment variables (`REDIS_ENABLED=true`, etc.) before launching the server.

## Launch the Frontend Control Center

The Next.js dashboard provides a graphical view of agent progress, trades, and risk checks.

```bash
pnpm --filter @tradingagents/frontend dev
```

By default the app listens on [http://localhost:3000](http://localhost:3000). To point the UI at a non-default backend, create `packages/frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

When running with Docker (see [docs/DEPLOYMENT.md](./DEPLOYMENT.md)), environment variables are injected automatically from the Compose stack.

## Next Steps

- Read [docs/DEVELOPMENT.md](./DEVELOPMENT.md) for testing, linting, and contribution workflows.
- Explore the backend endpoints in [docs/API.md](./API.md).
- Plan a containerised rollout with [docs/DEPLOYMENT.md](./DEPLOYMENT.md).
- Review architecture and subsystem design in [docs/ARCHITECTURE.md](./ARCHITECTURE.md).

Happy building! 🚀
