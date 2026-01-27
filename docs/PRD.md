# 股票 Agents 监控大屏 PRD (Updated)

## 1. 项目愿景
开发一个基于 **TradingAgents** 框架的专业级金融情报系统。通过编排一组专业 AI Agent（Scout, Analyst, Researcher, Risk Manager, Fund Manager）进行对抗性辩论和深度分析，为投资者提供实时、结构化的决策支持，并以交易室监控大屏的形式展示。

## 2. 核心角色与 Agent 架构
系统模拟真实资产管理公司的流程，采用多 Agent 协作模式：

### 2.1 🕵️ 发现者 (Scout Agent)
- **职责**：根据自然语言指令（如“寻找港股中低估值的 AI 供应链股票”）扫描市场。
- **能力**：语义搜索、趋势识别、行业过滤。

### 2.2 🔍 分析师团队 (Analyst Team)
- **技术分析师**：计算 RSI, MACD, 布林带, 关键支撑/压力位。
- **情绪分析师**：抓取最新新闻、社交媒体情绪。
- **基本面分析师**：分析财报、P/E 估值、行业催化剂。

### 2.3 ⚔️ 研究员辩论 (Researcher Debate)
- **多方研究员 (Bull Agent)**：寻找最强力的买入理由。
- **空方研究员 (Bear Agent)**：寻找最强力的看空理由。
- **机制**：通过对抗性辩论减少 AI 幻觉，暴露潜在风险。

### 2.4 🛡️ 风险经理 (Risk Manager)
- **职责**：专注于下行风险保护，拥有“一票否决权”。
- **输出**：0-10 风险评分、波动率评估、最大回撤预测。

### 2.5 👨‍💼 基金经理 (Fund Manager)
- **职责**：综合所有 Agent 输入，做出最终决策。
- **输出**：信号（Strong Buy/Hold/Sell）、入场区间、止盈止损位、置信度。

## 3. 核心功能需求

### 3.1 Watchlist 管理
- 支持 A 股/港股/美股代码管理。
- 支持通过 Scout Agent 发现并添加新股票。

### 3.2 自动化分析流程
- **定时任务**：每天固定时间（如开盘前/收盘后）自动运行全量分析。
- **即时分析**：支持手动触发特定股票的深度分析。
- **记忆模块**：Agent 能够回顾历史预测，从错误中学习（Memory Module）。

### 3.3 监控大屏 (Dashboard)
- **实时快讯 (Watchdog)**：滚动展示与 Watchlist 相关的重大新闻。
- **工作流可视化 (Workflow Timeline)**：实时展示 Agent 正在进行的步骤。
- **可视化仪表盘**：
    - **辩论计 (Debate Meter)**：展示多空双方的力量对比。
    - **风险计 (Risk Gauge)**：直观展示交易安全性。
- **AI 语音简报 (Audio Briefing)**：生成每日早间/晚间分析摘要语音。
- **Agent 问答 (Interrogate)**：支持与 Fund Manager 对话，询问特定风险场景。

## 4. 技术架构

### 4.1 后端 (Python)
- **框架**：FastAPI + LangGraph。
- **数据源**：yfinance, Alpha Vantage, AkShare。
- **数据库**：SQLite (初期) / PostgreSQL。
- **LLM**：Gemini 3 Pro (推理), Gemini 3 Flash (快讯/对话)。

### 4.2 前端 (React)
- **框架**：React 19 + Vite + Tailwind CSS。
- **图表**：Recharts / ECharts。
- **AI 集成**：Google GenAI SDK (用于 TTS 和部分前端交互)。

## 5. 未来路线图 (Roadmap)
- **组合管理 Agent**：分析 Watchlist 股票间的相关性，建议仓位配置。
- **宏观经济分析节点**：追踪美联储利率、GDP 等宏观数据对整体情绪的影响。
- **多模型对比**：支持同时运行不同 LLM 的 Agent 进行横向对比。
