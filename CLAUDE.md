# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

**Stock Agents Monitor** — 基于 TradingAgents 框架的金融情报监控系统。通过多 Agent 协作（Bull vs Bear 对抗性辩论）对 A股/港股/美股 进行深度分析，以实时大屏形式提供决策支持。

基于论文 [TradingAgents: Multi-Agents LLM Financial Trading Framework (arXiv:2412.20138)](https://arxiv.org/abs/2412.20138)。

## 开发命令

### 前端 (apps/client)
```bash
cd apps/client
npm install           # 安装依赖
npm run dev           # 启动开发服务器 (http://localhost:3000)
npm run build         # 生产构建
npm run preview       # 预览构建结果
```

### 后端 (apps/server)
```bash
cd apps/server
uv sync                             # 安装依赖（推荐，或 pip install -r requirements.txt）
uv sync --group dev                 # 安装开发依赖（测试、lint）
python main.py                      # 启动 FastAPI (http://localhost:8000)，内置热重载
uvicorn main:app --reload           # 备选热重载方式
python -m cli.main                  # CLI 交互式分析

# 测试
pytest                              # 运行所有测试
pytest tests/test_xxx.py -v         # 运行单个测试
pytest --cov=. --cov-report=html    # 生成覆盖率报告

# 代码质量
ruff check .                        # Lint 检查
ruff check . --fix                  # 自动修复 lint 问题
mypy api/ services/ config/ db/     # 类型检查
```

### Docker 全栈
```bash
docker compose up                                     # 启动 backend + frontend
docker compose --profile postgresql up                # 附加 PostgreSQL
docker compose --profile postgresql --profile cache up # 附加 PostgreSQL + Redis
```

## 代码架构

### Monorepo 结构（Moon 管理）
```
apps/
├── client/               # React 19 + Vite + TanStack Query + Tailwind CSS
│   ├── App.tsx           # 主组件，聚合所有 hooks 和 UI 状态
│   ├── types.ts          # 完整 TypeScript 类型定义（AgentAnalysis 为核心合约）
│   ├── services/api.ts   # 统一 API 层（REST + SSE）
│   ├── hooks/            # TanStack Query hooks（按功能域拆分，index.ts 统一导出）
│   └── components/       # UI 组件（StockCard, StockDetailModal, Sidebar 等）
│
└── server/               # Python 3.10 + FastAPI
    ├── main.py           # 应用入口，路由注册，生命周期管理
    ├── api/
    │   ├── routes/       # 业务路由（analyze, watchlist, market, discover, chat, portfolio, macro, memory, admin, health, market_watcher, news_aggregator, settings）
    │   ├── dependencies.py  # FastAPI 依赖注入（API Key 验证）
    │   └── sse.py        # SSE 事件流封装
    ├── services/         # 业务服务层
    │   ├── data_router.py     # MarketRouter：多市场数据路由 + 降级
    │   ├── synthesizer.py     # ResponseSynthesizer：Agent 报告 -> JSON
    │   ├── prompt_manager.py  # PromptManager（单例，YAML 热加载）
    │   ├── scheduler.py       # APScheduler 定时分析
    │   ├── memory_service.py  # ChromaDB 向量记忆 + 反思机制
    │   ├── macro_service.py   # 宏观经济数据
    │   ├── market_watcher.py  # 全球指数监控
    │   ├── news_aggregator.py # 新闻聚合
    │   └── health_monitor.py  # 系统健康监控
    ├── config/
    │   ├── settings.py   # Pydantic Settings（环境变量驱动）
    │   └── prompts.yaml  # Agent Prompt 注册表（支持热更新）
    ├── db/
    │   └── models.py     # SQLModel ORM（Watchlist, AnalysisResult, ChatHistory）
    └── tradingagents/    # 核心 AI Agent 框架（fork 自 TauricResearch/TradingAgents）
        ├── graph/
        │   ├── trading_graph.py  # TradingAgentsGraph 主类（LLM 初始化 + 编排）
        │   ├── setup.py          # LangGraph StateGraph 构建
        │   ├── propagation.py    # 初始状态 + 图执行参数
        │   ├── reflection.py     # 决策反思 + 记忆更新
        │   ├── signal_processing.py  # 交易信号提取
        │   └── conditional_logic.py  # 节点跳转逻辑
        ├── agents/
        │   ├── analysts/     # 分析师：market, fundamentals, news, social, macro, scout, portfolio
        │   ├── researchers/  # 研究员：bull_researcher, bear_researcher
        │   ├── managers/     # 管理层：research_manager, risk_manager
        │   ├── risk_mgmt/    # 风险辩论：aggressive, conservative, neutral debator
        │   ├── trader/       # 交易员
        │   └── utils/        # Agent 工具函数 + 状态定义
        ├── dataflows/        # 数据源适配器（yfinance, akshare, alpha_vantage, google news 等）
        └── default_config.py # Agent 默认配置（LLM 模型、数据源、辩论轮数）
```

### 核心数据流

```
前端点击分析 → POST /api/analyze/{symbol} → 返回 task_id
    ↓
BackgroundTask: run_analysis_task()
    ↓
TradingAgentsGraph (LangGraph StateGraph)
    ↓
  ┌─ memory_service.generate_reflection() → 注入历史反思
  ├─ Analyst Team (market/fundamentals/news/social/macro)
  │     → SSE event: stage_analyst
  ├─ Bull vs Bear Researcher 对抗辩论
  │     → SSE event: stage_debate
  ├─ Risk Manager 三方风险辩论（aggressive/conservative/neutral）
  │     → SSE event: stage_risk
  ├─ Trader/Portfolio Agent 决策
  │     → SSE event: stage_final
  └─ ResponseSynthesizer 将 Markdown 报告合成为 AgentAnalysis JSON
    ↓
SSE 实时推送 → GET /api/analyze/stream/{task_id}
    ↓
前端 useStockAnalysis() hook 消费 SSE → 更新 TanStack Query 缓存
```

### 智能数据路由 (MarketRouter)

MarketRouter 根据 symbol 后缀自动选择数据源，支持降级和缓存：
```
.SH / .SZ → CN (A股) → AkShare → yfinance（降级）
.HK → HK (港股) → yfinance → AkShare（降级）
其他 → US (美股) → yfinance → Alpha Vantage（降级）
```
价格缓存 TTL 60 秒，所有数据源失败时返回过期缓存。

### 前端架构模式

- **状态管理**：TanStack Query 管理所有服务器状态，QueryClient 全局配置在 `index.tsx`（staleTime: 1min, gcTime: 10min）
- **Hooks 层**：每个功能域一个 hook 文件，通过 `hooks/index.ts` 统一导出，每个 hook 导出查询 key 常量（如 `WATCHLIST_KEY`）
- **API 层**：`services/api.ts` 集中所有后端调用，统一错误处理（`ApiError` 类）
- **SSE 消费**：`analyzeStockWithAgent()` 函数触发分析后通过 EventSource 监听进度
- **路径别名**：`@/` 映射到 `apps/client/` 根目录

### 后端架构模式

- **路由注册**：所有路由在 `main.py` 中显式注册，统一前缀 `/api`
- **依赖注入**：`api/dependencies.py` 提供 API Key 验证（`verify_api_key`, `optional_api_key`）
- **配置管理**：`config/settings.py` 使用 Pydantic Settings，支持 sqlite/postgresql 双模式
- **Prompt 管理**：`PromptManager` 单例 + YAML 热加载，支持 `{symbol}`, `{data}` 等变量注入
- **日志**：全局使用 `structlog`（JSON 格式 + ISO 时间戳）
- **数据库**：SQLModel ORM，`get_session()` 提供 FastAPI 依赖注入

### LLM 配置

`tradingagents/default_config.py` 控制 Agent 使用的 LLM：
- **llm_provider**: `openai` | `anthropic` | `google`
- **deep_think_llm**: 深度推理模型（默认 `o4-mini`）
- **quick_think_llm**: 快速响应模型（默认 `gpt-4o-mini`）
- **data_vendors**: 按数据类别配置数据源（`core_stock_apis`, `technical_indicators`, `fundamental_data`, `news_data`）

### 动态 AI 配置系统

支持通过 UI 界面（侧边栏 → AI Config）动态配置 AI 提供商，无需重启服务：
- **支持类型**: `openai` | `openai_compatible` (NewAPI/OneAPI) | `google` | `anthropic` | `deepseek`
- **模型分配场景**: `deep_think`（复杂推理）| `quick_think`（快速任务）| `synthesis`（报告合成）
- **API 端点**: `/api/ai/providers`（CRUD）、`/api/ai/models`（模型配置）、`/api/ai/status`（状态检查）
- **安全**: API 密钥使用 Fernet 加密存储

## 前后端 JSON 合约

前端 `types.ts` 中的 `AgentAnalysis` 接口是核心数据合约。后端 `synthesizer.py` 的 `ResponseSynthesizer` 负责将 Agent 的 Markdown 报告通过 LLM 合成为严格匹配此接口的 JSON。修改 `AgentAnalysis` 时必须同步更新 synthesizer 的 prompt。

## 环境变量

### 前端 (apps/client/.env.local)
```
VITE_API_URL=http://localhost:8000/api
GEMINI_API_KEY=your_key
```

### 后端 (apps/server/.env)
```
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...
ALPHA_VANTAGE_API_KEY=...
DATABASE_MODE=sqlite              # sqlite | postgresql
DATABASE_URL=sqlite:///./db/trading.db
CHROMA_DB_PATH=./db/chroma
API_KEY_ENABLED=false             # 启用后 admin 路由需要 X-API-Key 头
DAILY_ANALYSIS_ENABLED=false
```

## 代码规范

### Python (后端)
- **Ruff**: line-length 120, target Python 3.10, lint rules: `E, F, W, I, N, UP, B, C4`（忽略 E501）
- **mypy**: strict_optional, check_untyped_defs, show_error_codes
- **pytest**: asyncio_mode="auto", testpaths=["tests"], 当前 58 个测试（unit 29 + integration 29）

### TypeScript (前端)
- 前端无 lint/ESLint 配置，使用 `npx tsc --noEmit` 做类型检查

### 提交规范
使用 [Conventional Commits](https://www.conventionalcommits.org/)：`feat(<scope>): <description>`

## 文档

- `docs/ARCH.md` — 系统架构设计（含 Mermaid 图、API 规范、数据源映射表）
- `docs/PRD.md` — 产品需求文档
- `docs/CONTRIB.md` — 贡献指南（环境变量完整列表、AI 配置系统 API）
- `docs/RUNBOOK.md` — 运维手册（部署、监控、故障排查）
- `plans/implementation_plan.md` — 实现计划
