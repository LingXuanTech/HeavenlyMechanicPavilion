# Stock Agents Monitor - 下一步开发计划

> 生成日期: 2026-01-29
> 基于代码分析自动生成

---

## 执行摘要

本计划涵盖三个核心开发方向：**前端 UX 优化**、**新增 Agent**、**A 股深度适配**，预计总工时 3-4 周。

---

## 一、前端 UX 优化 (Week 1-2)

### 1.1 流式打字机效果

**目标**：SSE 消息逐字渲染，提升 AI 分析过程的沉浸感

**当前实现分析**：
- `apps/client/services/api.ts` 已实现完整的 SSE 客户端
- `apps/client/components/StockDetailModal.tsx` 消费 SSE 事件但一次性显示

**实现方案**：

```typescript
// apps/client/hooks/useTypewriter.ts (新建)
interface UseTypewriterOptions {
  speed?: number;        // 每字符延迟（ms），默认 30
  onComplete?: () => void;
}

export function useTypewriter(text: string, options?: UseTypewriterOptions) {
  const [displayedText, setDisplayedText] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  useEffect(() => {
    if (!text) return;
    setIsTyping(true);
    let index = 0;
    const interval = setInterval(() => {
      setDisplayedText(text.slice(0, index + 1));
      index++;
      if (index >= text.length) {
        clearInterval(interval);
        setIsTyping(false);
        options?.onComplete?.();
      }
    }, options?.speed ?? 30);

    return () => clearInterval(interval);
  }, [text]);

  return { displayedText, isTyping };
}
```

**改动文件**：
| 文件 | 改动 |
|-----|------|
| `hooks/useTypewriter.ts` | 新建 - 打字机效果 Hook |
| `components/StockDetailModal.tsx:400-500` | 集成打字机效果到推理过程展示 |
| `components/AnalysisProgress.tsx` | 新建 - 抽取分析进度组件 |

**验收标准**：
- [ ] SSE `stage_*` 事件触发逐字渲染
- [ ] 支持暂停/继续打字
- [ ] 渲染速度可配置

---

### 1.2 TradingView 图表集成

**目标**：替换基础 `StockChart.tsx` 为专业级金融图表

**技术选型**：`lightweight-charts` (TradingView 官方轻量库)

**实现方案**：

```bash
# 安装依赖
cd apps/client
npm install lightweight-charts
```

```typescript
// apps/client/components/TradingViewChart.tsx (新建)
import { createChart, ColorType, IChartApi } from 'lightweight-charts';

interface TradingViewChartProps {
  data: KlineData[];
  symbol: string;
  height?: number;
  showVolume?: boolean;
  indicators?: ('ma20' | 'ma60' | 'bollinger')[];
}

export function TradingViewChart({
  data,
  symbol,
  height = 400,
  showVolume = true,
  indicators = ['ma20']
}: TradingViewChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: '#1a1a2e' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: '#2B2B43' },
        horzLines: { color: '#2B2B43' },
      },
      width: chartContainerRef.current.clientWidth,
      height,
    });

    // 蜡烛图
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });
    candlestickSeries.setData(formatCandleData(data));

    // 成交量
    if (showVolume) {
      const volumeSeries = chart.addHistogramSeries({
        color: '#26a69a',
        priceFormat: { type: 'volume' },
        priceScaleId: '',
      });
      volumeSeries.setData(formatVolumeData(data));
    }

    chartRef.current = chart;

    return () => chart.remove();
  }, [data, height, showVolume]);

  return <div ref={chartContainerRef} className="w-full" />;
}
```

**改动文件**：
| 文件 | 改动 |
|-----|------|
| `components/TradingViewChart.tsx` | 新建 - TradingView 图表组件 |
| `components/StockChart.tsx` | 重构为 wrapper，默认使用 TradingView |
| `components/StockDetailModal.tsx:89-120` | 切换到新图表组件 |
| `types.ts` | 补充图表相关类型定义 |

**验收标准**：
- [ ] 支持 K 线 + 成交量双面板
- [ ] 支持 MA20/MA60/布林带叠加
- [ ] 支持缩放、十字光标、价格标签
- [ ] 响应式宽度自适应

---

### 1.3 TTS 播放集成

**目标**：将 `anchor_script` 播稿转为语音播报

