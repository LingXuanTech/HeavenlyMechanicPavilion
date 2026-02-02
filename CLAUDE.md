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
npx tsc --noEmit      # TypeScript 类型检查
```

### 后端 (apps/server)
```bash
cd apps/server
uv sync                             # 安装依赖（推荐，或 pip install -r requirements.txt）
uv sync --group dev                 # 安装开发依赖（测试、lint）
python main.py                      # 启动 FastAPI (http://localhost:8000)，内置热重载
uvicorn main:app --reload           # 备选热重载方式
python -m cli.main                  # CLI 交互式分析

# 任务队列 Worker（生产环境）
python -m workers.analysis_worker --name worker-1  # 启动分析 Worker

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
│   ├── index.tsx         # React 根入口，路由配置
│   ├── types.ts          # 完整 TypeScript 类型定义（AgentAnalysis 为核心合约）
│   ├── services/api.ts   # 统一 API 层（REST + SSE）
│   ├── hooks/            # TanStack Query hooks（按功能域拆分，index.ts 统一导出）
│   ├── components/       # UI 组件（33 个）
│   └── pages/            # 页面组件（12 个）
│
└── server/               # Python 3.10 + FastAPI
    ├── main.py           # 应用入口，路由注册，生命周期管理
    ├── api/
    │   ├── routes/       # 业务路由（31 个路由模块）
    │   ├── dependencies.py  # FastAPI 依赖注入（API Key 验证）
    │   ├── middleware.py    # 请求追踪中间件
    │   └── sse.py        # SSE 事件流封装
    ├── services/         # 业务服务层（34 个服务模块）
    ├── workers/          # 后台任务 Worker
    │   └── analysis_worker.py  # 分析任务 Worker（Redis Stream 消费者）
    ├── config/
    │   ├── settings.py   # Pydantic Settings（环境变量驱动）
    │   ├── oauth.py      # OAuth 2.0 配置
    │   └── prompts.yaml  # Agent Prompt 注册表（支持热更新）
    ├── db/
    │   └── models.py     # SQLModel ORM（Watchlist, AnalysisResult, ChatHistory 等）
    └── tradingagents/    # 核心 AI Agent 框架（fork 自 TauricResearch/TradingAgents）
        ├── graph/        # LangGraph StateGraph 编排
        │   └── subgraphs/  # 模块化 SubGraph（Analyst/Debate/Risk）
        ├── agents/       # Agent 实现（详见下方 Agent 清单）
        ├── dataflows/    # 数据源适配器（yfinance, akshare, alpha_vantage 等）
        └── default_config.py # Agent 默认配置
