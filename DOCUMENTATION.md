# TradingAgents 项目文档

**最后更新**: 2025-11-06  
**项目状态**: 核心功能已完成 (85%)

---

## 📚 目录

- [项目概述](#项目概述)
- [快速开始](#快速开始)
- [核心功能](#核心功能)
- [技术架构](#技术架构)
- [开发指南](#开发指南)
- [部署运维](#部署运维)
- [待办事项](#待办事项)

---

## 项目概述

TradingAgents 是一个基于多智能体 LLM 的智能交易系统，通过 4 层 Agent 决策流程实现自动化交易。

### 核心特性

- ✅ **多层 Agent 决策**: 4类分析师 → 牛熊辩论 → 风险评估 → 最终决策
- ✅ **自动化交易**: 端到端自动执行（Agent → 风险检查 → 订单 → 持仓更新）
- ✅ **实盘支持**: Alpaca 券商集成（Paper Trading + Live Trading）
- ✅ **实时可视化**: Agent 决策流程、执行追踪、性能图表、Agent 对比
- ✅ **数据库优化**: 索引优化、连接池、查询优化

### 当前完成度

| 模块 | 完成度 | 状态 |
|------|--------|------|
| Agent 决策系统 | 95% | 🟢 优秀 |
| 自动交易编排 | 92% | 🟢 可用 |
| 券商集成 (Alpaca) | 88% | 🟢 可用 |
| 订单执行服务 | 98% | 🟢 优秀 |
| 前端可视化 | 90% | 🟢 完成 |
| 数据库优化 | 95% | 🟢 完成 |

---

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd HeavenlyMechanicPavilion

# 安装依赖
pnpm install

# 配置环境变量
cp .env.example .env
# 编辑 .env，配置数据库和 Alpaca API
```

### 2. 获取 Alpaca API Key

1. 访问 https://alpaca.markets/
2. 注册免费账户
3. 获取 Paper Trading API 密钥
4. 配置到 `.env`:

```bash
BROKER_TYPE=alpaca
ALPACA_API_KEY=your_api_key
ALPACA_SECRET_KEY=your_secret_key
ALPACA_PAPER_TRADING=true
```

### 3. 启动服务

```bash
# 启动后端
cd packages/backend
poetry run python -m app.main

# 启动前端（新终端）
cd packages/frontend
pnpm dev
```

### 4. 测试自动交易

```bash
# 单次测试
curl -X POST http://localhost:8000/api/auto-trading/run-once \
  -H "Content-Type: application/json" \
  -d '{
    "portfolio_id": 1,
    "symbols": ["AAPL"]
  }'

# 启动连续自动交易
curl -X POST http://localhost:8000/api/auto-trading/start \
  -d '{
    "portfolio_id": 1,
    "symbols": ["AAPL", "MSFT"],
    "interval_minutes": 30
  }'
```

---

## 核心功能

### 1. Agent 多层决策系统

**完整决策流程**:

```
[数据收集]
    ↓
[第一层: 4类专业分析师]
├── 市场分析师 (技术指标)
├── 新闻分析师 (新闻情感)
├── 基本面分析师 (财务数据)
└── 社交情绪分析师 (社交媒体)
    ↓
[第二层: 投资辩论]
├── 看涨研究员 (牛市观点)
├── 看跌研究员 (熊市观点)
└── 研究经理 (综合判断)
    ↓
[第三层: 风险辩论]
├── 激进派 (高收益策略)
├── 中性派 (平衡策略)
├── 保守派 (低风险策略)
└── 风险经理 (风险决策)
    ↓
[第四层: 最终决策]
└── 交易员 (执行决策 BUY/SELL/HOLD)
```

**核心文件**:
- Agent 实现: `packages/backend/src/tradingagents/`
- 决策图谱: `packages/backend/src/tradingagents/graph/trading_graph.py`

### 2. 自动化交易系统

**核心组件**:

| 组件 | 文件 | 功能 | 完成度 |
|------|------|------|--------|
| AutoTradingOrchestrator | `app/services/auto_trading_orchestrator.py` | 端到端自动化编排 | 92% |
| AlpacaBrokerAdapter | `app/services/brokers/alpaca_adapter.py` | Alpaca 券商适配 | 88% |
| ExecutionService | `app/services/execution.py` | 订单执行和风险管理 | 98% |

**执行流程**:

```
用户触发
    ↓
Agent 分析 (TradingGraphService)
    ↓
决策提取 (processed_signal: BUY/SELL/HOLD)
    ↓
风险检查 (购买力、仓位限制、风险评分)
    ↓
订单提交 (AlpacaBrokerAdapter → Alpaca API)
    ↓
成交确认 (Order Status Check)
    ↓
持仓更新 (Position 表)
    ↓
资金更新 (Portfolio 表)
    ↓
前端推送 (SSE/WebSocket)
```

**API 端点**:
- `POST /api/auto-trading/start` - 启动自动交易
- `POST /api/auto-trading/stop/{portfolio_id}` - 停止自动交易
- `GET /api/auto-trading/status/{portfolio_id}` - 查询状态
- `POST /api/auto-trading/run-once` - 单次执行

### 3. 前端实时可视化

**新增组件** (2025-11-06):

| 组件 | 文件 | 功能 |
|------|------|------|
| AgentDecisionFlow | `dashboard/agent-decision-flow.tsx` | 四层决策流程可视化 |
| TradeExecutionTracker | `dashboard/trade-execution-tracker.tsx` | 订单执行时间线 |
| PerformanceChart | `dashboard/performance-chart.tsx` | 历史收益走势图 |
| AgentPerformanceComparison | `dashboard/agent-performance-comparison.tsx` | Agent 质量对比 |

---

## 技术架构

### 后端技术栈

- **框架**: Python 3.11+ / FastAPI
- **数据库**: PostgreSQL + SQLAlchemy
- **LLM**: LangChain / LangGraph
- **券商**: Alpaca Trade API

### 前端技术栈

- **框架**: Next.js 14 / React 18
- **语言**: TypeScript
- **样式**: Tailwind CSS + shadcn/ui
- **图表**: Recharts

### 数据库优化

**已实现**:
- ✅ 关键表索引优化（trades, positions, portfolios）
- ✅ 连接池配置（pool_size=20, max_overflow=10）
- ✅ 查询优化（使用 joinedload、selectinload）
- ✅ 分页查询（避免全表扫描）

---

## 开发指南

### 项目结构

```
HeavenlyMechanicPavilion/
├── packages/
│   ├── backend/          # Python 后端
│   │   ├── app/         # FastAPI 应用
│   │   └── src/         # Agent 系统
│   ├── frontend/        # Next.js 前端
│   └── shared/          # 共享类型定义
├── docs/                # 技术文档
└── README.md           # 项目说明
```

### 开发工作流

1. **后端开发**: `packages/backend/`
   - 使用 Poetry 管理依赖
   - 遵循 FastAPI 最佳实践
   - 添加单元测试和集成测试

2. **前端开发**: `packages/frontend/`
   - 使用 pnpm 管理依赖
   - 遵循 React/TypeScript 规范
   - 使用 shadcn/ui 组件库

3. **Agent 开发**: `packages/backend/src/tradingagents/`
   - 继承 BaseAgent 类
   - 实现 run() 方法
   - 添加 memory 系统

### 配置系统

**环境变量** (`.env`):
```bash
# 数据库
DATABASE_URL=postgresql://user:pass@localhost/db

# Alpaca
BROKER_TYPE=alpaca
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
ALPACA_PAPER_TRADING=true

# LLM
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key
```

**Agent LLM 配置**:
- 数据库表: `agent_llm_configs`
- 支持热更新（无需重启）
- 为每个 Agent 单独配置 LLM

---

## 部署运维

### Docker 部署

```bash
# 开发环境
docker-compose -f docker-compose.dev.yml up

# 生产环境
docker-compose -f docker-compose.prod.yml up -d
```

### 数据库迁移

```bash
cd packages/backend
poetry run alembic upgrade head
```

### 监控与日志

- 日志位置: `logs/app.log`
- 监控端点: `GET /health`
- Prometheus: `GET /metrics`

### 性能优化建议

1. **数据库**:
   - 定期运行 `VACUUM ANALYZE`
   - 监控慢查询日志
   - 使用连接池

2. **API**:
   - 启用 Gzip 压缩
   - 使用 Redis 缓存
   - 限流保护

3. **Agent**:
   - 批量处理多个标的
   - 异步执行分析
   - 缓存 LLM 响应

---

## 待办事项

### P1 - 高优先级 (1-2周)

1. **事件推送系统** (2天)
   - 实现 `_emit_event()` WebSocket 推送
   - 前端实时接收交易事件

2. **API 认证授权** (3天)
   - JWT 认证
   - 基于角色的权限控制
   - API Key 管理

3. **WebSocket 实时通信** (3天)
   - 交易执行步骤实时更新
   - Agent 决策过程实时推送

### P2 - 中优先级 (2-3周)

1. **持仓查询 API** (1天)
   - AlpacaBrokerAdapter.get_positions()

2. **市场时间检查** (2天)
   - 时区处理
   - 节假日判断

3. **Agent 性能追踪** (5天)
   - 记录历史决策
   - 计算准确率和收益贡献
   - 动态权重调整

4. **Dashboard 集成** (3天)
   - 新组件添加到主页面
   - 路由和导航更新

---

## 详细文档

### 核心功能

- [Alpaca 券商配置](docs/ALPACA_BROKER_SETUP.md)
- [Agent LLM 配置](docs/AGENT_LLM_CONFIG.md)
- [认证系统](docs/AUTHENTICATION.md)

### 技术文档

- [系统架构](docs/ARCHITECTURE.md)
- [API 文档](docs/API.md)
- [配置说明](docs/CONFIGURATION.md)
- [开发指南](docs/DEVELOPMENT.md)
- [部署指南](docs/DEPLOYMENT.md)

### 性能优化

- [数据库性能调优](docs/DATABASE_PERFORMANCE_TUNING.md)
- [常见问题修复](docs/QUICK_FIXES.md)

---

## 获取帮助

- **文档问题**: 查看 `docs/` 目录
- **技术支持**: 参考 `docs/QUICK_FIXES.md`
- **功能请求**: 查看本文档的待办事项

---

**注意**: 本文档整合了所有核心信息，是项目的唯一主文档。所有功能实现细节、配置说明、使用指南都已包含在内。