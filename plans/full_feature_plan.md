# 全功能开发实施计划

> 基于现有架构的全面功能升级计划
> 创建日期: 2026-01-29

## 现有架构分析

### 已存在的组件
| 组件 | 路径 | 状态 |
|------|------|------|
| Policy Agent | `tradingagents/agents/analysts/policy_agent.py` | ✅ 存在 |
| Sentiment Agent | `tradingagents/agents/analysts/sentiment_agent.py` | ✅ 存在 |
| 北向资金路由 | `api/routes/north_money.py` | ✅ 存在 |
| 龙虎榜路由 | `api/routes/lhb.py` | ✅ 存在 |
| 解禁路由 | `api/routes/jiejin.py` | ✅ 存在 |
| NorthMoneyPanel | `components/NorthMoneyPanel.tsx` | ✅ 存在 |
| TradingViewChart | `components/TradingViewChart.tsx` | ✅ 存在 |
| TypewriterText | `components/TypewriterText.tsx` | ✅ 存在 |

### 数据流架构
```
MarketRouter (services/data_router.py)
    ↓ 市场识别 (.SH/.SZ → CN, .HK → HK, other → US)
    ↓ 降级机制 (AkShare → yfinance → Alpha Vantage)

TradingAgents Interface (tradingagents/dataflows/interface.py)
    ↓ 按类别路由 (core_stock_apis, technical_indicators, fundamental_data, news_data, search_data)
    ↓ Vendor 降级 (primary vendors → fallback vendors)
```

---

## 开发阶段总览

| 阶段 | 功能数 | 预估工作量 | 优先级 |
|------|--------|------------|--------|
| P2: 市场差异化与数据加固 | 4 | 2 周 | 高 |
| P3: 信任与洞察 | 2 | 3 周 | 中 |
| P4: 智能进化 | 2 | 2 周 | 中 |
| P5: 前端体验 | 3 | 1.5 周 | 低 |

**推荐开发顺序**: P2.3 → P5.2 → P2.1 → P2.2 → P2.4 → P5.1 → P5.3 → P3 → P4

---

## P2: 市场差异化与数据加固

### P2.1 A股政策 Agent 增强
**目标**: 强化现有 Policy Agent，增加更丰富的政策解读能力

**现状**: `policy_agent.py` 已存在，但功能较基础

**需要修改的文件**:
| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `tradingagents/agents/analysts/policy_agent.py` | 修改 | 增强 prompt，添加行业政策分析 |
| `tradingagents/agents/utils/policy_tools.py` | 新建 | 政策数据工具（政策搜索、行业规划解读） |
| `tradingagents/dataflows/policy_data.py` | 新建 | 政策数据源适配器（国务院、证监会、发改委） |
| `config/prompts.yaml` | 修改 | 添加政策分析专用 prompt |

**新增工具函数**:
```python
# policy_tools.py
def search_recent_policies(industry: str, days: int = 30) -> List[PolicyItem]
def analyze_policy_impact(policy_text: str, symbol: str) -> PolicyImpact
def get_industry_planning(industry: str) -> IndustryPlan
```

**预估工作量**: 中 (3-4 天)

---

### P2.2 北向资金/龙虎榜数据集成到 Agent 分析
**目标**: 将已有的北向资金、龙虎榜数据注入到分析流程中

**现状**:
- API 路由已存在 (`north_money.py`, `lhb.py`)
- 前端展示组件已存在 (`NorthMoneyPanel.tsx`)
- 但**未集成到 Agent 分析流程**

**需要修改的文件**:
| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `tradingagents/agents/utils/china_market_tools.py` | 新建 | 封装北向/龙虎榜为 LangChain Tools |
| `tradingagents/agents/analysts/fundamentals_analyst.py` | 修改 | A股时注入北向/龙虎榜数据 |
| `tradingagents/agents/utils/agent_states.py` | 修改 | 添加 `china_flow_data` 字段 |
| `tradingagents/graph/setup.py` | 修改 | 条件性启用 A 股特色数据工具 |
| `services/synthesizer.py` | 修改 | 合成 JSON 时包含 A 股数据 |

**新增工具函数**:
```python
# china_market_tools.py
def get_north_money_flow(date: str = None) -> NorthMoneyFlow
def get_north_money_top_stocks(direction: str = "buy") -> List[TopStock]
def get_lhb_stocks(date: str = None) -> List[LHBStock]
def check_stock_in_lhb(symbol: str, days: int = 5) -> Optional[LHBRecord]
```

