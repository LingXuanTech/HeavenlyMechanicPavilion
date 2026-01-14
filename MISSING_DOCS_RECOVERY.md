# 缺失文档清单与恢复建议

在梳理过程中发现，根目录下的 `README.md` 引用了大量在 `docs/` 目录下并不存在的文件。以下是缺失文档的清单以及基于当前代码逻辑的恢复建议。

---

## 1. 缺失文档清单 (Critical)

| 引用文件名 | 描述 | 恢复优先级 |
| --- | --- | --- |
| `docs/SETUP.md` | 安装依赖、环境配置、本地运行指南 | **最高** |
| `docs/ARCHITECTURE.md` | 多智能体工作流、项目结构、子系统设计 | **高** |
| `docs/API.md` | REST、SSE、WebSocket 和管理端点文档 | **高** (已由 `API_OVERVIEW.md` 部分替代) |
| `docs/CONFIGURATION.md` | 环境变量、数据源路由、Agent 配置 | 中 |
| `docs/DEPLOYMENT.md` | Docker 部署、生产环境配置、扩展策略 | 中 |
| `docs/DEVELOPMENT.md` | 开发规范、测试策略、贡献流程 | 中 |

---

## 2. 核心文档恢复建议 (基于代码分析)

### A. SETUP.md 核心内容建议
- **环境要求**: Python 3.10+, Node.js 18+, PostgreSQL, Redis。
- **后端安装**: 
    - 使用 `uv` 或 `pip` 安装 `packages/backend/requirements.txt`。
    - 配置 `.env` 文件（需包含 `DATABASE_URL`, `REDIS_HOST`, `OPENAI_API_KEY` 等）。
    - 运行数据库迁移：`alembic upgrade head`。
- **前端安装**:
    - 进入 `packages/frontend`，运行 `pnpm install`。
    - 启动开发服务器：`pnpm dev`。

### B. ARCHITECTURE.md 核心内容建议
- **编排引擎**: 详细说明 `LangGraph` 如何管理 `AgentState`。
- **状态流转**: 描述从 `Analyst` -> `Researcher` -> `Trader` -> `Risk` 的状态传递对象。
- **持久化层**: 说明 `SQLAlchemy` 模型与 `AnalysisSession` 的对应关系。
- **流式架构**: 解释 `SessionEventManager` 如何通过 Redis Pub/Sub 将后端事件推送到前端。

---

## 3. 临时替代方案
在正式恢复 `docs/` 目录前，建议开发者参考以下新生成的梳理文档：
- [项目架构概览](./README_OVERVIEW.md)
- [API 接口概览](./API_OVERVIEW.md)
- [数据流集成概览](./DATAFLOW_OVERVIEW.md)

---
*本文档由 Architect 模式自动梳理生成，最后更新日期：2026-01-14*