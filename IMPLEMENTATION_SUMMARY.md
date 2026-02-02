# Stock Agents Monitor - 项目实施总结

> 最后更新: 2026-02-02
> 状态: ✅ 生产就绪（SubGraph 架构建议灰度测试）

---

## 📊 项目概览

**Stock Agents Monitor** 是基于 TradingAgents 框架的专业级金融情报监控系统，通过多 Agent 协作（Bull vs Bear 对抗性辩论）对 A股/港股/美股 进行深度分析。

### 核心统计

| 指标 | 数值 |
|------|------|
| **后端路由** | 31 个 |
| **后端服务** | 34 个 |
| **AI Agent** | 18 个 |
| **前端页面** | 12 个 |
| **前端组件** | 33 个 |
| **前端 Hooks** | 20 个 |
| **TypeScript 类型** | 801 行 |
| **总代码行数** | ~40,000 行 |

---

## ✅ 已完成功能

### 1. 核心分析能力

- **多 Agent 协作**: 11 个分析师 + Bull/Bear 对抗辩论 + 三方风险评估
- **Planner Agent**: 自适应分析师选择，根据股票特征动态路由
- **分析分级 (L1/L2)**: L1 快速扫描 (15-20s) / L2 深度研究 (30-60s)
- **SubGraph 架构**: 模块化 Analyst/Debate/Risk 子图（实验性）

### 2. 多市场支持

- **智能数据路由 (MarketRouter)**: 根据 symbol 后缀自动选择数据源
- **A股特色功能**: 龙虎榜、北向资金、限售解禁、政策-行业映射、央行 NLP
- **跨资产分析**: 黄金/原油/债市联动监控
- **数据质量校验 (DataValidator)**: 跨源校验，低质量数据标记注入 Agent

### 3. 记忆与反思系统

- **分层记忆**: ChromaDB 向量数据库，支持按 symbol/宏观周期/技术形态检索
- **自动反思**: Agent 决策后自动生成反思，注入后续分析
- **准确率追踪**: 历史预测准确率统计

### 4. 认证与安全

- **三重认证**: JWT + OAuth 2.0 (Google/GitHub) + WebAuthn/Passkey
- **动态 AI 配置**: 通过 UI 动态配置 LLM 提供商，无需重启
- **API 密钥加密**: Fernet 对称加密存储

### 5. 任务处理

- **开发模式**: FastAPI BackgroundTasks
- **生产模式**: Redis Stream + Worker 水平扩展
- **SSE 实时推送**: Agent 分析进度实时推送前端

### 6. 前端体验

- **12 页面**: Dashboard、Login、Register、Settings、AIConfig、Prompts、Scheduler、Macro、News、ChinaMarket、Portfolio、NotFound
- **TradingView 图表**: Lightweight Charts 集成
- **Gemini TTS**: 音频简报生成
- **Agentic UI**: 根据分析结论动态展示

### 7. 可观测性

- **结构化日志**: JSON 格式 + request_id 追踪
- **LangSmith 集成**: Agent 执行链路可视化
- **健康检查**: 多层级健康探针（liveness/readiness/详细报告）
- **API 指标**: 请求统计、错误率、响应时间

---

## 🏗️ 技术架构

### 后端 (Python 3.10 + FastAPI)

```
apps/server/
├── api/routes/         # 31 个业务路由
├── services/           # 34 个服务模块
├── workers/            # Redis Stream Worker
├── config/             # Pydantic Settings + OAuth + Prompts
├── db/                 # SQLModel ORM
└── tradingagents/
    ├── agents/         # 18 个 Agent
    ├── graph/          # LangGraph 编排
    │   └── subgraphs/  # SubGraph 模块
    └── dataflows/      # 数据源适配器
```

### 前端 (React 19 + Vite)

```
apps/client/
├── pages/              # 12 个页面组件
├── components/         # 33 个 UI 组件
├── hooks/              # 20 个 TanStack Query Hooks
├── services/api.ts     # 统一 API 层
└── types.ts            # 801 行类型定义
```

### 数据流