**当前实现**：
- 后端 `FinalAnalysisOutput.anchor_script` 已生成播稿
- 前端有 `Volume2/VolumeX` 图标但未实现播放

**实现方案**：

```typescript
// apps/client/hooks/useTTS.ts (新建)
interface UseTTSOptions {
  apiEndpoint?: string;  // 默认使用 Gemini TTS
  voice?: string;
  rate?: number;
}

export function useTTS(options?: UseTTSOptions) {
  const [isPlaying, setIsPlaying] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const speak = useCallback(async (text: string) => {
    setIsPlaying(true);

    // 方案 A: 调用后端 TTS API
    const response = await fetch('/api/tts', {
      method: 'POST',
      body: JSON.stringify({ text, voice: options?.voice }),
    });
    const audioBlob = await response.blob();
    const audioUrl = URL.createObjectURL(audioBlob);

    audioRef.current = new Audio(audioUrl);
    audioRef.current.onended = () => setIsPlaying(false);
    await audioRef.current.play();
  }, [options]);

  const pause = () => { /* ... */ };
  const resume = () => { /* ... */ };
  const stop = () => { /* ... */ };

  return { speak, pause, resume, stop, isPlaying, isPaused };
}
```

**后端 TTS API** (需新增):
```python
# apps/server/api/routes/tts.py (新建)
from fastapi import APIRouter
from google.cloud import texttospeech  # 或 Gemini API

router = APIRouter(prefix="/tts", tags=["TTS"])

@router.post("/")
async def synthesize_speech(request: TTSRequest):
    """文本转语音"""
    # 调用 Gemini/Google TTS API
    audio_content = await generate_tts(request.text, request.voice)
    return Response(content=audio_content, media_type="audio/mpeg")
```

**改动文件**：
| 文件 | 改动 | 位置 |
|-----|------|------|
| `hooks/useTTS.ts` | 新建 - TTS Hook | 前端 |
| `components/StockDetailModal.tsx` | 集成 TTS 播放控制 | 前端 |
| `api/routes/tts.py` | 新建 - TTS 端点 | 后端 |
| `main.py` | 注册 TTS 路由 | 后端 |

**验收标准**：
- [ ] 点击播放按钮朗读 `anchor_script`
- [ ] 支持暂停/继续/停止
- [ ] 播放进度条可视化
- [ ] 支持多种音色选择

---

## 二、新增 Agent (Week 2-3)

### 2.1 SentimentAgent - 舆情分析师

**职责**：分析社交媒体散户情绪，提供反向指标参考

**数据源**：
- Reddit (r/wallstreetbets, r/stocks)
- Twitter/X 财经话题
- StockTwits

**输出结构**：
```python
# apps/server/tradingagents/agents/utils/output_schemas.py (扩展)
class SentimentAgentOutput(BaseModel):
    """Sentiment Agent 结构化输出"""
    summary: str = Field(description="舆情分析总结")

    # 散户情绪指数 (-100 到 100)
    retail_sentiment_score: int = Field(ge=-100, le=100)

    # 情绪来源分布
    sentiment_by_source: Dict[str, int] = Field(
        description="各平台情绪分布",
        examples=[{"reddit": 75, "twitter": 60, "stocktwits": 80}]
    )

    # 热门讨论
    hot_discussions: List[dict] = Field(
        description="热门讨论话题",
        examples=[{"topic": "NVDA earnings", "sentiment": "Bullish", "volume": 1200}]
    )

    # 散户 vs 机构背离指标
    retail_institutional_divergence: Literal["Aligned", "Divergent", "Strongly Divergent"] = Field(
        description="散户与机构情绪背离程度"
    )

    # FOMO/FUD 指标
    fomo_level: int = Field(description="FOMO 程度 0-100", ge=0, le=100)
    fud_level: int = Field(description="FUD 程度 0-100", ge=0, le=100)

    # 信号
    signal: Literal["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"]
    confidence: int = Field(ge=0, le=100)
```

**实现文件**：
```
apps/server/tradingagents/agents/analysts/sentiment_agent.py (新建)
apps/server/tradingagents/dataflows/reddit_data.py (新建)
apps/server/tradingagents/dataflows/twitter_data.py (新建)
```

**LangGraph 集成**：
- 添加到 `selected_analysts` 选项
- 并行执行于其他分析师

---

