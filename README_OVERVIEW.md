# TradingAgents 项目核心架构概览

本文档旨在为开发者提供 **TradingAgents** 项目的高层级技术梳理，涵盖系统架构、智能体工作流、核心组件及后续开发建议。

---

## 1. 项目定位
**TradingAgents** 是一个基于 **LangGraph** 和 **FastAPI** 的多智能体金融交易决策框架。它通过模拟专业投资团队（分析师、研究员、交易员、风控官）的协作流程，利用大语言模型（LLM）对市场数据进行深度分析并生成风险受控的交易决策。

---

## 2. 系统架构 (Monorepo)

项目采用 PNPM Workspace 组织的单体仓库结构：

- **`packages/backend`**: 核心后端服务。
    - `app/`: FastAPI 应用层，处理 API 请求、WebSocket 流、数据库持久化及任务调度。
    - `src/tradingagents/`: 核心逻辑层。
        - `graph/`: 基于 LangGraph 的智能体编排逻辑。
        - `agents/`: 各类智能体的定义与工具集。
        - `plugins/`: 插件系统，支持动态加载数据源（Vendors）和智能体逻辑。
        - `dataflows/`: 数据集成层，对接 Alpha Vantage, YFinance 等 API。
- **`packages/frontend`**: 基于 Next.js 的控制中心 UI，提供交易会话监控、智能体状态可视化及系统管理功能。
- **`packages/shared`**: 存放前后端共用的类型定义、OpenAPI 客户端代码及工具函数。

---

## 3. 智能体工作流 (LangGraph 编排)

项目最核心的逻辑在于其智能体协作图（Graph），流程如下：

### A. 分析阶段 (Analyst Team)
并行或顺序运行多个专业分析师，收集原始信号：
- **Market Analyst**: 技术指标与价格走势分析。
- **Fundamentals Analyst**: 财报、估值等基本面数据分析。
- **News Analyst**: 实时新闻与宏观事件分析。
- **Social Media Analyst**: 社交媒体情绪与热度分析。

### B. 研究与辩论阶段 (Research Panel)
- **Bull & Bear Researchers**: 针对分析师报告，分别从看多和看空两个对立视角进行深度研究和辩论，暴露认知盲点。
- **Research Manager**: 总结辩论内容，提炼核心论点，形成综合研究报告。

### C. 决策与风控阶段 (Execution & Risk)
- **Trader Agent**: 根据研究报告，制定具体的投资计划（标的、仓位、方向）。
- **Risk Management Team**: 激进、中立、保守三方风控员对计划进行多维度评审。
- **Risk Judge**: 最终裁决者，根据风控评审结果给出最终的“执行”或“拒绝”指令。

---

## 4. 核心技术特性
- **流式响应 (Streaming)**: 利用 Redis 和 FastAPI SSE/WebSocket 实现智能体思考过程的实时推送。
- **插件化设计**: 
    - **Vendor Plugins**: 统一的数据接入层，支持热插拔。
    - **Agent Plugins**: 允许在不重启服务的情况下调整智能体行为。
- **持久化与记忆**: 使用 PostgreSQL 存储交易会话，利用 ChromaDB 或自定义 Memory 模块实现智能体的长期记忆与反思（Reflection）。
- **高性能设计**: 集成了响应压缩、数据库连接池优化及 Redis 智能缓存。

---

## 5. 发现的问题与后续建议

### ⚠️ 当前问题
1. **文档缺失**: 根目录下 `docs/` 文件夹缺失，导致 `README.md` 中的许多链接失效。
2. **配置复杂性**: 依赖项较多（PostgreSQL, Redis, 多种 LLM API），缺乏一键式环境检查工具。

### 🚀 优化建议
1. **恢复文档**: 建议根据代码逻辑重新生成 `ARCHITECTURE.md`, `API.md` 和 `SETUP.md`。
2. **增强测试**: 增加针对单个 Agent 决策逻辑的单元测试，确保 LLM Prompt 变更后的稳定性。
3. **监控增强**: 在前端增加更直观的 LangGraph 运行状态图（Trace 可视化）。

---
*本文档由 Architect 模式自动梳理生成，最后更新日期：2026-01-14*