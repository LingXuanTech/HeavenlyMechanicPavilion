# 股票 Agents 监控系统迭代实施计划 (Implementation Plan)

本计划旨在基于现有架构，进一步增强系统的发现能力、数据稳定性和决策智能化水平。我们将通过架构重构最大化多 Agent 的协同潜力，并引入工业级的观测、评估与自我进化机制。

## 阶段 1: Scout Agent 联网能力增强 (Discovery Capability) - **P0 ✅ DONE**
**目标**: 赋予 Scout Agent 实时搜索市场热点的能力，解决 LLM 知识滞后问题。

### 1.1 集成搜索工具
- [x] **引入搜索服务**: 集成 `DuckDuckGo`（`duckduckgo_search.py`）
- [x] **封装 ToolNode**: 创建 `scout_tools.py`，包含 `search_market_news`、`validate_ticker` 等工具

### 1.2 优化发现工作流
- [x] **Query 理解**: 优化 Prompt（`prompts.yaml`），Agent 使用工具搜索后再输出
- [x] **代码验证**: `validate_ticker` 工具调用 `MarketRouter` 验证 Ticker 有效性

**实现文件**:
- `tradingagents/dataflows/duckduckgo_search.py` (新建)
- `tradingagents/agents/utils/scout_tools.py` (新建)
- `tradingagents/agents/analysts/scout_agent.py` (重写)
- `tradingagents/dataflows/interface.py` (修改)
- `config/prompts.yaml` (修改)
- `config/settings.py` (修改)

---

## 阶段 2: 架构深度重构与工程化 (Architecture & Engineering) - **P1 ✅ DONE**
**目标**: 从"串行流水线"转向"并行协同网络"，并提升系统的鲁棒性与可观测性。

### 2.1 并行分析与灵活状态
- [x] **重构 `setup.py`**: 实现 Analyst 节点的并行执行（Parallel Router + Sync Point 模式）
- [x] **结构化输出优化**: 全面改用 LLM 的 **Structured Output (Pydantic)** 特性 ✅
- [ ] **动态状态管理**: 将 `AgentState` 中的固定报告字段改为动态字典（后续迭代）

### 2.2 可观测性与评估 (Observability & Eval)
- [x] **LangSmith 接入**: 集成 LangSmith 追踪 + Token 消耗监控（`langsmith_service.py`, `token_monitor.py`）
- [ ] **自动化评估 (LLM-as-a-Judge)**: 引入评估框架（后续迭代）

**实现文件**:
- `tradingagents/graph/setup.py` (核心重构)
- `tradingagents/agents/utils/agent_utils.py` (优化)
- `tradingagents/graph/trading_graph.py` (修改)
- `services/langsmith_service.py` (新建)
- `services/token_monitor.py` (新建)
- `api/routes/admin.py` (添加观测端点)

**新增 API 端点**:
- `GET /api/admin/observability/langsmith-status`
- `GET /api/admin/observability/token-usage`
- `GET /api/admin/observability/summary`

---

## 阶段 3: 市场差异化与专家子图 (Market-Specific) - **P2**
**目标**: 针对 A 股、港股、美股的不同特性，提供定制化的分析逻辑。

### 3.1 A 股深度适配
- [ ] **政策分析 Agent**: 增加专门解读国内政策、行业规划的节点。
- [ ] **特色数据**: 接入北向资金、龙虎榜、涨跌停状态。

### 3.2 美/港股适配
- [ ] **宏观对冲逻辑**: 强化利率、非农数据对估值的影响分析。

---

## 阶段 4: 数据底座加固 (Data Reliability) - **P2**
- [x] **Redis 集成**: 已支持 Redis 缓存（`cache_service.py`），可选启用
- [ ] **AkShare 鲁棒性**: 增加针对 A 股接口的自动重试与备用源切换。

---

## 阶段 5: 信任、回测与舆情 (Trust & Insight) - **P3**
- [ ] **回测专家 (BacktestAgent)**: 负责历史模拟与胜率统计。
- [ ] **舆情分析师 (SentimentAgent)**: 监控 Reddit/Twitter/东财吧。

---

## 阶段 6: 智能进化与人机协同 (Evolution & Collaboration) - **P4**
**目标**: 实现 Agent 的自我优化和深度用户交互。

### 6.1 Agent 自我进化
- [ ] **反思闭环**: 实现 Agent 定期回顾预测准确率并自动微调 System Prompt 的机制。
- [ ] **多模型赛马**: 引入多模型共识机制，自动选择表现最优的模型结论。

### 6.2 人机共创决策 (Human-in-the-loop)
- [ ] **论点修正**: 允许用户在前端修正 Agent 的某个论点，并触发 Graph 的局部重新运行。
- [ ] **协作作战室**: 支持多用户共同向 Agent 提问并汇总决策。

---

## 阶段 7: 前端体验升级 (UX Enhancement) - **P5**
- [ ] **专业图表**: 引入 `TradingView Lightweight Charts`。
- [ ] **流式 UI 响应**: 优化 SSE，支持报告内容的实时流式打字机效果。
- [ ] **高保真 TTS**: 接入 OpenAI/Gemini TTS 替换浏览器原生语音。

---

## 变更日志

### 2026-01-28: P0 + P1 实施完成
- ✅ Scout Agent 集成 DuckDuckGo 搜索
- ✅ Analyst 节点并行化（Parallel Router + Sync Point 模式）
- ✅ LangSmith 可观测性 + Token 监控（14 种模型定价）
- ✅ 6 个新 Admin API 端点用于可观测性

**新增文件**:
- `tradingagents/dataflows/duckduckgo_search.py` - DuckDuckGo 搜索封装
- `tradingagents/agents/utils/scout_tools.py` - Scout Agent LangChain 工具
- `services/langsmith_service.py` - LangSmith 追踪服务（单例）
- `services/token_monitor.py` - Token 消耗监控

**修改文件**:
- `tradingagents/dataflows/interface.py` - 添加搜索数据路由
- `tradingagents/agents/analysts/scout_agent.py` - 重写，集成工具
- `tradingagents/graph/setup.py` - 核心重构，实现并行化
- `tradingagents/graph/trading_graph.py` - 添加 LangSmith 追踪
- `config/prompts.yaml` - 更新 Scout Agent prompt
- `config/settings.py` - 添加 DuckDuckGo/LangSmith 配置
- `api/routes/admin.py` - 添加可观测性端点

**新增依赖**: `duckduckgo-search>=6.0.0`, `langsmith>=0.1.100`, `cryptography>=46.0.4`, `psutil>=7.2.1`