**预估工作量**: 中 (3-4 天)

---

### P2.3 AkShare 鲁棒性增强 ⭐ 推荐优先
**目标**: 增加 A 股数据源的自动重试和备用源切换

**现状**: `interface.py` 有基础降级，但缺乏:
- 指数级退避重试
- 请求频率限制
- 连接池管理
- 健康检查熔断

**需要修改的文件**:
| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `tradingagents/dataflows/interface.py` | 修改 | 添加重试装饰器和熔断器 |
| `tradingagents/dataflows/retry_utils.py` | 新建 | 重试、熔断、限流工具 |
| `tradingagents/dataflows/akshare_robust.py` | 新建 | AkShare 增强封装 |
| `services/data_router.py` | 修改 | 添加相同机制 |

**核心实现**:
```python
# retry_utils.py
class CircuitBreaker:
    """熔断器: 连续失败 N 次后短路 M 秒"""

class RateLimiter:
    """令牌桶限流器: 控制请求频率"""

def retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=30.0):
    """指数退避重试装饰器"""
```

**预估工作量**: 小 (1-2 天)

---

### P2.4 美股宏观对冲逻辑
**目标**: 强化利率、非农数据对美股估值的影响分析

**需要修改的文件**:
| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `tradingagents/agents/analysts/macro_analyst.py` | 修改 | 增强美股宏观分析 |
| `tradingagents/dataflows/fred_data.py` | 新建 | FRED 经济数据接口 |
| `tradingagents/agents/utils/macro_tools.py` | 新建 | 宏观经济工具 |
| `config/prompts.yaml` | 修改 | 美股宏观分析 prompt |

**新增工具函数**:
```python
# macro_tools.py
def get_fed_rate_history(months: int = 12) -> List[RatePoint]
def get_nonfarm_payroll(months: int = 6) -> List[NFPData]
def get_cpi_data(months: int = 12) -> List[CPIData]
def calculate_rate_sensitivity(symbol: str) -> RateSensitivity
```

**新增环境变量**:
```
FRED_API_KEY=xxx  # 美联储经济数据 API
```

**预估工作量**: 中 (3-4 天)

---

## P3: 信任与洞察

### P3.1 BacktestAgent 回测专家
**目标**: 实现历史回测和胜率统计，增强用户对信号的信任

**需要新建的文件**:
| 文件 | 说明 |
|------|------|
| `tradingagents/agents/analysts/backtest_agent.py` | 回测 Agent 主体 |
| `tradingagents/dataflows/backtest_engine.py` | 回测引擎（基于 backtrader） |
| `services/backtest_service.py` | 回测服务层 |
| `api/routes/backtest.py` | 回测 API 路由 |
| `db/models.py` | 添加 `BacktestResult` 模型 |
| `components/BacktestPanel.tsx` | 前端回测面板 |

**核心功能**:
```python
# backtest_agent.py
class BacktestAgent:
    def backtest_signal(
        self,
        symbol: str,
        signal: SignalType,
        entry_price: float,
        target_price: float,
        stop_loss: float,
        lookback_days: int = 252
    ) -> BacktestResult

    def calculate_win_rate(self, symbol: str, signal_type: str) -> WinRateStats
    def compare_with_benchmark(self, symbol: str, benchmark: str = "SPY") -> ComparisonResult
```

**API 端点**:
| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/backtest/run` | 运行回测 |
| GET | `/api/backtest/history/{symbol}` | 历史回测记录 |
| GET | `/api/backtest/win-rate/{symbol}` | 胜率统计 |

**前端组件**:
- 回测结果图表（收益曲线、回撤）
- 胜率统计仪表盘
- 历史信号准确率追踪

**预估工作量**: 大 (5-7 天)

---

### P3.2 SentimentAgent 舆情分析师
**目标**: 监控 Reddit/Twitter/东财股吧的舆情

**需要新建的文件**:
| 文件 | 说明 |
|------|------|
| `tradingagents/dataflows/social_sentiment.py` | 社交媒体数据聚合 |
| `tradingagents/dataflows/eastmoney_guba.py` | 东财股吧爬虫 |
| `tradingagents/dataflows/twitter_api.py` | Twitter/X API 封装 |
| `tradingagents/agents/analysts/social_sentiment_agent.py` | 舆情 Agent |
| `services/sentiment_aggregator.py` | 舆情聚合服务 |
| `api/routes/sentiment.py` | 舆情 API |
| `components/SentimentPanel.tsx` | 舆情面板 |

**数据源优先级**:
| 市场 | 主数据源 | 备选数据源 |
|------|----------|------------|
| CN | 东财股吧、雪球 | 微博财经 |
| US | Reddit (r/wallstreetbets)、Twitter | StockTwits |
| HK | 雪球港股、富途牛牛 | Reddit |

**核心功能**:
```python
# social_sentiment_agent.py
def analyze_social_sentiment(symbol: str, market: str) -> SocialSentiment:
    """
    Returns:
        overall_sentiment: Bullish/Bearish/Neutral
        fomo_level: 0-100
        fud_level: 0-100
        hot_topics: List[str]
        influencer_mentions: List[InfluencerMention]
    """