```
前端触发 → POST /api/analyze/{symbol} → 返回 task_id
    ↓
任务入队: BackgroundTask (dev) / Redis Stream (prod)
    ↓
TradingAgentsGraph (LangGraph StateGraph)
    ↓
  ├─ Planner Agent → 自适应选择分析师
  ├─ Analyst SubGraph → 并行执行分析师
  ├─ Debate SubGraph → Bull vs Bear 辩论
  ├─ Risk SubGraph → 三方风险辩论
  └─ ResponseSynthesizer → Markdown → JSON
    ↓
SSE 实时推送 → 前端 useStreamingAnalysis() → TanStack Query 缓存
```

---

## 📈 性能指标

### 分析速度

| 场景 | 耗时 |
|------|------|
| L1 快速扫描 | 15-20 秒 |
| L2 完整分析 | 30-60 秒 |

### 并发能力

| 模式 | 并发任务 |
|------|----------|
| BackgroundTasks (开发) | ~4 |
| Redis Stream + Workers (生产) | 理论无限（水平扩展） |

---

## 🔧 配置选项

### 核心配置 (`tradingagents/default_config.py`)

```python
DEFAULT_CONFIG = {
    "llm_provider": "openai",
    "deep_think_llm": "o4-mini",
    "quick_think_llm": "gpt-4o-mini",
    "use_planner": True,
    "analysis_level": "L2",
    "use_subgraphs": False,  # 实验性
    "max_debate_rounds": 1,
    "max_risk_discuss_rounds": 1,
}
```

### 环境变量分类

| 类别 | 变量数量 |
|------|----------|
| LLM API Keys | 3 |
| 数据源 API Keys | 3 |
| 数据库配置 | 7 |
| 认证配置 | 12 |
| 任务队列配置 | 2 |
| Scout Agent 配置 | 4 |
| LangSmith 配置 | 4 |

---

## 📚 文档清单

| 文档 | 位置 | 说明 |
|------|------|------|
| CLAUDE.md | 根目录 | AI 编码指引，核心参考文档 |
| docs/ARCH.md | docs/ | 系统架构设计 |
| docs/PRD.md | docs/ | 产品需求文档 |
| docs/CONTRIB.md | docs/ | 贡献指南 |
| docs/RUNBOOK.md | docs/ | 运维手册 |

---

## 🚀 部署指南

### 快速启动

```bash
# 1. 克隆仓库
git clone <repo-url>
cd HeavenlyMechanicPavilion

# 2. 配置环境变量
cp apps/server/.env.example apps/server/.env
# 编辑 .env 配置 API 密钥

# 3. 启动服务
docker compose up -d

# 4. 验证
curl http://localhost:8000/health
```

### 生产环境

```bash
# 启用 PostgreSQL + Redis + 任务队列
DATABASE_MODE=postgresql
REDIS_URL=redis://localhost:6379
USE_TASK_QUEUE=true

# 启动多个 Worker
python -m workers.analysis_worker --name worker-1 &
python -m workers.analysis_worker --name worker-2 &
```

---

## 🔮 后续规划

### 短期 (P1)

- [ ] 测试覆盖率提升（当前 6 个测试文件）
- [ ] Swagger/OpenAPI 文档自动生成
- [ ] 前端 E2E 测试（Playwright）

### 中期 (P2)

- [ ] SubGraph 架构生产验证
- [ ] 日志聚合（ELK/Loki）
- [ ] 数据库迁移（Alembic）
- [ ] 前端 Bundle 优化（代码分割）

### 长期 (P3)

- [ ] 多模态分析（电话会录音、财报图表）
- [ ] 执行助手（模拟盘/实盘对接）
- [ ] 智能推送（Telegram/微信机器人）
- [ ] AI 播客生成

---

## 📝 变更日志

### 2026-02-02

- 📄 全面更新所有文档，反映当前代码状态
- 🔧 补充缺失的路由、服务、环境变量文档
- 📊 添加项目统计数据

### 2026-01-31

- ✅ Phase 1: Scout → Planner 改造，API 路径修复
- ✅ Phase 2: L1/L2 分析分级，Redis Stream 任务队列
- ✅ Phase 3: A股特色功能（龙虎榜/北向/解禁）
- ✅ Phase 4: DataValidator 跨源校验
- ✅ Phase 5: SubGraph 架构重构

### 2026-01-28

- ✅ 动态 AI 配置系统
- ✅ 三重认证（JWT/OAuth/Passkey）
- ✅ 健康监控系统

---

**项目状态**: ✅ 生产就绪
**SubGraph 架构**: ⚠️ 建议灰度测试后再全量启用
**文档同步**: ✅ 2026-02-02 全面更新