```

### 路由清单 (`api/routes/`) — 31 个

| 路由 | 功能 |
|------|------|
| `analyze` | Agent 分析触发 + SSE 流（支持 L1/L2 分级） |
| `watchlist` | 自选股 CRUD |
| `market` | 实时行情 |
| `discover` | Scout 股票发现 |
| `chat` | Fund Manager 对话 |
| `portfolio` | 组合分析 |
| `macro` | 宏观经济数据 |
| `memory` | 向量记忆管理 |
| `reflection` | 决策反思 |
| `ai_config` | 动态 AI 提供商配置 |
| `auth` | JWT 认证 |
| `oauth` | OAuth 2.0（Google/GitHub） |
| `passkey` | WebAuthn 免密认证 |
| `lhb` | 龙虎榜（A 股） |
| `north_money` | 北向资金（A 股） |
| `jiejin` | 限售解禁（A 股） |
| `unlock` | 解禁管理（A 股） |
| `central_bank` | 央行 NLP 分析 |
| `cross_asset` | 跨资产联动分析 |
| `policy` | 政策-行业板块映射 |
| `sentiment` | 情绪分析 |
| `news` | 新闻路由 |
| `news_aggregator` | 新闻聚合服务 |
| `backtest` | 回测服务 |
| `model_racing` | 模型竞赛评估 |
| `tts` | 语音合成 |
| `prompts` | Prompt 管理 |
| `settings` | 系统设置 |
| `market_watcher` | 全球指数监控 |
| `health` | 系统健康 + 指标 |
| `admin` | 管理接口（需 API Key） |

### 服务清单 (`services/`) — 34 个

| 服务 | 功能 |
|------|------|
| `data_router` | MarketRouter：多市场数据路由 + 降级 |
| `data_validator` | DataValidator：跨数据源校验与质量标记 |
| `synthesizer` | ResponseSynthesizer：Agent 报告 -> JSON |
| `prompt_manager` | PromptManager（单例，YAML 热加载） |
| `prompt_config_service` | Prompt 版本管理 |
| `prompt_optimizer` | Prompt 自动优化 |
| `scheduler` | APScheduler 定时分析 |
| `task_queue` | Redis Stream 任务队列 |
| `memory_service` | ChromaDB 向量记忆 + 分层检索 + 反思机制 |
| `ai_config_service` | 动态 AI 提供商管理 |
| `auth_service` | 认证服务（JWT/OAuth/Passkey） |
| `macro_service` | 宏观经济数据 |
| `market_watcher` | 全球指数监控 |
| `market_analyst_router` | 市场分析路由 |
| `news_aggregator` | 新闻聚合 |
| `sentiment_aggregator` | 情绪聚合 |
| `health_monitor` | 系统健康监控 |
| `api_metrics` | API 性能指标 |
| `accuracy_tracker` | 预测准确率追踪 |
| `lhb_service` | 龙虎榜服务 |
| `north_money_service` | 北向资金服务 |
| `jiejin_service` | 限售解禁服务 |
| `unlock_service` | 解禁管理服务 |
| `central_bank_nlp_service` | 央行文本 NLP 分析 |
| `cross_asset_service` | 跨资产相关性分析 |
| `policy_sector_service` | 政策-行业映射服务 |
| `backtest_service` | 回测服务 |
| `model_racing` | 模型竞赛 |
| `tts_service` | TTS 语音合成 |
| `langsmith_service` | LangSmith 追踪 |
| `token_monitor` | Token 使用监控 |
| `cache_service` | 缓存服务（Redis/内存） |

### Agent 清单 (`tradingagents/agents/`)

| 分类 | Agents |
|------|--------|
| `analysts/` | market, fundamentals, news, social, macro, scout, portfolio, sentiment, policy, fund_flow, **planner** |
| `researchers/` | bull_researcher, bear_researcher |
| `managers/` | research_manager, risk_manager |
| `risk_mgmt/` | aggressive_debator, conservative_debator, neutral_debator |
| `trader/` | trader |

### 核心数据流

```
前端点击分析 → POST /api/analyze/{symbol} → 返回 task_id
    ↓
任务入队: BackgroundTask (dev) / Redis Stream (prod)
    ↓
Worker/Task: run_analysis_task()
    ↓
TradingAgentsGraph (LangGraph StateGraph)
    ↓
  ┌─ Planner Agent (可选) → 自适应选择分析师
  ├─ memory_service.generate_reflection() → 注入历史反思
  ├─ Analyst SubGraph (market/fundamentals/news/social/macro)
  │     → SSE event: stage_analyst
  ├─ Bull vs Bear Debate SubGraph
  │     → SSE event: stage_debate
  ├─ Risk SubGraph 三方风险辩论（aggressive/conservative/neutral）
  │     → SSE event: stage_risk
  ├─ Trader/Portfolio Agent 决策
  │     → SSE event: stage_final
  └─ ResponseSynthesizer 将 Markdown 报告合成为 AgentAnalysis JSON
    ↓
SSE 实时推送 → GET /api/analyze/stream/{task_id}
    ↓
前端 useStreamingAnalysis() hook 消费 SSE → 更新 TanStack Query 缓存
```

### 分析分级 (L1/L2)

| 级别 | 分析师 | 辩论 | 耗时 | 场景 |
|------|--------|------|------|------|
| **L1 Quick** | Market + News + Macro | ❌ 无 | 15-20s | Watchlist 批量扫描 |
| **L2 Full** | 全部 + Planner 自适应 | ✅ 完整 | 30-60s | 深度研究 |

```bash
# L1 快速扫描
POST /api/analyze/quick/{symbol}