```

**预估工作量**: 大 (5-7 天)

---

## P4: 智能进化

### P4.1 反思闭环 - Agent 自我优化
**目标**: Agent 定期回顾预测准确率并自动微调 Prompt

**需要修改/新建的文件**:
| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `tradingagents/graph/reflection.py` | 修改 | 增强反思逻辑 |
| `services/prompt_optimizer.py` | 新建 | Prompt 自动优化服务 |
| `services/accuracy_tracker.py` | 新建 | 预测准确率追踪 |
| `db/models.py` | 修改 | 添加 `PredictionOutcome` 模型 |
| `api/routes/reflection.py` | 新建 | 反思 API |

**核心机制**:
```python
# prompt_optimizer.py
class PromptOptimizer:
    def analyze_prediction_errors(self, agent_key: str, days: int = 30) -> ErrorAnalysis
    def suggest_prompt_improvements(self, agent_key: str, errors: ErrorAnalysis) -> List[PromptSuggestion]
    def auto_tune_prompt(self, agent_key: str, dry_run: bool = True) -> TuningResult
```

**工作流程**:
1. 每日收盘后收集实际价格
2. 对比历史预测信号
3. 计算各 Agent 准确率
4. 识别系统性偏差（如总是过于乐观）
5. 生成 Prompt 调整建议
6. 人工审核后应用

**预估工作量**: 中 (4-5 天)

---

### P4.2 多模型赛马
**目标**: 多模型共识机制，自动选择表现最优模型

**需要修改/新建的文件**:
| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `tradingagents/graph/trading_graph.py` | 修改 | 支持多模型并行 |
| `services/model_racing.py` | 新建 | 模型赛马服务 |
| `services/consensus_engine.py` | 新建 | 共识引擎 |
| `db/models.py` | 修改 | 添加 `ModelPerformance` 模型 |
| `api/routes/model_racing.py` | 新建 | 赛马 API |

**核心机制**:
```python
# model_racing.py
class ModelRacing:
    def run_parallel_analysis(
        self,
        symbol: str,
        models: List[str] = ["gpt-4o", "claude-3-sonnet", "gemini-pro"]
    ) -> List[AnalysisResult]

    def calculate_consensus(self, results: List[AnalysisResult]) -> ConsensusResult
    def track_model_accuracy(self, model: str, prediction: str, actual: str) -> None
    def get_best_model(self, task_type: str, lookback_days: int = 30) -> str
