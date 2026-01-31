from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum


# ============ 数据源模型 ============

class StockPrice(BaseModel):
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int
    timestamp: datetime
    market: str  # CN, HK, US


class KlineData(BaseModel):
    datetime: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class TechnicalIndicators(BaseModel):
    rsi: Optional[float] = None
    macd: Optional[Dict[str, float]] = None
    ma5: Optional[float] = None
    ma10: Optional[float] = None
    ma20: Optional[float] = None
    trend: Optional[str] = None


class NewsItem(BaseModel):
    title: str
    content: Optional[str] = None
    source: str
    url: Optional[str] = None
    timestamp: datetime
    sentiment: Optional[str] = None  # Positive, Negative, Neutral


class CompanyFundamentals(BaseModel):
    symbol: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    pe_ratio: Optional[float] = None
    market_cap: Optional[float] = None
    dividend_yield: Optional[float] = None
    revenue_growth: Optional[float] = None
    profit_margin: Optional[float] = None
    description: Optional[str] = None


# ============ AgentAnalysis 合成结果模型 ============
# 与前端 types.ts 中的 AgentAnalysis 接口保持一一对应


class SignalType(str, Enum):
    STRONG_BUY = "Strong Buy"
    BUY = "Buy"
    HOLD = "Hold"
    SELL = "Sell"
    STRONG_SELL = "Strong Sell"


class DebatePoint(BaseModel):
    argument: str
    evidence: str
    weight: Literal["High", "Medium", "Low"]


class DebateSide(BaseModel):
    thesis: str
    points: List[DebatePoint] = []


class ResearcherDebate(BaseModel):
    bull: DebateSide
    bear: DebateSide
    winner: Literal["Bull", "Bear", "Neutral"]
    conclusion: str


class RiskAssessment(BaseModel):
    score: int = Field(ge=0, le=10, description="0 (Safe) to 10 (Extreme Risk)")
    volatilityStatus: Literal["Low", "Moderate", "High", "Extreme"]
    liquidityConcerns: bool = False
    maxDrawdownRisk: str
    verdict: Literal["Approved", "Caution", "Rejected"]


class CatalystEvent(BaseModel):
    name: str
    date: str
    impact: Literal["Positive", "Negative", "Neutral"]


class PriceLevels(BaseModel):
    support: float
    resistance: float


class AnalysisNewsItem(BaseModel):
    """合成结果中的新闻项（不同于数据源 NewsItem）"""
    headline: str
    sentiment: Literal["Positive", "Negative", "Neutral"]
    summary: str


class PeerData(BaseModel):
    name: str
    comparison: str


class TradeSetup(BaseModel):
    entryZone: str
    targetPrice: float
    stopLossPrice: float
    rewardToRiskRatio: float
    invalidationCondition: str


class MacroContext(BaseModel):
    relevantIndex: str
    correlation: Literal["High", "Medium", "Low", "Inverse"]
    environment: Literal["Tailwind", "Headwind", "Neutral"]
    summary: str


class WebSource(BaseModel):
    uri: str
    title: str


class RetailSentimentAnalysis(BaseModel):
    fomoLevel: Literal["High", "Medium", "Low", "None"]
    fudLevel: Literal["High", "Medium", "Low", "None"]
    overallMood: Literal["Greedy", "Neutral", "Fearful"]
    keyIndicators: List[str] = []


class PolicyAnalysis(BaseModel):
    recentPolicies: List[str] = []
    impact: Literal["Positive", "Neutral", "Negative"]
    riskFactors: List[str] = []
    opportunities: List[str] = []


class ChinaMarketAnalysis(BaseModel):
    retailSentiment: RetailSentimentAnalysis
    policyAnalysis: PolicyAnalysis


class DebateDisplay(BaseModel):
    showWinnerBadge: bool = True
    emphasisLevel: Literal["default", "prominent", "subtle", "highlight"] = "default"
    expandByDefault: bool = False


class UIHints(BaseModel):
    alertLevel: Literal["none", "info", "warning", "critical"] = "none"
    alertMessage: Optional[str] = None
    highlightSections: List[str] = ["signal"]
    keyMetrics: List[str] = []
    dataQualityIssues: Optional[List[str]] = None
    confidenceDisplay: Literal["gauge", "progress", "badge", "number"] = "number"
    debateDisplay: DebateDisplay = DebateDisplay()
    showPlannerReasoning: bool = False
    plannerInsight: Optional[str] = None
    actionSuggestions: List[str] = []
    historicalCasesCount: Optional[int] = None
    analysisLevel: Literal["L1", "L2"] = "L2"
    marketSpecificHints: Optional[List[str]] = None


class Diagnostics(BaseModel):
    task_id: Optional[str] = None
    elapsed_seconds: Optional[float] = None
    analysts_used: Optional[List[str]] = None
    planner_decision: Optional[str] = None
    planner_reasoning: Optional[str] = None
    planner_skip_reasons: Optional[Dict[str, str]] = None
    from_cache: Optional[bool] = None


class AgentAnalysis(BaseModel):
    """
    核心数据合约：Agent 分析合成结果

    与前端 types.ts 中的 AgentAnalysis 接口严格对应。
    由 ResponseSynthesizer 生成，通过 SSE 推送给前端。
    """
    symbol: str
    timestamp: str
    signal: str  # SignalType 值，但 LLM 输出可能略有差异，使用 str 容忍
    confidence: int = Field(ge=0, le=100)
    reasoning: str

    # 核心分析组件
    debate: Optional[ResearcherDebate] = None
    riskAssessment: Optional[RiskAssessment] = None

    # 辅助数据
    catalysts: Optional[List[CatalystEvent]] = None
    priceLevels: Optional[PriceLevels] = None
    technicalIndicators: Optional[Dict[str, Any]] = None
    newsAnalysis: Optional[List[AnalysisNewsItem]] = None
    peers: Optional[List[PeerData]] = None
    tradeSetup: Optional[TradeSetup] = None
    macroContext: Optional[MacroContext] = None
    webSources: Optional[List[WebSource]] = None
    anchor_script: Optional[str] = None

    # A股专用
    chinaMarket: Optional[ChinaMarketAnalysis] = None

    # UI 展示指导
    uiHints: Optional[UIHints] = None

    # 诊断信息
    diagnostics: Optional[Diagnostics] = None

    model_config = {"extra": "allow"}  # LLM 可能输出额外字段