### 2.2 PolicyAgent - A 股政策分析师

**职责**：解读中国财政/货币政策对 A 股的影响

**数据源**：
- 央行公告 (PBOC)
- 财政部政策
- 发改委产业政策
- 证监会监管动态

**输出结构**：
```python
class PolicyAnalystOutput(BaseModel):
    """Policy Analyst 结构化输出（A 股专用）"""
    summary: str = Field(description="政策分析总结")

    # 政策环境
    policy_environment: Literal["Supportive", "Neutral", "Restrictive"] = Field(
        description="当前政策环境对该行业/股票的影响"
    )

    # 相关政策列表
    relevant_policies: List[dict] = Field(
        description="相关政策",
        examples=[{
            "title": "央行降准0.5个百分点",
            "date": "2026-01-15",
            "impact": "Positive",
            "affected_sectors": ["银行", "地产"]
        }]
    )

    # 行业政策导向
    sector_policy_trend: Literal["鼓励", "中性", "限制"] = Field(
        description="所属行业的政策导向"
    )

    # 合规风险
    compliance_risks: List[str] = Field(description="潜在合规风险")

    # 政策催化剂
    policy_catalysts: List[dict] = Field(
        description="即将出台的政策催化剂",
        examples=[{"event": "两会", "date": "2026-03", "expected_impact": "Positive"}]
    )

    signal: Literal["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"]
    confidence: int = Field(ge=0, le=100)
```

**实现文件**：
```
apps/server/tradingagents/agents/analysts/policy_analyst.py (新建)
apps/server/tradingagents/dataflows/cn_policy_data.py (新建)
```

---

### 2.3 BacktestAgent - 回测分析师

**职责**：基于历史数据评估当前信号的可靠性

**功能**：
1. 历史相似形态匹配
2. 信号准确率统计
3. 策略回测模拟

**输出结构**：
```python
class BacktestAgentOutput(BaseModel):
    """Backtest Agent 结构化输出"""
    summary: str = Field(description="回测分析总结")

    # 历史相似形态
    similar_patterns: List[dict] = Field(
        description="历史相似形态",
        examples=[{
            "date": "2024-06-15",
            "pattern": "突破前高+放量",
            "subsequent_return": "+12.5%",
            "holding_days": 20
        }]
    )

    # 信号历史准确率
    signal_accuracy: dict = Field(
        description="当前信号的历史准确率",
        examples=[{
            "signal": "Strong Buy",
            "historical_occurrences": 15,
            "success_rate": 73.3,
            "avg_return": "+8.2%",
            "avg_holding_period": "15 days"
        }]
    )

    # 风险收益比历史
    historical_risk_reward: dict = Field(
        description="历史风险收益统计",
        examples=[{
            "win_rate": 65,
            "avg_win": "+10%",
            "avg_loss": "-5%",
            "max_drawdown": "-15%"
        }]
    )

    # 置信区间
    confidence_interval: dict = Field(
        description="预期收益置信区间",
        examples=[{"lower_95": -5, "upper_95": 15, "expected": 8}]
    )

    # 信号可靠性评分
    signal_reliability: int = Field(description="信号可靠性 0-100", ge=0, le=100)
    confidence: int = Field(ge=0, le=100)
```

**实现文件**：
```
apps/server/tradingagents/agents/analysts/backtest_agent.py (新建)
apps/server/services/backtest_service.py (新建)
```

---

### Agent 集成流程

修改 `apps/server/tradingagents/graph/setup.py`:

```python
def setup_graph(
    self,
    selected_analysts=["market", "social", "news", "fundamentals"],
    enable_sentiment=False,    # 新增
    enable_policy=False,       # 新增
    enable_backtest=False,     # 新增
):
    """Set up and compile the agent workflow graph."""

    # 动态添加 Agent 节点
    if enable_sentiment:
        sentiment_agent = create_sentiment_agent(self.quick_thinking_llm)
        workflow.add_node("sentiment_analyst", sentiment_agent)
        # 添加到并行路由

    if enable_policy:
        policy_agent = create_policy_agent(self.quick_thinking_llm)
        workflow.add_node("policy_analyst", policy_agent)

    if enable_backtest:
        backtest_agent = create_backtest_agent(self.quick_thinking_llm)
        # Backtest 在所有分析完成后执行
        workflow.add_node("backtest_analyst", backtest_agent)
```