```

**共识算法**:
- 加权投票（根据历史准确率）
- 信心度加权平均
- 异常值检测（排除极端偏离）

**预估工作量**: 中 (4-5 天)

---

## P5: 前端体验

### P5.1 TradingView 专业图表
**目标**: 优化现有 TradingViewChart 组件，添加更多专业功能

**现状**: `TradingViewChart.tsx` 已存在，使用 `lightweight-charts`

**需要修改的文件**:
| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `components/TradingViewChart.tsx` | 修改 | 添加技术指标、画图工具 |
| `components/ChartToolbar.tsx` | 新建 | 图表工具栏 |
| `hooks/useChartIndicators.ts` | 新建 | 技术指标计算 hook |
| `services/api.ts` | 修改 | 添加历史数据 API |

**新增功能**:
- [ ] 多时间周期切换（1D/1W/1M/1Y）
- [ ] 技术指标叠加（MA/EMA/BOLL/MACD/RSI）
- [ ] 价格预警线标注
- [ ] 支撑/阻力位可视化
- [ ] 成交量柱状图
- [ ] 全屏模式

**预估工作量**: 中 (3-4 天)

---

### P5.2 流式打字机效果 ⭐ 推荐优先
**目标**: SSE 实时文本流式渲染，提升分析过程的交互感

**现状**:
- `TypewriterText.tsx` 已存在（静态文本打字效果）
- SSE 已用于分析进度推送
- 但分析报告是**一次性**返回，非流式

**需要修改的文件**:
| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `api/sse.py` | 修改 | 支持文本流式推送 |
| `api/routes/analyze.py` | 修改 | Agent 输出流式化 |
| `tradingagents/graph/trading_graph.py` | 修改 | 添加流式回调 |
| `services/api.ts` | 修改 | 处理流式 SSE 事件 |
| `components/StockDetailModal.tsx` | 修改 | 流式渲染分析文本 |
| `hooks/useStreamingAnalysis.ts` | 新建 | 流式分析 hook |

**SSE 事件格式**:
```typescript
// 新增事件类型
type SSEEvent =
  | { type: 'stage_start', stage: string }
  | { type: 'text_chunk', stage: string, text: string }  // 新增
  | { type: 'stage_complete', stage: string, data: any }
  | { type: 'analysis_complete', data: AgentAnalysis }
```

**预估工作量**: 小 (2-3 天)

---

### P5.3 高保真 TTS 语音合成
**目标**: 集成 OpenAI/Gemini TTS 替换浏览器原生语音

**需要修改/新建的文件**:
| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `services/tts_service.py` | 新建 | TTS 服务（OpenAI/Gemini） |
| `api/routes/tts.py` | 新建 | TTS API 路由 |
| `services/api.ts` | 修改 | 添加 TTS API 调用 |
| `components/AudioBriefing.tsx` | 新建 | 音频播报组件 |
| `hooks/useTTS.ts` | 新建 | TTS hook |

**TTS 提供商配置**:
```python
# tts_service.py
class TTSService:
    providers = {
        "openai": OpenAITTS,      # tts-1, tts-1-hd
        "gemini": GeminiTTS,      # gemini-2.5-flash-preview-tts
        "edge": EdgeTTS,          # 免费备选
    }

    async def synthesize(
        self,
        text: str,
        voice: str = "alloy",
        provider: str = "openai"
    ) -> bytes
```

**API 端点**:
| 方法 | 端点 | 功能 |
|------|------|------|
| POST | `/api/tts/synthesize` | 文本转语音 |
| GET | `/api/tts/voices` | 获取可用声音列表 |

**预估工作量**: 小 (2-3 天)

---

## 实施时间线

```
Week 1:
├── Day 1-2: P2.3 AkShare 鲁棒性
├── Day 3-4: P5.2 流式打字机效果
└── Day 5:   P5.3 高保真 TTS

Week 2:
├── Day 1-2: P2.1 A股政策 Agent
├── Day 3-4: P2.2 北向/龙虎榜集成
└── Day 5:   P2.4 美股宏观对冲

Week 3:
├── Day 1-3: P5.1 TradingView 优化
├── Day 4-5: P4.1 反思闭环 (Part 1)

Week 4:
├── Day 1-2: P4.1 反思闭环 (Part 2)
├── Day 3-5: P4.2 多模型赛马

Week 5-6:
├── P3.1 BacktestAgent (5-7 days)

Week 7-8:
└── P3.2 SentimentAgent (5-7 days)
```

---

## 依赖项新增

### Python 依赖
```toml
# pyproject.toml [project.dependencies]
tenacity = ">=8.2.0"          # 重试库
aiolimiter = ">=1.1.0"        # 异步限流
fredapi = ">=0.5.0"           # FRED 经济数据
edge-tts = ">=6.1.0"          # Edge TTS (免费备选)
```

### 环境变量新增
```bash
# .env
FRED_API_KEY=xxx              # 美联储数据
TWITTER_BEARER_TOKEN=xxx      # Twitter API (可选)
TTS_PROVIDER=openai           # TTS 提供商
```

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| AkShare 接口变更 | 高 | 版本锁定 + 单元测试覆盖 |
| 社交媒体 API 限制 | 中 | 多数据源降级 + 缓存 |
| LLM API 成本 | 中 | Token 监控 + 模型分层 |
| 回测数据质量 | 中 | 多数据源交叉验证 |