# L2 完整分析（默认）
POST /api/analyze/{symbol}
```

### 智能数据路由 (MarketRouter)

MarketRouter 根据 symbol 后缀自动选择数据源，支持降级和缓存：
```
.SH / .SZ → CN (A股) → AkShare → yfinance（降级）
.HK → HK (港股) → yfinance → AkShare（降级）
其他 → US (美股) → yfinance → Alpha Vantage（降级）
```
价格缓存 TTL 60 秒，所有数据源失败时返回过期缓存。

### SubGraph 架构（实验性）

```
MainGraph
  ├─ Planner Node (自适应选择分析师)
  ├─ AnalystSubGraph (并行执行分析师)
  ├─ Trader Node
  ├─ DebateSubGraph (Bull vs Bear 辩论)
  ├─ RiskSubGraph (三方风险辩论)
  └─ Portfolio Agent
```

通过 `use_subgraphs=True` 启用（默认关闭）。

### 前端架构模式

- **状态管理**：TanStack Query 管理所有服务器状态，QueryClient 全局配置在 `index.tsx`（staleTime: 1min, gcTime: 10min）
- **Hooks 层**：每个功能域一个 hook 文件，通过 `hooks/index.ts` 统一导出，每个 hook 导出查询 key 常量
- **API 层**：`services/api.ts` 集中所有后端调用，统一错误处理（`ApiError` 类），导出 `API_BASE` 常量
- **SSE 消费**：`useStreamingAnalysis` hook 触发分析后通过 EventSource 监听进度
- **路径别名**：`@/` 映射到 `apps/client/` 根目录

### 后端架构模式

- **路由注册**：所有路由在 `main.py` 中显式注册，统一前缀 `/api`
- **中间件**：RequestTracingMiddleware（请求追踪）、SessionMiddleware（OAuth 状态）、CORSMiddleware
- **依赖注入**：`api/dependencies.py` 提供 API Key 验证（`verify_api_key`, `optional_api_key`）
- **配置管理**：`config/settings.py` 使用 Pydantic Settings，支持 sqlite/postgresql 双模式
- **Prompt 管理**：`PromptManager` 单例 + YAML 热加载，支持 `{symbol}`, `{data}` 等变量注入
- **日志**：全局使用 `structlog`（JSON 格式 + ISO 时间戳 + request_id 追踪）
- **数据库**：SQLModel ORM，`get_session()` 提供 FastAPI 依赖注入
- **生命周期**：startup 初始化数据库和调度器，shutdown 关闭缓存/队列/HTTP 客户端

### LLM 配置

`tradingagents/default_config.py` 控制 Agent 使用的 LLM：
- **llm_provider**: `openai` | `anthropic` | `google`
- **deep_think_llm**: 深度推理模型（默认 `o4-mini`）
- **quick_think_llm**: 快速响应模型（默认 `gpt-4o-mini`）
- **use_planner**: 启用 Planner 自适应分析师选择
- **analysis_level**: `L1` | `L2`
- **use_subgraphs**: 启用 SubGraph 架构（实验性）
- **data_vendors**: 按数据类别配置数据源

### 动态 AI 配置系统

支持通过 UI 界面（侧边栏 → AI Config）动态配置 AI 提供商，无需重启服务：
- **支持类型**: `openai` | `openai_compatible` (NewAPI/OneAPI) | `google` | `anthropic` | `deepseek`
- **模型分配场景**: `deep_think`（复杂推理）| `quick_think`（快速任务）| `synthesis`（报告合成）
- **API 端点**: `/api/ai/providers`（CRUD）、`/api/ai/models`（模型配置）、`/api/ai/status`（状态检查）
- **安全**: API 密钥使用 Fernet 加密存储

### 认证系统

支持三种认证方式：
1. **JWT**: 用户名/密码登录，签发 Access + Refresh Token
2. **OAuth 2.0**: Google、GitHub 第三方登录
3. **WebAuthn/Passkey**: 免密生物识别认证

## 前后端 JSON 合约

前端 `types.ts` 中的 `AgentAnalysis` 接口是核心数据合约（801 行类型定义）。后端 `synthesizer.py` 的 `ResponseSynthesizer` 负责将 Agent 的 Markdown 报告通过 LLM 合成为严格匹配此接口的 JSON。修改 `AgentAnalysis` 时必须同步更新 synthesizer 的 prompt。

核心类型：
- `SignalType`: STRONG_BUY | BUY | HOLD | SELL | STRONG_SELL
- `AgentAnalysis`: 分析结果完整结构
- `TradeSetup`: 交易设置（入场/止盈/止损）
- `RiskAssessment`: 风险评估
- `MacroContext`: 宏观环境

## 环境变量

### 前端 (apps/client/.env.local)
```
VITE_API_URL=http://localhost:8000/api
GEMINI_API_KEY=your_key
```

### 后端 (apps/server/.env)
```bash
# LLM API Keys（至少配置一个）
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...

