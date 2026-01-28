# Contributing Guide

> 自动生成自 package.json / pyproject.toml / .env.example
> 最后更新: 2026-01-28

## 目录

1. [开发环境设置](#开发环境设置)
2. [项目脚本参考](#项目脚本参考)
3. [环境变量](#环境变量)
4. [AI 配置系统](#ai-配置系统)
5. [开发工作流](#开发工作流)
6. [测试流程](#测试流程)
7. [代码规范](#代码规范)

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
uv pip install -r requirements.txt

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
| `pytest tests/` | 运行所有测试 |
| `pytest tests/ -v --cov=.` | 运行测试并生成覆盖率报告 |
| `ruff check .` | 运行代码风格检查 |
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

> 至少配置一个 LLM API 密钥

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

### 安全配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `API_KEY` | - | Admin API 访问密钥 |
| `API_KEY_ENABLED` | `false` | 是否启用 API Key 认证 |
| `CORS_ORIGINS` | `http://localhost:3000` | 允许的跨域来源 (逗号分隔) |

### 调度器配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DAILY_ANALYSIS_ENABLED` | `false` | 启用每日自动分析 |
| `DAILY_ANALYSIS_HOUR` | `9` | 每日分析执行小时 |
| `DAILY_ANALYSIS_MINUTE` | `30` | 每日分析执行分钟 |

### 其他配置

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `CHROMA_DB_PATH` | `./db/chroma` | ChromaDB 向量数据库路径 |
| `PROMPTS_YAML_PATH` | `./config/prompts.yaml` | Prompt 配置文件路径 |
| `REDIS_URL` | - | Redis 连接 URL (可选) |

### AI 配置加密

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AI_CONFIG_ENCRYPTION_KEY` | 自动生成 | AI Provider API 密钥加密密钥 (Fernet) |

> 如未设置，系统自动生成并存储于 `./db/.encryption_key`

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

**当前测试统计:**
- 单元测试: 29 个
- 集成测试: 29 个
- 总计: 58 个

### 前端测试

```bash
cd apps/client

# TypeScript 类型检查
npx tsc --noEmit

# ESLint 检查
npm run lint
```

---

## 代码规范

### Python (后端)

- **代码格式**: Ruff (line-length: 120)
- **类型检查**: mypy
- **测试框架**: pytest + pytest-asyncio

运行检查:
```bash
ruff check .
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
my-trading/
├── apps/
│   ├── client/          # React 19 + Vite 前端
│   │   ├── components/  # UI 组件
│   │   ├── hooks/       # TanStack Query Hooks
│   │   ├── services/    # API 调用层
│   │   └── types.ts     # TypeScript 类型
│   │
│   └── server/          # FastAPI 后端
│       ├── api/routes/  # REST API 路由
│       ├── services/    # 业务服务层
│       ├── db/          # SQLModel ORM
│       ├── config/      # 配置管理
│       ├── tests/       # 测试用例
│       └── tradingagents/  # Agent 框架
│
├── docs/                # 项目文档
├── plans/               # 开发计划
└── .github/workflows/   # CI/CD 配置
```
