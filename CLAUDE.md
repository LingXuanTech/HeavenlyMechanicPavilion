# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TradingAgents - 多智能体LLM金融交易框架，采用PNPM monorepo架构，包含Python后端、Next.js前端和共享TypeScript包。

## Common Commands

### 根级命令 (推荐使用)
```bash
make sync              # 安装所有依赖 (pnpm + uv)
make lint              # 全栈代码检查
make format            # 全栈代码格式化
make run               # 启动后端服务
make cli               # 启动CLI交互界面
```

### 后端 (Python)
```bash
pnpm --filter @tradingagents/backend run sync          # uv sync
pnpm --filter @tradingagents/backend run lint          # ruff check
pnpm --filter @tradingagents/backend run format        # ruff format
pnpm --filter @tradingagents/backend run type-check    # mypy
pnpm --filter @tradingagents/backend run test          # pytest (全部测试)
pnpm --filter @tradingagents/backend run test -- -k "test_name"  # 单个测试
pnpm --filter @tradingagents/backend run coverage      # pytest --cov
```

### 前端 (Next.js)
```bash
pnpm --filter @tradingagents/frontend dev              # 开发服务器
pnpm --filter @tradingagents/frontend build            # 生产构建
pnpm --filter @tradingagents/frontend lint             # ESLint
pnpm --filter @tradingagents/frontend type-check       # TypeScript检查
pnpm --filter @tradingagents/frontend test             # Vitest单元测试
pnpm --filter @tradingagents/frontend test:e2e         # Playwright E2E
```

### 共享包
```bash
pnpm --filter @tradingagents/shared build              # TypeScript编译
pnpm --filter @tradingagents/shared test               # Vitest测试
```

### Docker
```bash
make docker-up         # 启动完整栈
make docker-down       # 停止容器
make docker-migrate    # 数据库迁移
```

## Architecture

### 多智能体工作流 (LangGraph)
```
分析师团队 → 研究小组 → 交易员 → 风险管理
    ↓           ↓         ↓        ↓
基本面分析   看涨/看跌   交易提案   风险评估
技术分析     辩论       信心评分   头寸规模
情感分析     盲点暴露   执行建议   合规检查
新闻分析
```

### 核心模块

**后端 (`packages/backend/`)**
- `app/api/` - FastAPI路由 (agents, auth, trading, sessions, streaming, monitoring)
- `app/services/` - 业务逻辑 (execution, risk_management, market_data, analysis_session)
- `app/repositories/` - 数据访问层 (SQLModel ORM)
- `app/middleware/` - 认证、限流、压缩、错误处理
- `src/tradingagents/agents/` - 12个专门代理角色 (分析师、研究员、交易员、风险管理)
- `src/tradingagents/graph/` - LangGraph状态机定义
- `src/tradingagents/plugins/` - 数据供应商插件系统
- `src/tradingagents/llm_providers/` - LLM提供商注册表 (OpenAI, Anthropic, Google, DeepSeek)

**前端 (`packages/frontend/`)**
- `src/app/` - Next.js App Router页面 (dashboard, sessions, admin, monitoring)
- `src/components/` - Radix UI + Tailwind组件库
- `src/hooks/` - 自定义React hooks
- `src/lib/` - API客户端和工具函数

**共享包 (`packages/shared/`)**
- `src/domain/` - 类型定义和DTOs
- `src/clients/` - 类型化API客户端
- `src/theme/` - UI主题令牌
- `src/utils/` - 通用工具函数

### 关键设计模式

1. **插件系统**: 代理和数据供应商通过注册表动态加载，支持热重载
2. **异步执行**: LangGraph同步图在ThreadPoolExecutor中运行，避免阻塞FastAPI事件循环
3. **事件流**: SSE和WebSocket双通道实时推送分析会话事件
4. **分层缓存**: Redis缓存市场数据、会话数据、代理配置

### 数据流

```
前端 → FastAPI → 服务层 → LangGraph工作流 → 代理执行
                    ↓              ↓
              Repository      插件系统
                    ↓              ↓
              PostgreSQL    数据供应商API
                    ↓
                 Redis缓存
```

## Code Style

### Python
- **Linter/Formatter**: Ruff (配置在 `pyproject.toml`)
- **类型检查**: MyPy (strict mode)
- **测试**: Pytest + pytest-asyncio

### TypeScript/React
- **Linter**: ESLint
- **Formatter**: Prettier (通过ESLint集成)
- **测试**: Vitest (单元) + Playwright (E2E)
- **UI**: Radix UI primitives + Tailwind CSS

### 提交前检查
项目配置了 `.pre-commit-config.yaml`，包含 Ruff、MyPy、ESLint 钩子。

## Environment Setup

1. 复制 `.env.example` 到 `.env` 并配置必要的API密钥
2. 运行 `make sync` 安装所有依赖
3. 运行 `make docker-up` 启动PostgreSQL和Redis
4. 运行 `make docker-migrate` 执行数据库迁移

详细配置参考 `docs/CONFIGURATION.md`
