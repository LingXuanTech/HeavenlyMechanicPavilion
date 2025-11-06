<p align="center">
  <img src="assets/TauricResearch.png" style="width: 60%; height: auto;" alt="TradingAgents logo">
</p>

<div align="center" style="line-height: 1;">
  <a href="https://arxiv.org/abs/2412.20138" target="_blank"><img alt="arXiv" src="https://img.shields.io/badge/arXiv-2412.20138-B31B1B?logo=arxiv"/></a>
  <a href="https://discord.com/invite/hk9PGKShPK" target="_blank"><img alt="Discord" src="https://img.shields.io/badge/Discord-TradingResearch-7289da?logo=discord&logoColor=white&color=7289da"/></a>
  <a href="./assets/wechat.png" target="_blank"><img alt="WeChat" src="https://img.shields.io/badge/WeChat-TauricResearch-brightgreen?logo=wechat&logoColor=white"/></a>
  <a href="https://x.com/TauricResearch" target="_blank"><img alt="X Follow" src="https://img.shields.io/badge/X-TauricResearch-white?logo=x&logoColor=white"/></a>
  <br>
  <a href="https://github.com/TauricResearch/" target="_blank"><img alt="Community" src="https://img.shields.io/badge/Join_GitHub_Community-TauricResearch-14C290?logo=discourse"/></a>
</div>

---

# TradingAgents: Multi-Agent LLM Financial Trading Framework

TradingAgents orchestrates a team of specialist LLM-driven agents – analysts, researchers, traders, and risk managers – to research markets and propose risk-aware trading decisions. The project combines LangGraph, FastAPI, and a Next.js Control Center with vendor integrations for market, fundamental, and news data.

> **Disclaimer**: TradingAgents is released for research purposes only. It is not financial, investment, or trading advice. Real-world performance depends on model choice, data quality, configuration, and market conditions. See the full [disclaimer](https://tauric.ai/disclaimer/).

## 📚 Documentation

**主文档**: [DOCUMENTATION.md](DOCUMENTATION.md) - 完整的项目文档，包含功能说明、快速开始、技术架构、开发指南和待办事项

### 核心文档

| 文档 | 说明 |
| --- | --- |
| [SETUP](docs/SETUP.md) | 安装依赖、环境配置、本地运行指南 |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | 多智能体工作流、项目结构、子系统设计 |
| [API](docs/API.md) | REST、SSE、WebSocket 和管理端点文档 |
| [CONFIGURATION](docs/CONFIGURATION.md) | 环境变量、数据源路由、Agent 配置 |
| [DEPLOYMENT](docs/DEPLOYMENT.md) | Docker 部署、生产环境配置、扩展策略 |
| [DEVELOPMENT](docs/DEVELOPMENT.md) | 开发规范、测试策略、贡献流程 |

### 技术专题

| 文档 | 说明 |
| --- | --- |
| [DATABASE PERFORMANCE TUNING](docs/DATABASE_PERFORMANCE_TUNING.md) | 连接池、查询优化、索引、读副本支持 |
| [QUICK FIXES](docs/QUICK_FIXES.md) | 常见问题快速修复指南 |

更多运维指南（如 Kubernetes 配置）请查看 [`docs/operations/`](docs/operations/README.md)。

## 🔍 What You Get

- **Multi-agent trading workflow** built on LangGraph with specialized analyst, researcher, trader, and risk-management roles.
- **Extensible plugin ecosystems** for both data vendors and agents, including hot-reloadable routing and registry APIs.
- **FastAPI backend** with SSE/WebSocket streaming, persistence, monitoring endpoints, and optional workers.
- **Production-optimized performance** with response compression, connection pooling, intelligent caching, and code splitting.
- **Optimized database layer** with connection pooling, query performance monitoring, and read replica support for scaling.
- **Next.js Control Center** with advanced bundle optimization, lazy loading, and caching strategies.
- **ChromaDB-backed memory** and reflection loops for iterative research and trading decisions.

## ⚡ Quick Start

```bash
# Clone the repository
git clone https://github.com/TauricResearch/TradingAgents.git
cd TradingAgents

# Sync workspace dependencies (runs uv inside packages/backend)
pnpm sync

# Configure environment variables
cp .env.example .env
# Populate API keys such as OPENAI_API_KEY and ALPHA_VANTAGE_API_KEY

# Launch the interactive CLI
pnpm cli
```

For detailed installation steps, Python environment setup, and frontend instructions, see [docs/SETUP.md](docs/SETUP.md).

## 🧠 Architecture Snapshot

TradingAgents breaks research and execution into focused stages:

- **Analyst team** – Fundamentals, sentiment, news, and technical analysts synthesize diverse signals.
- **Research panel** – Bullish and bearish researchers debate proposals to expose blind spots.
- **Trader agent** – Summarizes evidence and proposes trades.
- **Risk & portfolio management** – Validates exposure, sizing, and compliance before execution.

<p align="center">
  <img src="assets/schema.png" style="width: 100%; height: auto;" alt="Workflow diagram">
</p>

The repository is organised as a PNPM workspace:

```text
.
├── packages
│   ├── backend/     # LangGraph workflow, FastAPI services, persistence, plugins
│   ├── frontend/    # Next.js Control Center UI
│   └── shared/      # OpenAPI clients, typings, and UI tokens
├── docs/            # Centralised documentation
└── scripts/         # Deployment and healthcheck tooling
```

An in-depth view of subsystems (plugins, streaming, execution, monitoring, UI) is available in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## 🛠️ Running Services

- **CLI**: `pnpm cli` (delegates to `uv run python -m cli.main`).
- **FastAPI backend**: `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` from `packages/backend`.
- **Frontend Control Center**: `pnpm --filter @tradingagents/frontend dev` for live previews.

The backend exposes REST endpoints (`/sessions`, `/vendors`, `/monitoring`), SSE streams, and WebSockets. Explore usage examples and request payloads in [docs/API.md](docs/API.md).

## 🚢 Deploying TradingAgents

Docker Compose stacks covering PostgreSQL, Redis, backend, workers, frontend, and nginx live in the repository. Start with:

```bash
cp .env.docker .env
PROFILE=frontend,workers ./scripts/deploy.sh up
```

Production checklists, scaling strategies, SSL guidance, monitoring hooks, and backup workflows are consolidated in [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## 🤝 Contributing

We welcome issues, ideas, and pull requests! Review our development workflow, testing strategy, and style expectations in [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md).

Join the community:
- Discord: [https://discord.com/invite/hk9PGKShPK](https://discord.com/invite/hk9PGKShPK)
- GitHub: [https://github.com/TauricResearch](https://github.com/TauricResearch)
- X: [@TauricResearch](https://x.com/TauricResearch)

## 📄 Citation

If TradingAgents supports your research, please cite:

```
@misc{xiao2025tradingagentsmultiagentsllmfinancial,
      title={TradingAgents: Multi-Agents LLM Financial Trading Framework},
      author={Yijia Xiao and Edward Sun and Di Luo and Wei Wang},
      year={2025},
      eprint={2412.20138},
      archivePrefix={arXiv},
      primaryClass={q-fin.TR},
      url={https://arxiv.org/abs/2412.20138},
}
```
