# TradingAgents 开发路线图 (Development Roadmap)

本文档基于当前代码库的扫描结果，梳理了项目从当前“开发中”状态到“生产就绪”状态所需的关键开发任务。

---

## 阶段一：核心服务补全 (基础稳固)
此阶段重点解决后端核心服务的缺失，确保系统能够正常运行和配置。

- **[ ] 实现 `AgentLLMConfigService`**:
    - 目前 `app/api/agents.py` 中相关逻辑被注释。
    - 需要实现数据库模型、Schema 和 Service 层，支持为每个 Agent 独立配置 LLM（如：分析师用 GPT-4o-mini，研究经理用 GPT-4o）。
- **[ ] 完善 `PortfolioRebalancingService`**:
    - 实现 `Market Cap Weighting` (市值加权) 算法。
    - 实现执行逻辑（目前仅有计划，无实际执行）。
- **[ ] 恢复 `docs/` 目录**:
    - 补全 `SETUP.md`, `ARCHITECTURE.md`, `API.md` 等核心文档，确保团队协作顺畅。

---

## 阶段二：功能增强与集成 (能力提升)
此阶段重点扩展系统的交易能力和数据源。

- **[ ] 扩展券商支持 (Brokers)**:
    - 目前仅支持 Alpaca。
    - 计划集成：Interactive Brokers (IBKR) 或 Binance (针对加密货币)。
- **[ ] 增强数据流 (Dataflows)**:
    - 实现 `Alpha Vantage` 的异步化请求，减少阻塞。
    - 完善 `Reddit` 和 `Google News` 的实时抓取与清洗逻辑。
- **[ ] 前端控制中心补全**:
    - 实现 Agent 运行轨迹的实时可视化图表。
    - 增加“手动干预”模式，允许用户在 Risk Judge 环节进行人工审批。

---

## 阶段三：稳定性与性能优化 (生产就绪)
此阶段重点关注系统在高并发和长时间运行下的表现。

- **[ ] 引入语义缓存 (Semantic Caching)**:
    - 使用向量数据库缓存 LLM 对相似新闻的分析结果，降低 Token 成本。
- **[ ] 完善监控与告警**:
    - 实现基于 Prometheus 的自定义指标监控（如：Agent 决策成功率、API 延迟分布）。
    - 集成 Slack/Discord 告警通知。
- **[ ] 自动化测试覆盖**:
    - 增加针对 LangGraph 状态流转的集成测试。
    - 编写针对 Dataflow 异常回退逻辑的单元测试。

---

## 阶段四：上线准备 (Launch)
- **[ ] 环境自检脚本**: 编写 `scripts/check_env.py`。
- **[ ] 生产环境压力测试**: 模拟多会话并发运行，观察内存和数据库连接池表现。
- **[ ] 最终安全审计**: 检查 API 鉴权逻辑和敏感信息加密存储。

---
*本文档由 Architect 模式自动生成，最后更新日期：2026-01-14*