# 数据源
ALPHA_VANTAGE_API_KEY=...
FRED_API_KEY=...
FINNHUB_API_KEY=...

# 数据库
DATABASE_MODE=sqlite              # sqlite | postgresql
DATABASE_URL=sqlite:///./db/trading.db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=...
POSTGRES_DB=trading

# 向量数据库
CHROMA_DB_PATH=./db/chroma

# 缓存（生产推荐）
REDIS_URL=redis://localhost:6379

# 任务队列（生产环境）
USE_TASK_QUEUE=false              # 启用后使用 Redis Stream

# 安全
API_KEY=your_admin_key
API_KEY_ENABLED=false             # 启用后 admin 路由需要 X-API-Key 头
CORS_ORIGINS=http://localhost:3000

# JWT 认证
JWT_SECRET_KEY=your_jwt_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# OAuth 2.0
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...

# WebAuthn
WEBAUTHN_RP_ID=localhost
WEBAUTHN_RP_NAME=Stock Agents Monitor
WEBAUTHN_ORIGIN=http://localhost:3000

# 定时任务
DAILY_ANALYSIS_ENABLED=false
DAILY_ANALYSIS_HOUR=9
DAILY_ANALYSIS_MINUTE=30

# Scout Agent
DUCKDUCKGO_ENABLED=true
DUCKDUCKGO_TIMEOUT=10
SCOUT_SEARCH_LIMIT=10
SCOUT_ENABLE_VALIDATION=true

# LangSmith 追踪（可选）
LANGSMITH_ENABLED=false
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=stock-agents
LANGSMITH_TRACE_SAMPLING_RATE=1.0

# AI 配置加密（自动生成）
AI_CONFIG_ENCRYPTION_KEY=...
```

## 代码规范

### Python (后端)
- **Ruff**: line-length 120, target Python 3.10, lint rules: `E, F, W, I, N, UP, B, C4`（忽略 E501）
- **mypy**: strict_optional, check_untyped_defs, show_error_codes
- **pytest**: asyncio_mode="auto", testpaths=["tests"]

### TypeScript (前端)
- **严格模式**: `strict: true`, `noImplicitAny: true`, `strictNullChecks: true`
- 使用 `npx tsc --noEmit` 做类型检查

### 提交规范
使用 [Conventional Commits](https://www.conventionalcommits.org/)：`feat(<scope>): <description>`

## 文档

- `docs/ARCH.md` — 系统架构设计（含 Mermaid 图、API 规范、数据源映射表）
- `docs/PRD.md` — 产品需求文档
- `docs/CONTRIB.md` — 贡献指南（环境变量完整列表、AI 配置系统 API）
- `docs/RUNBOOK.md` — 运维手册（部署、监控、故障排查）
- `IMPLEMENTATION_SUMMARY.md` — 最近实施总结
