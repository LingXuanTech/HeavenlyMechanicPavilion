# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

**Stock Agents Monitor（天机阁）** — 基于 TradingAgents 框架的金融情报监控系统。通过多 Agent 协作（Bull vs Bear 对抗性辩论）对 A股/港股/美股 进行深度分析，以实时大屏形式提供决策支持。

基于论文 [TradingAgents: Multi-Agents LLM Financial Trading Framework (arXiv:2412.20138)](https://arxiv.org/abs/2412.20138)。

## 开发命令

### Moon（推荐）
```bash
moon run :install                   # 安装所有依赖（前端+后端）
moon run server:dev                 # 启动后端开发服务器
moon run client:dev                 # 启动前端开发服务器
moon run :typecheck                 # 全栈类型检查
moon run :lint                      # 全栈 lint
moon run :test                      # 全栈测试
moon run :format                    # 全栈格式化
```

### 前端 (apps/client)
```bash
cd apps/client
npm install                         # 安装依赖
npm run dev                         # 启动开发服务器 (http://localhost:3000)
npm run build                       # 生产构建
npx tsc --noEmit                    # TypeScript 类型检查
npm run gen:types                   # 从后端 OpenAPI schema 生成前端类型（需后端运行中）
npm run gen:types:check             # 仅检查类型是否过期（CI 用）
npm run lint                        # ESLint 检查
npm run lint:fix                    # ESLint 自动修复
npm run format                      # Prettier 格式化
```

### 后端 (apps/server)
```bash
cd apps/server
uv sync                             # 安装依赖
uv sync --group dev                 # 安装开发依赖（测试、lint）
python main.py                      # 启动 FastAPI (http://localhost:8000)，内置热重载
python -m cli.main                  # CLI 交互式分析

# 任务队列 Worker（生产环境，需 Redis）
python -m workers.analysis_worker --name worker-1

# 测试（分层：tests/unit/ + tests/integration/，fixtures 在 tests/fixtures/）
pytest                              # 运行所有测试
pytest tests/unit/test_xxx.py -v    # 运行单个单元测试
pytest tests/integration/ -v        # 运行集成测试
pytest --cov=. --cov-report=html    # 覆盖率报告

# 代码质量
ruff check .                        # Lint 检查
ruff check . --fix                  # 自动修复
mypy api/ services/ config/ db/     # 类型检查

# 数据库迁移 (Alembic)
alembic revision --autogenerate -m "description"  # 生成迁移脚本
alembic upgrade head                              # 应用迁移
alembic downgrade -1                              # 回滚一个版本
```

### Docker 全栈
```bash
docker compose up                                     # backend + frontend
docker compose --profile postgresql up                # + PostgreSQL
docker compose --profile postgresql --profile cache up # + PostgreSQL + Redis
```

## 代码架构

### Monorepo 结构（Moon + pnpm workspace，工具链：Node 20.18.0 + pnpm 9.15.0）
```
apps/
├── client/               # React 19 + Vite + TanStack Query + Tailwind CSS 4
│   ├── index.tsx         # React 根入口，路由配置，QueryClient 全局配置
│   ├── services/api.ts   # 统一 API 层（REST + SSE），ApiError 类，API_BASE 常量
│   ├── hooks/            # TanStack Query hooks（26 个功能域文件，index.ts 统一导出）
│   ├── src/types/        # 类型定义中心
│   │   ├── schema.ts     # 类型消费入口（从 generated/ 导出辅助类型）
│   │   ├── frontend-types.ts  # 纯前端类型（后端无对应 schema：MarketStatus, FlashNews 等）
│   │   └── generated/    # OpenAPI 自动生成的类型（按模块拆分：market/analysis/trading/system）
│   ├── components/       # UI 组件（layout/ + auth/ + common/ 子目录）
│   ├── pages/            # 页面组件（懒加载，14 个路由页面）
│   └── contexts/         # React Context（AuthContext 等）
│
└── server/               # Python 3.10 + FastAPI
    ├── main.py           # 应用入口：路由注册、中间件栈、生命周期管理、Alembic 迁移
    ├── api/
    │   ├── routes/       # 4 个路由模块（见下方）
    │   ├── schemas/      # Pydantic 请求/响应 schema（10 个模块：analysis, ai_config, chat, health 等）
    │   ├── exceptions.py # 统一异常体系（AppException → 结构化 JSON 错误响应）
    │   ├── dependencies.py  # FastAPI 依赖注入（API Key 验证）
    │   ├── middleware.py    # RequestTracingMiddleware（request_id 追踪）
    │   └── sse.py        # SSE 事件流封装
    ├── services/         # 业务服务层（~41 个模块，含 notification_service, graph_executor, token_monitor 等）
    ├── workers/          # 后台任务 Worker（Redis Stream 消费者）
    ├── cli/              # CLI 交互式分析（main.py, models.py, utils.py）
    ├── config/
    │   ├── settings.py   # Pydantic Settings（环境变量驱动，sqlite/postgresql 双模式）
    │   ├── oauth.py      # OAuth 2.0 配置
    │   └── prompts.yaml  # Agent Prompt 注册表（支持热更新，变量注入 {symbol}/{data}）
    ├── db/
    │   └── models.py     # SQLModel ORM
    ├── alembic/          # 数据库迁移脚本（3 个版本：initial_schema → north_money → user_id）
    └── tradingagents/    # 核心 AI Agent 框架（fork 自 TauricResearch/TradingAgents）
        ├── graph/        # LangGraph StateGraph 编排
        │   ├── trading_graph.py   # 主图定义
        │   ├── subgraphs/         # 模块化 SubGraph（Analyst/Debate/Risk）
        │   ├── reflection.py      # 反思机制
        │   ├── conditional_logic.py # 条件路由
        │   ├── signal_processing.py # 信号处理
        │   └── resilience.py      # 容错与重试
        ├── agents/       # Agent 实现
        │   ├── analysts/    # 12 个分析师（含 planner, sentiment, vision, supply_chain, scout 等）
        │   ├── researchers/ # 研究员
        │   ├── managers/    # 管理者
        │   ├── risk_mgmt/   # 风控
        │   ├── trader/      # 交易员
        │   └── utils/       # Agent 工具集（agent_states, output_schemas, china_market_tools 等 13 个模块）
        ├── dataflows/    # 数据源适配器（yfinance, akshare, alpha_vantage 等）
        └── default_config.py # Agent 默认配置（LLM 选择、分析级别、数据源）
```

### 后端路由模块化架构

路由在 `api/routes/` 下按业务域分为 4 个子包，每个子包有 `__init__.py` 聚合子路由并导出 `router`，在 `main.py` 中统一注册（前缀 `/api`）：

| 模块 | 子路由 | 职责 |
|------|--------|------|
| `market/` | 行情、龙虎榜、北向资金、解禁、跨资产、市场监控、替代数据 | 市场数据 |
| `analysis/` | Agent 分析(SSE)、宏观、情绪、央行NLP、政策、反思、模型竞赛、视觉、供应链 | 分析决策 |
| `trading/` | 自选股、组合、发现、对话、记忆、新闻、新闻聚合、回测、风控 | 交易执行 |
| `system/` | 认证(JWT/OAuth/Passkey)、AI配置、Prompt管理、通知、健康、管理、设置、TTS、SubGraph指标 | 系统服务 |

### 核心数据流

```
前端点击分析 → POST /api/analyze/{symbol} → 返回 task_id
    ↓
任务入队: BackgroundTask (dev) / Redis Stream (prod)
    ↓
TradingAgentsGraph (LangGraph StateGraph)
    ↓
  ┌─ Planner Agent (可选) → 自适应选择分析师
  ├─ memory_service.generate_reflection() → 注入历史反思
  ├─ Analyst SubGraph → SSE: stage_analyst
  ├─ Bull vs Bear Debate → SSE: stage_debate
  ├─ Risk 三方辩论 → SSE: stage_risk
  ├─ Trader/Portfolio 决策 → SSE: stage_final
  └─ ResponseSynthesizer → Markdown 报告合成为结构化 JSON
    ↓
SSE 实时推送 → GET /api/analyze/stream/{task_id}
    ↓
前端 useStreamingAnalysis() hook → 更新 TanStack Query 缓存
    ↓
分析完成触发 → notification_service.notify_analysis_complete()
    ↓
根据用户配置推送通知 → Telegram/企业微信/钉钉
```

### 分析分级 (L1/L2)

- **L1 Quick** (`POST /api/analyze/quick/{symbol}`)：Market + News + Macro，无辩论，15-20s，适合批量扫描
- **L2 Full** (`POST /api/analyze/{symbol}`)：全部分析师 + Planner 自适应 + 完整辩论，30-60s，深度研究

### 智能数据路由 (MarketRouter)

`services/data_router.py` 根据 symbol 后缀自动选择数据源，支持降级链和 60s 价格缓存：
- `.SH/.SZ` → A股 → AkShare → yfinance（降级）
- `.HK` → 港股 → yfinance → AkShare（降级）
- 其他 → 美股 → yfinance → Alpha Vantage（降级）

## 前后端类型合约

**类型生成流程**：后端 FastAPI OpenAPI schema → `npm run gen:types` → `src/types/generated/`（按 market/analysis/trading/system 模块拆分）→ `src/types/schema.ts` 统一导出辅助类型（`ApiResponse<Path>`, `ApiRequestParams<Path>`, `ApiRequestBody<Path>`）。类型生成脚本使用 `tsx` 运行（`scripts/generate-types.ts`）。

**关键约束**：`services/synthesizer.py` 的 `ResponseSynthesizer` 将 Agent Markdown 报告通过 LLM 合成为结构化 JSON。修改后端响应模型时，需重新生成前端类型：`npm run gen:types`。

核心信号类型：`STRONG_BUY | BUY | HOLD | SELL | STRONG_SELL`

## 关键架构模式

### 前端
- **状态管理**：TanStack Query 管理所有服务器状态（staleTime: 5min, gcTime: 30min, retry: 2, refetchOnWindowFocus: false）
- **Hooks 层**：每个功能域一个 hook 文件，通过 `hooks/index.ts` 统一导出，每个 hook 导出查询 key 常量
- **路由**：React Router v7，公开路由（/login, /register）+ ProtectedRoute 包裹的 MainLayout 内嵌路由
- **路径别名**：`@/` 映射到 `apps/client/` 根目录
- **SSE 消费**：`useStreamingAnalysis` hook 通过 EventSource 监听分析进度
- **构建优化**：Vite manualChunks 分包（vendor-react, vendor-charts, vendor-motion, vendor-query）

### 后端
- **中间件栈**（顺序重要）：RequestTracingMiddleware → SessionMiddleware → CORSMiddleware
- **依赖注入**：`api/dependencies.py` 提供 `verify_api_key` / `optional_api_key`
- **Prompt 管理**：`PromptManager` 单例 + YAML 热加载（`config/prompts.yaml`）
- **日志**：`structlog`（JSON 格式 + ISO 时间戳 + request_id 追踪）
- **数据库**：SQLModel ORM，`get_session()` 依赖注入；启动时优先 Alembic 迁移，失败回退 `init_db()`
- **异常处理**：`AppException(code, message, status_code)` → `{"error": {"code": ..., "message": ..., "details": ...}}`
- **灰度发布**：`rollout_manager.py` + `subgraph_metrics_service.py` 支持 SubGraph A/B 测试

### LLM 配置
`tradingagents/default_config.py`：
- `llm_provider`: `openai` | `anthropic` | `google`
- `deep_think_llm`: 深度推理（默认 `o4-mini`）
- `quick_think_llm`: 快速响应（默认 `gpt-4o-mini`）
- 支持通过 UI（`/api/ai/providers`）动态配置，API 密钥 Fernet 加密存储

## 代码规范

### Python
- **Ruff**: line-length 120, target Python 3.10, rules: `E, F, W, I, N, UP, B, C4, SIM, TID, RUF`（忽略 E501）
- **mypy**: strict_optional, check_untyped_defs, warn_return_any, warn_unused_ignores（注意：`disallow_untyped_defs = false`）；排除 `tests/` 和 `cli/`
- **pytest**: asyncio_mode="auto", testpaths=["tests"], addopts="-v --tb=short"
- **coverage**: source=["api", "services", "db", "tradingagents"]

### TypeScript
- **严格模式**: `strict: true`, `noImplicitAny`, `strictNullChecks`, `noUnusedLocals`, `noUnusedParameters`, `noImplicitReturns`, `strictFunctionTypes`, target ES2022
- **ESLint**: flat config (`eslint.config.js`) — typescript-eslint + react-hooks + react-refresh + prettier
- **Prettier**: semi, singleQuote, trailingComma: all, printWidth: 100

### 通用
- **EditorConfig**: UTF-8, LF, space indent（JS/TS: 2, Python: 4）
- **提交规范**: Conventional Commits — `feat(<scope>): <description>`

## 环境变量

后端 `.env` 放在 `apps/server/`（参考 `apps/server/.env.example`），Docker 用根目录 `.env`（参考 `.env.example`），前端 `.env.local` 放在 `apps/client/`。完整变量列表参见 `docs/CONTRIB.md`。

最小启动配置：
- 后端：至少一个 LLM API Key（`OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GOOGLE_API_KEY`）
- 前端：`VITE_API_URL=http://localhost:8000/api`（默认值，可省略）

主要环境变量分类：JWT/OAuth/WebAuthn 认证、LLM API Keys、数据源 Keys（FRED/Finnhub）、LangSmith 追踪、推送通知（Telegram）、灰度发布、定时分析调度。

## 文档

- `docs/ARCH.md` — 系统架构设计（Mermaid 图、API 规范、数据源映射表）
- `docs/PRD.md` — 产品需求文档
- `docs/CONTRIB.md` — 贡献指南（环境变量完整列表、AI 配置系统 API）
- `docs/RUNBOOK.md` — 运维手册（部署、监控、故障排查）
