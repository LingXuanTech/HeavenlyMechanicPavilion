# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

**Stock Agents Monitor** - 基于 TradingAgents 框架的专业级金融情报监控系统，通过多 Agent 协作（Bull vs Bear 对抗性辩论）对股票市场进行深度分析，并以实时大屏形式提供决策支持。支持 A股/港股/美股三大市场。

## 开发命令

### 前端 (apps/client)
```bash
cd apps/client
npm install           # 安装依赖
npm run dev           # 启动开发服务器 (http://localhost:3000)
npm run build         # 生产构建
npm run preview       # 预览构建结果
```

### 后端 (apps/server)
```bash
cd apps/server
pip install -r requirements.txt   # 安装依赖（或 uv sync）
python main.py                    # 启动 FastAPI 服务 (http://localhost:8000)
uvicorn main:app --reload         # 热重载开发模式
python -m cli.main                # 启动 CLI 版本
pytest                            # 运行测试
pytest tests/test_xxx.py -v       # 运行单个测试文件
```

### Docker
```bash
docker build -t stock-agents apps/server
docker run -p 8000:8000 stock-agents
```

## 代码架构

### 整体结构
```
apps/
├── client/          # React 19 + Vite 前端
│   ├── components/  # UI 组件
│   ├── services/    # API 调用层
│   └── types.ts     # TypeScript 类型定义
│
└── server/          # FastAPI + Python 后端
    ├── api/routes/  # REST API 路由
    ├── services/    # 业务服务层
    ├── db/          # SQLModel ORM
    ├── config/      # 配置管理
    └── tradingagents/  # 核心 AI Agent 框架
        ├── graph/      # LangGraph 工作流编排
        ├── agents/     # Agent 实现
        └── dataflows/  # 数据源适配器
```

### 核心数据流

```
前端点击分析 → POST /api/analyze/{symbol}
    ↓
TradingAgentsGraph.propagate() 执行 LangGraph 工作流
    ↓
  ┌─ Analyst Team (技术/基本面/新闻/情绪分析师)
  │     ↓ stage_analyst 事件
  ├─ Researchers Debate (Bull vs Bear 对抗辩论)
  │     ↓ stage_debate 事件
  ├─ Risk Manager (风险评估，可一票否决)
  │     ↓ stage_risk 事件
  └─ Fund Manager (最终决策)
        ↓ stage_final 事件 + 完整 AgentAnalysis JSON
    ↓
SSE 实时推送到前端 → GET /api/analyze/stream/{task_id}
```

### 智能数据路由 (MarketRouter)

```
symbol 后缀 → 市场识别 → 数据源选择
├── .SH / .SZ → CN (A股) → AkShare
├── .HK → HK (港股) → yfinance / AkShare
└── 其他 → US (美股) → yfinance / Alpha Vantage
```

## 关键文件

### 前端
- `apps/client/App.tsx` - 主应用组件，状态管理和事件处理
- `apps/client/types.ts` - 核心类型定义 (AgentAnalysis, ResearcherDebate, etc.)
- `apps/client/services/api.ts` - REST/SSE API 调用
- `apps/client/components/StockDetailModal.tsx` - 分析结果详情弹窗

### 后端
- `apps/server/main.py` - FastAPI 应用入口
- `apps/server/api/routes/analyze.py` - 分析 API（触发 Agent 工作流，SSE 推送）
- `apps/server/services/data_router.py` - 智能数据路由（多市场适配）
- `apps/server/services/synthesizer.py` - 多 Agent 报告合成为前端 JSON
- `apps/server/tradingagents/graph/trading_graph.py` - LangGraph 核心编排
- `apps/server/config/prompts.yaml` - Agent Prompt 配置
- `apps/server/config/settings.py` - Pydantic Settings 配置

## 技术栈

### 前端
- React 19 + TypeScript 5.8
- Vite 6.2 (构建)
- Recharts (图表)
- Tailwind CSS (样式)
- @google/genai (Gemini API)

### 后端
- Python 3.10+ / FastAPI
- LangGraph (Agent 编排)
- SQLModel (ORM)
- ChromaDB (向量存储)
- yfinance / AkShare / Alpha Vantage (数据源)
- APScheduler (定时任务)
- SSE-Starlette (实时推送)

### LLM 提供商
- **Google Gemini** (推荐): gemini-3-pro-preview, gemini-3-flash-preview
- **OpenAI** (备选): gpt-4o, gpt-4o-mini, o4-mini

## 环境变量

### 前端 (.env)
```
VITE_API_URL=http://localhost:8000/api
GEMINI_API_KEY=your_key
```

### 后端 (.env)
```
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIza...
ALPHA_VANTAGE_API_KEY=...
DATABASE_URL=sqlite:///./db/trading.db
CHROMA_DB_PATH=./db/chroma
```

## API 端点

| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/analyze/{symbol}` | 触发 Agent 分析 |
| GET | `/api/analyze/stream/{task_id}` | SSE 分析进度流 |
| GET/POST/DEL | `/api/watchlist/` | 关注列表 CRUD |
| GET | `/api/market/price/{symbol}` | 实时价格 |
| GET | `/api/market/history/{symbol}` | K 线历史 |
| GET | `/api/discover/?query=...` | AI Scout 发现 |
| GET/POST | `/api/chat/{thread_id}` | 对话接口 |

## 架构模式

- **Multi-Agent 对抗**: Bull/Bear Researcher 辩论减少 AI 幻觉
- **SSE 实时推送**: 前后端工作流状态同步
- **数据路由适配器**: 统一处理三大市场差异
- **Prompt 热加载**: YAML 配置支持运行时更新

## 文档

- `docs/ARCH.md` - 系统架构设计
- `docs/PRD.md` - 产品需求文档
- `plans/implementation_plan.md` - 实现计划