---

## 三、A 股深度适配 (Week 3-4)

### 3.1 北向资金监控

**数据源**：AkShare `stock_em_hsgt_*` 系列

**新增服务**：
```python
# apps/server/services/north_money_service.py (新建)
class NorthMoneyService:
    """北向资金监控服务"""

    async def get_north_money_flow(self) -> NorthMoneyFlow:
        """获取当日北向资金流向"""
        df = ak.stock_em_hsgt_north_money()
        return NorthMoneyFlow(
            date=datetime.now().date(),
            sh_connect=float(df['沪股通'].iloc[-1]),  # 亿元
            sz_connect=float(df['深股通'].iloc[-1]),
            total=float(df['北向资金'].iloc[-1]),
            net_buy_stocks=await self._get_top_buy_stocks(),
            net_sell_stocks=await self._get_top_sell_stocks(),
        )

    async def get_stock_north_holding(self, symbol: str) -> StockNorthHolding:
        """获取个股北向持仓变化"""
        code = symbol.split('.')[0]
        df = ak.stock_em_hsgt_hold_stock(market="沪深", indicator="今日排行")
        row = df[df['代码'] == code]
        if row.empty:
            return None
        return StockNorthHolding(
            symbol=symbol,
            holding_shares=int(row['持股数量'].values[0]),
            holding_ratio=float(row['持股占比'].values[0]),
            change_shares=int(row['今日增持'].values[0]),
            change_ratio=float(row['增持比例'].values[0]),
        )
```

**API 端点**：
```python
# apps/server/api/routes/north_money.py (新建)
router = APIRouter(prefix="/north-money", tags=["North Money"])

@router.get("/flow")
async def get_north_money_flow():
    """获取北向资金流向"""

@router.get("/holding/{symbol}")
async def get_stock_north_holding(symbol: str):
    """获取个股北向持仓"""

@router.get("/top-buys")
async def get_top_north_buys(limit: int = 20):
    """获取北向资金净买入 TOP"""

@router.get("/top-sells")
async def get_top_north_sells(limit: int = 20):
    """获取北向资金净卖出 TOP"""
```

---

### 3.2 龙虎榜解析

**数据源**：AkShare `stock_lhb_*` 系列

**新增服务**：
```python
# apps/server/services/lhb_service.py (新建)
class LHBService:
    """龙虎榜解析服务"""

    async def get_daily_lhb(self, date: str = None) -> List[LHBStock]:
        """获取每日龙虎榜"""
        df = ak.stock_lhb_detail_daily_em(start_date=date, end_date=date)
        # 解析机构/游资席位
        return [self._parse_lhb_row(row) for _, row in df.iterrows()]

    async def get_stock_lhb_history(self, symbol: str, days: int = 30) -> List[LHBRecord]:
        """获取个股龙虎榜历史"""
        code = symbol.split('.')[0]
        df = ak.stock_lhb_ggtj_em()
        return [...]

    def _identify_hot_money(self, seat_name: str) -> HotMoneyInfo:
        """识别知名游资席位"""
        hot_money_map = {
            "华鑫证券上海分公司": {"name": "溧阳路", "style": "打板"},
            "国泰君安上海江苏路": {"name": "章盟主", "style": "趋势"},
            # ...
        }
        return hot_money_map.get(seat_name)
```

**API 端点**：
```python
# apps/server/api/routes/lhb.py (新建)
router = APIRouter(prefix="/lhb", tags=["龙虎榜"])

@router.get("/daily")
async def get_daily_lhb(date: str = None):
    """获取每日龙虎榜"""

@router.get("/stock/{symbol}")
async def get_stock_lhb(symbol: str, days: int = 30):
    """获取个股龙虎榜历史"""

@router.get("/hot-money")
async def get_hot_money_activity():
    """获取知名游资动向"""
```

---

### 3.3 限售解禁预警

**数据源**：AkShare `stock_restricted_release_*`

