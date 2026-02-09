# Contributing Guide

> 最后更新: 2026-02-09

## 目录

1. [开发环境设置](#开发环境设置)
2. [项目脚本参考](#项目脚本参考)
3. [环境变量](#环境变量)
4. [AI 配置系统](#ai-配置系统)
5. [任务队列系统](#任务队列系统)
6. [通知系统配置](#通知系统配置)
7. [开发工作流](#开发工作流)
8. [测试流程](#测试流程)
9. [代码规范](#代码规范)
10. [目录结构](#目录结构)

---

## 开发环境设置

### 前端 (apps/client)

```bash
cd apps/client
npm install        # 安装依赖
npm run dev        # 启动开发服务器 http://localhost:3000
```

**依赖版本要求:**
- Node.js 20+
- npm 10+

### 后端 (apps/server)

```bash
cd apps/server

# 方式1: 使用 uv (推荐)
uv venv
source .venv/bin/activate
uv sync

# 方式2: 使用 pip
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 启动开发服务器
python main.py
# 或热重载模式
uvicorn main:app --reload
```

**依赖版本要求:**
- Python 3.10+
- uv 或 pip

---

## 项目脚本参考

### 前端脚本 (package.json)

| 脚本 | 命令 | 说明 |
|------|------|------|
| `dev` | `npm run dev` | 启动 Vite 开发服务器 (HMR) |
| `build` | `npm run build` | 生产环境构建 |
| `preview` | `npm run preview` | 预览生产构建结果 |

### 后端脚本

| 命令 | 说明 |
|------|------|
| `python main.py` | 启动 FastAPI 服务 (端口 8000) |
| `uvicorn main:app --reload` | 热重载开发模式 |
| `python -m cli.main` | CLI 交互式分析 |
| `python -m workers.analysis_worker --name worker-1` | 启动分析 Worker |
| `pytest tests/` | 运行所有测试 |
| `pytest tests/ -v --cov=.` | 运行测试并生成覆盖率报告 |
| `ruff check .` | 运行代码风格检查 |
| `ruff check . --fix` | 自动修复 lint 问题 |
| `mypy api/ services/` | 运行类型检查 |

---

## 环境变量

从 `.env.example` 复制到 `.env` 并配置：

```bash
cp .env.example .env
```

### LLM API Keys

| 变量 | 必需 | 说明 |
|------|------|------|
| `OPENAI_API_KEY` | 可选 | OpenAI API 密钥 (GPT-4o) |
| `ANTHROPIC_API_KEY` | 可选 | Anthropic API 密钥 (Claude) |
| `GOOGLE_API_KEY` | 可选 | Google AI API 密钥 (Gemini) |

> **注意**: 至少配置一个 LLM API 密钥

### 数据源 API Keys

| 变量 | 必需 | 说明 |
|------|------|------|
| `ALPHA_VANTAGE_API_KEY` | 可选 | Alpha Vantage 金融数据 API |
| `FRED_API_KEY` | 可选 | 美联储经济数据 API |
| `FINNHUB_API_KEY` | 可选 | Finnhub 股票新闻 API |

### 数据库配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DATABASE_MODE` | `sqlite` | 数据库类型: `sqlite` / `postgresql` |
| `DATABASE_URL` | `sqlite:///./db/trading.db` | SQLite 连接字符串 |
| `POSTGRES_HOST` | `localhost` | PostgreSQL 主机 |
| `POSTGRES_PORT` | `5432` | PostgreSQL 端口 |
| `POSTGRES_USER` | `postgres` | PostgreSQL 用户 |
| `POSTGRES_PASSWORD` | - | PostgreSQL 密码 |
| `POSTGRES_DB` | `trading` | PostgreSQL 数据库名 |
| `CHROMA_DB_PATH` | `./db/chroma` | ChromaDB 向量数据库路径 |

### 缓存与任务队列

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `REDIS_URL` | - | Redis 连接 URL (可选) |
| `USE_TASK_QUEUE` | `false` | 启用 Redis Stream 任务队列 |

### 安全配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `API_KEY` | - | Admin API 访问密钥 |
| `API_KEY_ENABLED` | `false` | 是否启用 API Key 认证 |
| `CORS_ORIGINS` | `http://localhost:3000` | 允许的跨域来源 (逗号分隔) |

### JWT 认证

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `JWT_SECRET_KEY` | - | JWT 签名密钥 |
| `JWT_ALGORITHM` | `HS256` | JWT 算法 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access Token 过期时间 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh Token 过期时间 |

### OAuth 2.0

| 变量 | 说明 |
|------|------|
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret |
| `GITHUB_CLIENT_ID` | GitHub OAuth Client ID |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth Client Secret |

### WebAuthn/Passkey

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WEBAUTHN_RP_ID` | `localhost` | Relying Party ID |
| `WEBAUTHN_RP_NAME` | `Stock Agents Monitor` | Relying Party 名称 |
| `WEBAUTHN_ORIGIN` | `http://localhost:3000` | 允许的来源 |

### 调度器配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DAILY_ANALYSIS_ENABLED` | `false` | 启用每日自动分析 |
| `DAILY_ANALYSIS_HOUR` | `9` | 每日分析执行小时 |
| `DAILY_ANALYSIS_MINUTE` | `30` | 每日分析执行分钟 |

### Scout Agent 配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DUCKDUCKGO_ENABLED` | `true` | 启用 DuckDuckGo 搜索 |
| `DUCKDUCKGO_TIMEOUT` | `10` | 搜索超时时间 (秒) |
| `SCOUT_SEARCH_LIMIT` | `10` | 搜索结果数量限制 |
| `SCOUT_ENABLE_VALIDATION` | `true` | 启用 Ticker 验证 |

### LangSmith 追踪

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `LANGSMITH_ENABLED` | `false` | 启用 LangSmith 追踪 |
| `LANGSMITH_API_KEY` | - | LangSmith API 密钥 |
| `LANGSMITH_PROJECT` | `stock-agents` | LangSmith 项目名 |
| `LANGSMITH_TRACE_SAMPLING_RATE` | `1.0` | 采样率 |

### AI 配置加密

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AI_CONFIG_ENCRYPTION_KEY` | 自动生成 | AI Provider API 密钥加密密钥 (Fernet) |

> 如未设置，系统自动生成并存储于 `./db/.encryption_key`

### 通知系统配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `TELEGRAM_BOT_TOKEN` | - | Telegram Bot API Token |
| `TELEGRAM_API_BASE` | `https://api.telegram.org` | Telegram API 基础 URL（可选） |

---

## AI 配置系统

### 概述

系统支持通过 UI 界面动态配置多个 AI 提供商，无需修改代码或重启服务。

### 支持的提供商类型

| 类型 | 说明 | Base URL |
|------|------|----------|
| `openai` | 官方 OpenAI | https://api.openai.com/v1 |
| `openai_compatible` | OpenAI 兼容 (NewAPI/OneAPI/OpenRouter) | 用户自定义 |
| `google` | Google Gemini | - |
| `anthropic` | Anthropic Claude | - |
| `deepseek` | DeepSeek | https://api.deepseek.com/v1 |

### 模型分配场景

| 场景 | 用途 | 推荐模型 |
|------|------|----------|
| `deep_think` | 复杂推理 (风险评估/辩论) | gpt-4o / claude-3-sonnet / gemini-pro |
| `quick_think` | 快速任务 (发现/新闻) | gpt-4o-mini / gemini-flash |
| `synthesis` | 报告合成 | gpt-4o / gemini-pro |

### API 端点

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/api/ai/providers` | 列出所有提供商 |
| POST | `/api/ai/providers` | 创建提供商 |
| PUT | `/api/ai/providers/{id}` | 更新提供商 |
| DELETE | `/api/ai/providers/{id}` | 删除提供商 |
| POST | `/api/ai/providers/{id}/test` | 测试连接 |
| GET | `/api/ai/models` | 获取模型配置 |
| PUT | `/api/ai/models/{key}` | 更新模型配置 |
| POST | `/api/ai/refresh` | 刷新配置缓存 |
| GET | `/api/ai/status` | 获取配置状态 |

### 前端入口

侧边栏 → "AI Config" 按钮 → 配置面板

### 安全特性

- API 密钥使用 Fernet 对称加密存储
- 前端显示脱敏密钥 (`sk-****...****`)
- 更新时空密钥保持原值

---

## 任务队列系统

### 概述

系统支持两种任务处理模式：

| 模式 | 技术 | 并发能力 | 适用场景 |
|------|------|----------|----------|
| **开发模式** | FastAPI BackgroundTasks | 单进程限制 (~4) | 本地开发 |
| **生产模式** | Redis Stream + Worker | 水平无限扩展 | 生产部署 |

### 启用任务队列

```bash
# 1. 启动 Redis
docker-compose --profile cache up -d

# 2. 配置环境变量
USE_TASK_QUEUE=true
REDIS_URL=redis://localhost:6379

# 3. 启动 Worker 进程（可多实例）
python -m workers.analysis_worker --name worker-1
python -m workers.analysis_worker --name worker-2
python -m workers.analysis_worker --name worker-3

# 4. 启动 API 服务
python main.py
```

### Worker 管理

```bash
# 查看运行中的 Worker
ps aux | grep analysis_worker

# 优雅停止 Worker (SIGTERM)
kill -TERM <pid>

# 强制停止 Worker (SIGINT)
kill -INT <pid>
```

### 任务流程

```
API 请求 → 入队 Redis Stream → Worker 消费 → 执行分析 → SSE 推送结果
```

---

## 通知系统配置

### 概述

系统支持多渠道推送通知（当前已实现 Telegram，计划支持企业微信、钉钉），可在分析完成、定时任务等场景自动推送消息。

### Telegram Bot 配置教程

#### 1. 创建 Telegram Bot

1. 在 Telegram 中搜索 [@BotFather](https://t.me/BotFather)
2. 发送 `/newbot` 命令
3. 按提示输入 Bot 名称和用户名
4. 获取 Bot Token（格式：`123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`）

#### 2. 获取 Chat ID

**方法 1: 通过 API 获取**
1. 与你的 Bot 对话，发送任意消息（如 `/start`）
2. 在浏览器访问：
   ```
   https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
   ```
3. 在返回的 JSON 中找到 `message.chat.id`（通常是一个数字）

**方法 2: 使用第三方 Bot**
1. 搜索 [@userinfobot](https://t.me/userinfobot)
2. 发送任意消息，Bot 会返回你的 Chat ID

#### 3. 配置后端环境变量

在 `apps/server/.env` 中添加：

```bash
# Telegram Bot 配置
TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
TELEGRAM_API_BASE=https://api.telegram.org  # 可选，默认值
```

#### 4. 前端配置通知

1. 登录系统
2. 进入 **设置页面**（Settings）
3. 找到 **通知配置** 区域
4. 填写配置：
   - **Chat ID**: 你的 Telegram Chat ID
   - **信号阈值**: 选择推送的最低信号级别
     - `STRONG_BUY`: 仅推送强买入/强卖出信号
     - `BUY`: 推送买入/卖出及以上信号
     - `ALL`: 推送所有信号（包括持有）
   - **静默时段**（可选）: 设置不接收通知的时间段（如 22:00-08:00）
5. 点击 **测试通知** 验证配置
6. 保存配置

#### 5. 通知触发场景

| 场景 | 说明 |
|------|------|
| **分析完成** | Agent 完成股票分析后自动推送 |
| **定时分析** | 每日自动分析完成后推送 |
| **手动测试** | 点击"测试通知"按钮立即发送 |

#### 6. 通知内容示例

```
📊 AAPL 分析完成

信号: STRONG_BUY | 置信度: 85%
技术面显示强劲上涨趋势，RSI 指标健康，MACD 金叉确认。
基本面支撑稳固，Q4 财报超预期...
```

### 静默时段说明

静默时段支持跨午夜配置：

- **不跨午夜**: 如 `09:00-18:00`，仅在 9 点到 18 点之间静默
- **跨午夜**: 如 `22:00-08:00`，从晚上 10 点到次日早上 8 点静默

### 查看通知日志

在设置页面的 **通知日志** 区域可以查看：
- 发送时间
- 通知内容
- 发送状态（成功/失败）
- 错误信息（如有）

### 故障排查

**问题 1: 测试通知失败**
- 检查 Bot Token 是否正确
- 确认 Chat ID 是否正确
- 确保已与 Bot 发起过对话（发送 `/start`）

**问题 2: 收不到分析完成通知**
- 检查信号阈值设置（可能信号未达到阈值）
- 检查是否在静默时段内
- 查看通知日志确认发送状态

**问题 3: Telegram API 访问失败**
- 检查网络连接
- 如在中国大陆，可能需要配置代理或使用自建 Telegram Bot API 服务器

---

## 开发工作流

### 1. 分支命名规范

- `feature/<name>` - 新功能
- `fix/<issue-id>` - Bug 修复
- `refactor/<name>` - 重构
- `docs/<name>` - 文档更新

### 2. 提交信息规范

使用 [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

feat: 新增功能
fix: Bug 修复
docs: 文档更新
refactor: 代码重构
test: 测试相关
chore: 构建/配置变更
```

示例:
```
feat(portfolio): add correlation heatmap component
fix(api): handle missing price data gracefully
docs(readme): update environment setup guide
```

### 3. Pull Request 流程

1. 从 `main` 创建功能分支
2. 完成开发并通过本地测试
3. 提交 PR 并等待 CI 检查通过
4. 请求代码审查
5. 合并后删除功能分支

---

## 测试流程

### 后端测试

```bash
cd apps/server

# 运行所有测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/integration/test_analyze_api.py -v

# 生成覆盖率报告
pytest tests/ --cov=. --cov-report=html

# 仅运行快速单元测试
pytest tests/unit/ -v
```

**测试目录结构:**
```
tests/
├── unit/
│   ├── test_data_router.py
│   ├── test_market_analyst_router.py
│   ├── test_memory_service.py
│   └── test_resilience.py
├── integration/
│   ├── test_analyze_api.py
│   └── test_watchlist_api.py
├── fixtures/
│   ├── sample_market_data.py
│   └── mock_llm_responses.py
└── conftest.py
```

### 前端测试

```bash
cd apps/client

# TypeScript 类型检查
npx tsc --noEmit
```

---

## 代码规范

### Python (后端)

- **代码格式**: Ruff (line-length: 120)
- **Lint 规则**: E, F, W, I, N, UP, B, C4（忽略 E501）
- **类型检查**: mypy
- **测试框架**: pytest + pytest-asyncio

运行检查:
```bash
ruff check .
ruff check . --fix  # 自动修复
mypy api/ services/ config/ db/
```

### TypeScript (前端)

- **严格模式**: `strict: true`
- **无 any**: `noImplicitAny: true`
- **空检查**: `strictNullChecks: true`

运行检查:
```bash
npx tsc --noEmit
```

---

## 目录结构

```
HeavenlyMechanicPavilion/
├── apps/
│   ├── client/                 # React 19 + Vite 前端
│   │   ├── components/         # UI 组件 (33 个)
│   │   ├── hooks/              # TanStack Query Hooks (20 个)
│   │   ├── pages/              # 页面组件 (12 个)
│   │   ├── services/           # API 调用层
│   │   └── types.ts            # TypeScript 类型 (801 行)
│   │
│   └── server/                 # FastAPI 后端
│       ├── api/
│       │   ├── routes/         # REST API 路由 (31 个)
│       │   ├── dependencies.py # 依赖注入
│       │   ├── middleware.py   # 中间件
│       │   └── sse.py          # SSE 封装
│       ├── services/           # 业务服务层 (34 个)
│       ├── workers/            # 后台 Worker
│       │   └── analysis_worker.py
│       ├── db/                 # SQLModel ORM
│       ├── config/             # 配置管理
│       │   ├── settings.py
│       │   ├── oauth.py
│       │   └── prompts.yaml
│       ├── tests/              # 测试用例
│       └── tradingagents/      # Agent 框架
│           ├── agents/         # 18 个 Agent
│           ├── graph/          # LangGraph 编排
│           │   └── subgraphs/  # SubGraph 模块
│           └── dataflows/      # 数据源适配器
│
├── docs/                       # 项目文档
│   ├── ARCH.md                 # 架构设计
│   ├── PRD.md                  # 产品需求
│   ├── CONTRIB.md              # 贡献指南（本文件）
│   └── RUNBOOK.md              # 运维手册
│
├── plans/                      # 开发计划
├── docker-compose.yml          # Docker 编排
├── CLAUDE.md                   # AI 编码指引
└── IMPLEMENTATION_SUMMARY.md   # 实施总结
```
