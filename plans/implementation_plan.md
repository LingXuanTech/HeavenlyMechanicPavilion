# 股票 Agents 监控大屏开发计划 (Final Version)

## 1. 项目概述
本项目旨在将现有的 `TradingAgents` 逻辑封装为 Web 服务，并提供一个实时监控大屏，展示 AI Agent 对股票的分析建议、技术指标和新闻摘要。

## 2. 系统架构

```mermaid
graph TD
    subgraph Frontend [React Dashboard (Vite)]
        UI[Dashboard UI]
        API_Client[API Service]
    end

    subgraph Backend [FastAPI Server]
        API[FastAPI Routes]
        Scheduler[APScheduler]
        Graph[TradingAgentsGraph]
        DB[(SQLite)]
    end

    subgraph External_Data
        YF[yfinance]
        AV[Alpha Vantage]
        LLM[Gemini/GPT-4o-mini]
    end

    UI <--> API_Client
    API_Client <--> API
    API <--> DB
    API <--> Graph
    Scheduler --> Graph
    Graph <--> External_Data
    Graph --> DB
```

## 3. 核心任务分解

### 后端 (Python/FastAPI)
- **API 基础架构**: 搭建 FastAPI 框架，配置 CORS 以支持前端调用。
- **数据库设计**: 
    - `Watchlist`: 存储用户关注的股票代码（如 `AAPL`, `600276.SH`）。
    - `AnalysisResult`: 存储 Agent 运行后的完整状态（JSON）和核心决策（Buy/Sell/Hold）。
- **Agent 增强 (对齐 README)**:
    - **Scout Agent**: 实现股票发现逻辑，对接前端 "AI Market Scout"。
    - **Macro Analyst**: 增加宏观经济分析节点，追踪利率、GDP 等。
    - **Portfolio Agent**: 实现跨股票相关性分析，提供组合建议。
    - **Memory Module**: 激活并优化基于 ChromaDB 的记忆反射机制。
- **系统优化 (架构补充)**:
    - **SSE (Server-Sent Events)**: 实现分析进度的实时推送，对齐前端 Workflow Timeline。
    - **Task & Session Management**: 引入 `task_id` 机制支持 SSE 断线重连，引入 `thread_id` 支持对话记忆持久化。
    - **DataProvider 抽象层 (Smart Router)**: 统一处理 A/港/美股代码转换，根据市场自动切换数据源（yfinance/akshare），增加市场开收盘逻辑适配。
    - **静态资源服务**: 配置 FastAPI 托管 Agent 头像等静态资源。
    - **语言优化**: 统一后端 Prompt 为简体中文输出，确保分析理由和主播稿的阅读体验。
    - **Pydantic 模型对齐**: 在后端定义与前端 `types.ts` 完全一致的 Pydantic 模型，确保 JSON 序列化无缝对接。
    - **Prompt 管理系统**:
        - 建立 `apps/server/config/prompts.yaml` 存储各 Agent 的 System Prompt。
        - 实现热加载机制，支持通过 API 动态更新 Prompt 而无需重启。
    - **环境配置**: 补充 `GOOGLE_API_KEY` (Gemini), `AKSHARE_TOKEN` 等必要环境变量。
- **API 严格对齐**:
    - **分析接口**: `POST /api/analyze` 必须返回与前端 `AgentAnalysis` 类型完全一致的 JSON 结构。
    - **市场接口**: 实现 `GET /api/market/global` 对齐前端 `GlobalMarketAnalysis`。
    - **发现接口**: 实现 `POST /api/scout` 对齐前端 `MarketOpportunity`。
    - **快讯接口**: 实现 `GET /api/news/flash` 对齐前端 `FlashNews`。
    - **对话接口**: 实现 `POST /api/chat` 对齐前端 Fund Manager 对话功能，支持上下文记忆。
    - **语音脚本**: 在分析结果中增加专门为 TTS 优化的 "Anchor Script"。
    - **Prompt 接口**: 实现 `GET/PUT /api/settings/prompts`，允许在前端管理 Agent 的 Prompt。
    - **诊断信息**: 在 API 返回中增加 Token 消耗、运行耗时等诊断数据。
- **Agent 集成**: 将 `TradingAgentsGraph` 实例化并作为单例或依赖注入到路由中。
- **部署优化**: 增加 `docker-compose` 支持，实现一键部署。
- **定时任务**: 实现每日定时触发全量 Watchlist 分析的逻辑。

### 前端 (React/Vite) 重构
- **状态管理迁移**:
    - 将 `INITIAL_STOCKS` 和 `localStorage` 逻辑迁移至后端数据库。
    - 实现 `useWatchlist` hook，统一管理股票列表的增删改查。
- **API 服务层**:
    - 编写 `services/api.ts`，封装 Axios 拦截器，支持后端不可用时自动回退至 Mock 数据。
    - 实现 `useSSE` hook，用于订阅分析进度和实时快讯。
- **交互增强**:
    - **Workflow Timeline**: 监听 SSE 事件，动态更新 `StockDetailModal` 中的进度条。
    - **AI Scout**: 对接后端 `/api/scout`，展示带行情的搜索结果。
    - **Chat**: 对接后端 `/api/chat`，支持基于 `thread_id` 的有记忆对话。
- **实时性**:
    - 移除前端模拟的 `setInterval` 价格跳动，改为从后端获取准实时价格。

## 4. 待讨论问题
- **数据源**: 目前 `main.py` 使用 `yfinance` 和 `alpha_vantage`。对于 A 股，是否需要优先配置 `akshare` 或 `tushare`？
- **LLM 选择**: 默认使用 `gpt-4o-mini`，是否需要支持在 UI 上切换模型？
- **部署**: 是否需要 Docker 化以便于一键部署？

## 5. 后续步骤
1. 确认此计划。
2. 切换至 **Code** 模式开始后端基础架构开发。
