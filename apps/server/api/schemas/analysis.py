"""分析相关的 Pydantic Schema 定义

这些模型将被 FastAPI 用于：
1. 自动生成 OpenAPI schema
2. 响应数据验证
3. 前端类型自动生成
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Any, Literal
from pydantic import BaseModel, Field


# ============ 枚举类型 ============

class SignalType(str, Enum):
    """交易信号类型"""
    STRONG_BUY = "Strong Buy"
    BUY = "Buy"
    HOLD = "Hold"
    SELL = "Sell"
    STRONG_SELL = "Strong Sell"


class AlertLevel(str, Enum):
    """警示级别"""
    NONE = "none"
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class VisualStyle(str, Enum):
    """视觉样式"""
    DEFAULT = "default"
    PROMINENT = "prominent"
    SUBTLE = "subtle"
    HIGHLIGHT = "highlight"


class VolatilityStatus(str, Enum):
    """波动性状态"""
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    EXTREME = "Extreme"


class RiskVerdict(str, Enum):
    """风险评估结论"""
    APPROVED = "Approved"
    CAUTION = "Caution"
    REJECTED = "Rejected"


class DebateWinner(str, Enum):
    """辩论获胜方"""
    BULL = "Bull"
    BEAR = "Bear"
    NEUTRAL = "Neutral"


class TrendDirection(str, Enum):
    """趋势方向"""
    BULLISH = "Bullish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"


# ============ 基础模型 ============

class DebatePoint(BaseModel):
    """辩论论点"""
    argument: str = Field(..., description="论点内容")
    evidence: str = Field(..., description="支持证据")
    weight: str = Field(..., description="权重: High/Medium/Low")


class BullBearPosition(BaseModel):
    """多空立场"""
    thesis: str = Field(..., description="核心论点")
    points: List[DebatePoint] = Field(default_factory=list, description="支持论点列表")


class ResearcherDebate(BaseModel):
    """研究员辩论结果"""
    bull: BullBearPosition = Field(..., description="多头立场")
    bear: BullBearPosition = Field(..., description="空头立场")
    winner: DebateWinner = Field(..., description="获胜方")
    conclusion: str = Field(..., description="辩论结论")


class RiskAssessment(BaseModel):
    """风险评估"""
    score: int = Field(..., ge=0, le=10, description="风险评分 (0-10)")
    volatility_status: VolatilityStatus = Field(..., description="波动性状态")
    liquidity_concerns: bool = Field(..., description="是否存在流动性问题")
    max_drawdown_risk: str = Field(..., description="最大回撤风险估计")
    verdict: RiskVerdict = Field(..., description="风险评估结论")


class TechnicalIndicators(BaseModel):
    """技术指标"""
    rsi: float = Field(..., description="RSI 指标值")
    macd: str = Field(..., description="MACD 状态描述")
    trend: TrendDirection = Field(..., description="趋势方向")


class TradeSetup(BaseModel):
    """交易设置"""
    entry_zone: Optional[str] = Field(None, description="入场区间")
    target_price: Optional[str] = Field(None, description="目标价格")
    stop_loss: Optional[str] = Field(None, description="止损价格")
    risk_reward: Optional[str] = Field(None, description="风险收益比")


class NewsItem(BaseModel):
    """新闻条目"""
    headline: str = Field(..., description="新闻标题")
    summary: Optional[str] = Field(None, description="新闻摘要")
    sentiment: Optional[str] = Field(None, description="情感倾向")
    source: Optional[str] = Field(None, description="来源")
    url: Optional[str] = Field(None, description="链接")
    published_at: Optional[str] = Field(None, description="发布时间")


class PeerData(BaseModel):
    """同行数据"""
    symbol: str = Field(..., description="股票代码")
    name: str = Field(..., description="公司名称")
    change_percent: Optional[float] = Field(None, description="涨跌幅")
    correlation: Optional[float] = Field(None, description="相关性")


class CatalystEvent(BaseModel):
    """催化剂事件"""
    event: str = Field(..., description="事件描述")
    date: Optional[str] = Field(None, description="预期日期")
    impact: str = Field(..., description="影响程度: High/Medium/Low")


class PriceLevels(BaseModel):
    """价格水平"""
    support: Optional[float] = Field(None, description="支撑位")
    resistance: Optional[float] = Field(None, description="阻力位")
    pivot: Optional[float] = Field(None, description="枢轴点")


class MacroContext(BaseModel):
    """宏观环境"""
    environment: str = Field(..., description="市场环境: Tailwind/Headwind/Neutral")
    summary: str = Field(..., description="宏观环境摘要")


class WebSource(BaseModel):
    """网络来源"""
    title: str = Field(..., description="标题")
    url: str = Field(..., description="链接")
    snippet: Optional[str] = Field(None, description="摘要片段")


# ============ A股市场专用 ============

class RetailSentimentAnalysis(BaseModel):
    """散户情绪分析"""
    fomo_level: str = Field(..., description="FOMO 程度: High/Medium/Low/None")
    fud_level: str = Field(..., description="FUD 程度: High/Medium/Low/None")
    overall_mood: str = Field(..., description="整体情绪: Greedy/Neutral/Fearful")
    key_indicators: List[str] = Field(default_factory=list, description="关键指标")


class PolicyAnalysis(BaseModel):
    """政策分析"""
    recent_policies: List[str] = Field(default_factory=list, description="近期政策")
    impact: str = Field(..., description="影响: Positive/Neutral/Negative")
    risk_factors: List[str] = Field(default_factory=list, description="风险因素")
    opportunities: List[str] = Field(default_factory=list, description="机会")


class ChinaMarketAnalysis(BaseModel):
    """A股市场专用分析"""
    retail_sentiment: RetailSentimentAnalysis = Field(..., description="散户情绪")
    policy_analysis: PolicyAnalysis = Field(..., description="政策分析")


# ============ UI Hints ============

class DebateDisplay(BaseModel):
    """辩论展示配置"""
    show_winner_badge: bool = Field(True, description="是否显示获胜方徽章")
    emphasis_level: VisualStyle = Field(VisualStyle.DEFAULT, description="强调级别")
    expand_by_default: bool = Field(False, description="是否默认展开")


class UIHints(BaseModel):
    """UI 展示提示 - AI 生成的展示指导"""
    alert_level: AlertLevel = Field(AlertLevel.NONE, description="警示级别")
    alert_message: Optional[str] = Field(None, description="警示消息")
    highlight_sections: List[str] = Field(
        default_factory=list,
        description="需要突出显示的区域: signal/risk/debate/trade_setup/news/planner"
    )
    key_metrics: List[str] = Field(default_factory=list, description="关键指标列表")
    data_quality_issues: Optional[List[str]] = Field(None, description="数据质量问题")
    confidence_display: str = Field("number", description="置信度展示方式: gauge/progress/badge/number")
    debate_display: DebateDisplay = Field(default_factory=DebateDisplay, description="辩论展示配置")
    show_planner_reasoning: bool = Field(False, description="是否展示 Planner 决策逻辑")
    planner_insight: Optional[str] = Field(None, description="Planner 洞察")
    action_suggestions: List[str] = Field(default_factory=list, description="行动建议")
    historical_cases_count: Optional[int] = Field(None, description="相关历史案例数量")
    analysis_level: str = Field("L2", description="分析级别: L1/L2")
    market_specific_hints: Optional[List[str]] = Field(None, description="市场特殊提示")


# ============ 诊断信息 ============

class AnalysisDiagnostics(BaseModel):
    """分析诊断信息"""
    task_id: Optional[str] = Field(None, description="任务 ID")
    user_id: Optional[int] = Field(None, description="任务所属用户 ID（审计字段）")
    elapsed_seconds: Optional[float] = Field(None, description="耗时（秒）")
    analysts_used: Optional[List[str]] = Field(None, description="使用的分析师列表")
    planner_decision: Optional[str] = Field(None, description="Planner 决策说明")
    architecture_mode: Optional[str] = Field(None, description="架构模式 (monolith / subgraph)")


# ============ 完整报告 ============

class FullReport(BaseModel):
    """完整分析报告"""
    signal: SignalType = Field(..., description="交易信号")
    confidence: int = Field(..., ge=0, le=100, description="置信度 (0-100)")
    reasoning: str = Field(..., description="分析推理")
    debate: ResearcherDebate = Field(..., description="研究员辩论")
    risk_assessment: RiskAssessment = Field(..., description="风险评估")
    technical_indicators: TechnicalIndicators = Field(..., description="技术指标")
    news_analysis: List[NewsItem] = Field(default_factory=list, description="新闻分析")
    peers: List[PeerData] = Field(default_factory=list, description="同行数据")
    trade_setup: Optional[TradeSetup] = Field(None, description="交易设置")
    catalysts: Optional[List[CatalystEvent]] = Field(None, description="催化剂事件")
    price_levels: Optional[PriceLevels] = Field(None, description="价格水平")
    macro_context: Optional[MacroContext] = Field(None, description="宏观环境")
    web_sources: Optional[List[WebSource]] = Field(None, description="网络来源")
    china_market: Optional[ChinaMarketAnalysis] = Field(None, description="A股市场分析")


# ============ API 响应模型 ============

class AgentAnalysisResponse(BaseModel):
    """Agent 分析响应"""
    id: Optional[int] = Field(None, description="分析记录 ID")
    symbol: str = Field(..., description="股票代码")
    date: str = Field(..., description="分析日期")
    signal: str = Field(..., description="交易信号")
    confidence: int = Field(..., ge=0, le=100, description="置信度")
    full_report: FullReport = Field(..., description="完整报告")
    anchor_script: Optional[str] = Field(None, description="TTS 播报脚本")
    created_at: str = Field(..., description="创建时间")
    task_id: Optional[str] = Field(None, description="任务 ID")
    user_id: Optional[int] = Field(None, description="任务所属用户 ID（审计字段）")
    diagnostics: Optional[AnalysisDiagnostics] = Field(None, description="诊断信息")
    ui_hints: Optional[UIHints] = Field(None, description="UI 展示提示")

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "date": "2024-01-15",
                "signal": "Buy",
                "confidence": 75,
                "full_report": {
                    "signal": "Buy",
                    "confidence": 75,
                    "reasoning": "Based on strong fundamentals...",
                    "debate": {
                        "bull": {"thesis": "Strong growth", "points": []},
                        "bear": {"thesis": "Valuation concerns", "points": []},
                        "winner": "Bull",
                        "conclusion": "Bullish outlook prevails"
                    },
                    "risk_assessment": {
                        "score": 4,
                        "volatility_status": "Moderate",
                        "liquidity_concerns": False,
                        "max_drawdown_risk": "-15%",
                        "verdict": "Approved"
                    },
                    "technical_indicators": {
                        "rsi": 55.5,
                        "macd": "Bullish crossover",
                        "trend": "Bullish"
                    },
                    "news_analysis": [],
                    "peers": []
                },
                "created_at": "2024-01-15T10:30:00Z"
            }
        }


class AnalysisHistoryItem(BaseModel):
    """分析历史条目"""
    id: int = Field(..., description="记录 ID")
    date: str = Field(..., description="分析日期")
    signal: str = Field(..., description="交易信号")
    confidence: int = Field(..., description="置信度")
    status: str = Field(..., description="状态: completed/failed/pending")
    created_at: str = Field(..., description="创建时间")
    task_id: Optional[str] = Field(None, description="任务 ID")
    user_id: Optional[int] = Field(None, description="任务所属用户 ID（审计字段）")


class AnalysisHistoryResponse(BaseModel):
    """分析历史响应"""
    items: List[AnalysisHistoryItem] = Field(..., description="历史记录列表")
    total: Optional[int] = Field(None, description="总记录数（仅 offset 分页时返回）")
    offset: Optional[int] = Field(None, description="偏移量（offset 分页）")
    limit: int = Field(..., description="每页数量")
    next_cursor: Optional[int] = Field(None, description="下一页游标（cursor 分页）")
    has_more: bool = Field(False, description="是否有更多数据")


class AnalysisDetailResponse(BaseModel):
    """分析详情响应"""
    id: int = Field(..., description="记录 ID")
    symbol: str = Field(..., description="股票代码")
    date: str = Field(..., description="分析日期")
    signal: str = Field(..., description="交易信号")
    confidence: int = Field(..., description="置信度")
    full_report: FullReport = Field(..., description="完整报告")
    anchor_script: Optional[str] = Field(None, description="TTS 播报脚本")
    created_at: str = Field(..., description="创建时间")
    task_id: Optional[str] = Field(None, description="任务 ID")
    elapsed_seconds: Optional[float] = Field(None, description="耗时（秒）")
    user_id: Optional[int] = Field(None, description="任务所属用户 ID（审计字段）")


class AnalysisTaskStatus(BaseModel):
    """分析任务状态"""
    task_id: str = Field(..., description="任务 ID")
    symbol: str = Field(..., description="股票代码")
    status: str = Field(..., description="状态: pending/running/completed/failed")
    progress: Optional[int] = Field(None, description="进度 (0-100)")
    current_stage: Optional[str] = Field(None, description="当前阶段")
    error_message: Optional[str] = Field(None, description="错误信息")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")
    user_id: Optional[int] = Field(None, description="任务所属用户 ID（审计字段）")
