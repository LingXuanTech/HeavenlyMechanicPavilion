# TradingAgents API 接口概览

本文档梳理了后端 FastAPI 提供的核心 API 端点，方便前端集成与系统调试。

---

## 1. 会话管理 (Sessions)
用于启动和监控智能体交易分析会话。
- **`GET /sessions/config`**: 获取当前图（Graph）的配置信息（LLM 供应商、数据源等）。
- **`POST /sessions`**: 启动一个新的分析会话。需提供 `ticker` (股票代码) 和 `trade_date`。
- **`GET /sessions`**: 分页列出历史会话，支持按状态和代码过滤。
- **`GET /sessions/{session_id}`**: 获取特定会话的详细信息及最近的事件日志。
- **`GET /sessions/{session_id}/events`**: **SSE (Server-Sent Events)** 流，实时推送智能体思考过程和决策结果。

---

## 2. 插件与供应商管理 (Vendors)
管理数据源插件（如 YFinance, Alpha Vantage）。
- **`GET /vendors/`**: 列出所有已注册的供应商插件及其能力（Capabilities）。
- **`GET /vendors/{name}/config`**: 获取特定供应商的配置（如 API Key）。
- **`PUT /vendors/{name}/config`**: 动态更新供应商配置。
- **`GET /vendors/routing/config`**: 获取数据路由配置（决定哪个方法使用哪个供应商）。
- **`POST /vendors/config/reload`**: 从配置文件热加载供应商设置。

---

## 3. 智能体配置 (Agents)
管理各个智能体（分析师、研究员等）的 Prompt 和 LLM 设置。
- **`GET /agents/`**: 列出所有智能体配置。
- **`POST /agents/`**: 创建新的智能体配置。
- **`GET /agents/{id}`**: 获取智能体详情。
- **`PUT /agents/{id}`**: 更新智能体的 Prompt 模板或 LLM 配置。
- **`POST /agents/reload`**: **热加载** 智能体注册表，使更改立即生效。
- **`GET /agents/{id}/llm-usage`**: 查询特定智能体的 Token 使用统计。

---

## 4. 系统监控 (Monitoring)
提供系统健康状况和性能指标。
- **`GET /monitoring/health`**: 综合健康检查（数据库、Redis、供应商、Worker）。
- **`GET /monitoring/metrics`**: 暴露 Prometheus 格式的监控指标。
- **`GET /monitoring/workers`**: 查看后台任务 Worker 的运行状态。
- **`GET /monitoring/alerts/history`**: 查看系统告警历史。
- **`GET /monitoring/uptime`**: 获取系统运行时间。

---

## 5. 自动交易与回测 (Auto-Trading & Backtests)
- **`POST /auto-trading/start`**: 启动自动交易逻辑。
- **`POST /backtests/run`**: 启动历史数据回测任务。

---
*注：所有接口默认需要身份验证，公共接口（如 `/health`, `/docs`）除外。*