**新增服务**：
```python
# apps/server/services/restricted_release_service.py (新建)
class RestrictedReleaseService:
    """限售解禁预警服务"""

    async def get_upcoming_releases(self, days: int = 30) -> List[RestrictedRelease]:
        """获取未来 N 天解禁数据"""
        df = ak.stock_restricted_release_summary_em()
        # 过滤并计算解禁市值占比
        return [...]

    async def get_stock_release_schedule(self, symbol: str) -> List[ReleaseEvent]:
        """获取个股解禁时间表"""
        code = symbol.split('.')[0]
        df = ak.stock_restricted_release_detail_em(symbol=code)
        return [...]

    def calculate_impact_score(self, release: RestrictedRelease) -> int:
        """计算解禁冲击评分 (0-100)"""
        # 基于解禁市值/流通市值、股东类型等计算
        ...
```

**API 端点**：
```python
# apps/server/api/routes/restricted.py (新建)
router = APIRouter(prefix="/restricted", tags=["限售解禁"])

@router.get("/upcoming")
async def get_upcoming_releases(days: int = 30):
    """获取未来解禁数据"""

@router.get("/stock/{symbol}")
async def get_stock_release_schedule(symbol: str):
    """获取个股解禁时间表"""

@router.get("/high-impact")
async def get_high_impact_releases(threshold: int = 50):
    """获取高冲击解禁预警"""
```

---

### 3.4 前端 A 股面板

**新增组件**：
```typescript
// apps/client/components/ChinaMarketPanel.tsx (新建)
interface ChinaMarketPanelProps {
  symbol: string;
}

export function ChinaMarketPanel({ symbol }: ChinaMarketPanelProps) {
  const { data: northMoney } = useNorthMoney(symbol);
  const { data: lhb } = useLHB(symbol);
  const { data: restricted } = useRestricted(symbol);

  return (
    <div className="grid grid-cols-3 gap-4">
      {/* 北向资金 */}
      <NorthMoneyCard data={northMoney} />

      {/* 龙虎榜 */}
      <LHBCard data={lhb} />

      {/* 限售解禁 */}
      <RestrictedCard data={restricted} />
    </div>
  );
}
```

---

## 四、开发优先级与排期

```
Week 1:
├── [P0] 流式打字机效果 (2d)
├── [P0] TradingView 图表集成 (3d)
└── [P1] TTS 播放基础功能 (2d)

Week 2:
├── [P1] TTS 播放完善 (1d)
├── [P1] SentimentAgent 实现 (3d)
└── [P2] PolicyAgent 实现 (3d)

Week 3:
├── [P2] BacktestAgent 实现 (5d)
└── [P2] 北向资金监控 (2d)

Week 4:
├── [P2] 龙虎榜解析 (2d)
├── [P2] 限售解禁预警 (2d)
├── [P3] 前端 A 股面板 (2d)
└── [P3] 集成测试 (1d)
```

---

## 五、技术依赖

### 前端新增依赖
```json
{
  "lightweight-charts": "^4.1.0"
}
```

### 后端新增依赖
```toml
# pyproject.toml
praw = "^7.7.1"        # Reddit API
tweepy = "^4.14.0"     # Twitter API
```

---

## 六、风险与缓解

| 风险 | 影响 | 缓解措施 |
|-----|------|---------|
| Reddit/Twitter API 限流 | SentimentAgent 数据不足 | 实现缓存 + 降级到 Google News |
| AkShare 接口变更 | A 股数据获取失败 | 版本锁定 + 监控告警 |
| TTS 延迟过高 | 用户体验下降 | 预生成 + 缓存热门分析 |
| 新 Agent 增加分析耗时 | 整体响应变慢 | 按需启用 + 并行优化 |

---

## 七、验收检查清单

### 前端 UX
- [ ] 打字机效果流畅（60fps）
- [ ] TradingView 图表支持缩放/十字光标
- [ ] TTS 播放可暂停/继续

### 新增 Agent
- [ ] SentimentAgent 输出符合 Schema
- [ ] PolicyAgent 正确解析政策来源
- [ ] BacktestAgent 历史匹配准确率 > 70%

### A 股适配
- [ ] 北向资金实时更新（延迟 < 5min）
- [ ] 龙虎榜识别主要游资席位
- [ ] 限售解禁提前 7 天预警

---

## 八、后续迭代方向

完成本阶段后，建议的下一步方向：

1. **WhaleWatcher Agent** - 大户链上/订单流监控
2. **自动化交易执行** - 对接券商 API
3. **AI 播客生成** - 多 Agent 对话音频合成
4. **协作作战室** - 多用户实时协作分析
