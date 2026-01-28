"""Pydantic 输出模型定义

统一各 Agent 的结构化输出格式，使用 LangChain 的 with_structured_output() 特性。
这些模型与前端 types.ts 中的接口保持一致。
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


# ============ 基础类型 ============

class TechnicalIndicator(BaseModel):
    """技术指标"""
    name: str = Field(description="指标名称，如 RSI, MACD, MA20")
    value: str = Field(description="指标值或描述")
    signal: Literal["Bullish", "Bearish", "Neutral"] = Field(description="该指标给出的信号")
    interpretation: str = Field(description="指标解读")


class NewsItem(BaseModel):
    """新闻条目"""
    headline: str = Field(description="新闻标题")
    sentiment: Literal["Positive", "Negative", "Neutral"] = Field(description="新闻情感")
    summary: str = Field(description="新闻摘要及对股票的影响")


class PriceLevels(BaseModel):
    """价格支撑/阻力位"""
    support: float = Field(description="支撑位价格")
    resistance: float = Field(description="阻力位价格")


class WebSource(BaseModel):
    """信息来源"""
    uri: str = Field(description="来源 URL")
    title: str = Field(description="来源标题")


# ============ 分析师输出模型 ============

class MarketAnalystOutput(BaseModel):
    """Market Analyst 结构化输出"""
    summary: str = Field(description="市场分析总结，2-3 句话")
    trend: Literal["Bullish", "Bearish", "Neutral"] = Field(description="当前趋势判断")
    indicators: List[TechnicalIndicator] = Field(
        description="选择的技术指标分析（最多 8 个）",
        max_length=8
    )
    price_levels: PriceLevels = Field(description="支撑位和阻力位")
    signal: Literal["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"] = Field(
        description="基于技术面的交易信号"
    )
    confidence: int = Field(description="信心度 0-100", ge=0, le=100)
    key_observations: List[str] = Field(
        description="关键观察点，3-5 条",
        min_length=1,
        max_length=5
    )


class FundamentalsAnalystOutput(BaseModel):
    """Fundamentals Analyst 结构化输出"""
    summary: str = Field(description="基本面分析总结")
    valuation_status: Literal["Undervalued", "Fair Value", "Overvalued"] = Field(
        description="估值状态"
    )
    financial_health: Literal["Strong", "Moderate", "Weak"] = Field(
        description="财务健康状况"
    )
    key_metrics: List[dict] = Field(
        description="关键财务指标，如 PE, PB, ROE 等",
        examples=[{"name": "P/E", "value": "15.2", "assessment": "合理"}]
    )
    growth_outlook: str = Field(description="增长前景描述")
    risks: List[str] = Field(description="主要风险因素")
    signal: Literal["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"] = Field(
        description="基于基本面的交易信号"
    )
    confidence: int = Field(description="信心度 0-100", ge=0, le=100)


class NewsAnalystOutput(BaseModel):
    """News Analyst 结构化输出"""
    summary: str = Field(description="新闻分析总结")
    overall_sentiment: Literal["Positive", "Negative", "Neutral", "Mixed"] = Field(
        description="整体新闻情感"
    )
    news_items: List[NewsItem] = Field(
        description="重要新闻列表",
        max_length=10
    )
    market_impact: str = Field(description="对市场/股价的潜在影响")
    catalysts: List[dict] = Field(
        description="即将到来的催化剂事件",
        examples=[{"name": "财报发布", "date": "2024-02-15", "impact": "Positive"}]
    )
    signal: Literal["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"] = Field(
        description="基于新闻面的交易信号"
    )
    confidence: int = Field(description="信心度 0-100", ge=0, le=100)


class SocialMediaAnalystOutput(BaseModel):
    """Social Media Analyst 结构化输出"""
    summary: str = Field(description="舆情分析总结")
    sentiment_score: int = Field(description="情感得分 -100 到 100", ge=-100, le=100)
    sentiment_trend: Literal["Improving", "Stable", "Deteriorating"] = Field(
        description="情感趋势变化"
    )
    hot_topics: List[str] = Field(description="热门讨论话题")
    influencer_sentiment: Literal["Positive", "Negative", "Neutral", "Mixed"] = Field(
        description="意见领袖的情感倾向"
    )
    retail_sentiment: Literal["Positive", "Negative", "Neutral", "Mixed"] = Field(
        description="散户情感倾向"
    )
    signal: Literal["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"] = Field(
        description="基于舆情的交易信号"
    )
    confidence: int = Field(description="信心度 0-100", ge=0, le=100)


class MacroAnalystOutput(BaseModel):
    """Macro Analyst 结构化输出"""
    summary: str = Field(description="宏观分析总结")
    environment: Literal["Tailwind", "Headwind", "Neutral"] = Field(
        description="宏观环境对该股票的影响"
    )
    relevant_factors: List[dict] = Field(
        description="相关宏观因素",
        examples=[{"factor": "利率环境", "status": "紧缩", "impact": "Negative"}]
    )
    sector_outlook: str = Field(description="所属行业前景")
    correlation_analysis: str = Field(description="与主要指数的相关性分析")
    signal: Literal["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"] = Field(
        description="基于宏观面的交易信号"
    )
    confidence: int = Field(description="信心度 0-100", ge=0, le=100)


class PortfolioAnalystOutput(BaseModel):
    """Portfolio Analyst 结构化输出"""
    summary: str = Field(description="组合分析总结")
    correlation_risk: Literal["Low", "Moderate", "High"] = Field(
        description="与现有持仓的相关性风险"
    )
    concentration_risk: Literal["Low", "Moderate", "High"] = Field(
        description="集中度风险"
    )
    position_suggestion: str = Field(description="建议仓位")
    diversification_impact: str = Field(description="对组合分散化的影响")
    signal: Literal["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"] = Field(
        description="基于组合视角的交易信号"
    )
    confidence: int = Field(description="信心度 0-100", ge=0, le=100)


# ============ 研究员/辩论输出模型 ============

class DebatePoint(BaseModel):
    """辩论论点"""
    argument: str = Field(description="论点陈述")
    evidence: str = Field(description="支持论点的证据")
    weight: Literal["High", "Medium", "Low"] = Field(description="论点权重")


class ResearcherOutput(BaseModel):
    """Bull/Bear Researcher 结构化输出"""
    position: Literal["Bull", "Bear"] = Field(description="立场")
    thesis: str = Field(description="核心论点，一句话概括")
    arguments: List[DebatePoint] = Field(
        description="支持论点列表",
        min_length=2,
        max_length=5
    )
    counter_to_opponent: str = Field(description="对对方观点的反驳")
    confidence: int = Field(description="信心度 0-100", ge=0, le=100)


class ResearchManagerOutput(BaseModel):
    """Research Manager 投资决策输出"""
    decision: Literal["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"] = Field(
        description="投资决策"
    )
    winner: Literal["Bull", "Bear", "Neutral"] = Field(
        description="辩论胜者判定"
    )
    reasoning: str = Field(description="决策理由")
    bull_summary: str = Field(description="多头核心观点总结")
    bear_summary: str = Field(description="空头核心观点总结")
    key_factors: List[str] = Field(description="影响决策的关键因素")
    action_plan: str = Field(description="具体行动计划")
    confidence: int = Field(description="信心度 0-100", ge=0, le=100)


# ============ 交易员输出模型 ============

class TradeSetup(BaseModel):
    """交易设置"""
    entry_zone: str = Field(description="入场价格区间")
    target_price: float = Field(description="目标价格")
    stop_loss_price: float = Field(description="止损价格")
    reward_to_risk_ratio: float = Field(description="盈亏比")
    invalidation_condition: str = Field(description="交易失效条件")


class TraderOutput(BaseModel):
    """Trader 结构化输出"""
    decision: Literal["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"] = Field(
        description="交易决策"
    )
    trade_setup: Optional[TradeSetup] = Field(
        default=None,
        description="交易设置（Hold 时可为空）"
    )
    position_size: str = Field(description="建议仓位比例")
    time_horizon: str = Field(description="持有时间框架")
    execution_notes: str = Field(description="执行注意事项")
    confidence: int = Field(description="信心度 0-100", ge=0, le=100)


# ============ 风险管理输出模型 ============

class RiskDebaterOutput(BaseModel):
    """Risky/Safe/Neutral Analyst 结构化输出"""
    position: Literal["Aggressive", "Conservative", "Neutral"] = Field(
        description="风险立场"
    )
    assessment: str = Field(description="风险评估观点")
    arguments: List[str] = Field(description="支持该立场的论点")
    counter_arguments: List[str] = Field(description="对其他立场的反驳")
    recommended_action: str = Field(description="建议的风险调整行动")
    confidence: int = Field(description="信心度 0-100", ge=0, le=100)


class RiskAssessment(BaseModel):
    """风险评估结果"""
    score: int = Field(description="风险评分 0-10", ge=0, le=10)
    volatility_status: Literal["Low", "Moderate", "High", "Extreme"] = Field(
        description="波动性状态"
    )
    liquidity_concerns: bool = Field(description="是否有流动性担忧")
    max_drawdown_risk: str = Field(description="最大回撤风险估计")
    verdict: Literal["Approved", "Caution", "Rejected"] = Field(
        description="风险审批结果"
    )


class RiskManagerOutput(BaseModel):
    """Risk Manager 最终决策输出"""
    final_decision: Literal["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"] = Field(
        description="最终交易决策"
    )
    risk_assessment: RiskAssessment = Field(description="风险评估")
    position_adjustment: str = Field(description="仓位调整建议")
    risk_mitigation: List[str] = Field(description="风险缓解措施")
    reasoning: str = Field(description="最终决策理由")
    confidence: int = Field(description="信心度 0-100", ge=0, le=100)


# ============ Scout Agent 输出模型 ============

class MarketOpportunity(BaseModel):
    """市场机会"""
    symbol: str = Field(description="股票代码")
    name: str = Field(description="公司名称")
    market: Literal["US", "HK", "CN"] = Field(description="市场")
    reason: str = Field(description="推荐理由")
    score: int = Field(description="机会评分 0-100", ge=0, le=100)


class ScoutAgentOutput(BaseModel):
    """Scout Agent 结构化输出"""
    summary: str = Field(description="市场热点总结")
    opportunities: List[MarketOpportunity] = Field(
        description="发现的投资机会",
        max_length=10
    )
    market_themes: List[str] = Field(description="当前市场主题/热点")
    sources: List[WebSource] = Field(description="信息来源")


# ============ 最终综合输出模型 ============

class FinalAnalysisOutput(BaseModel):
    """最终分析输出，对应前端 AgentAnalysis 接口"""
    symbol: str = Field(description="股票代码")
    timestamp: str = Field(description="分析时间戳")
    signal: Literal["Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"] = Field(
        description="最终信号"
    )
    confidence: int = Field(description="总体信心度 0-100", ge=0, le=100)
    reasoning: str = Field(description="决策理由总结")

    # 辩论结果
    debate: dict = Field(description="Bull vs Bear 辩论结果")

    # 风险评估
    risk_assessment: RiskAssessment = Field(description="风险评估")

    # 技术指标
    technical_indicators: dict = Field(description="技术指标摘要")

    # 支撑/阻力位
    price_levels: Optional[PriceLevels] = Field(default=None, description="价格水平")

    # 交易设置
    trade_setup: Optional[TradeSetup] = Field(default=None, description="交易设置")

    # 新闻分析
    news_analysis: List[NewsItem] = Field(description="新闻分析")

    # 催化剂
    catalysts: List[dict] = Field(default_factory=list, description="催化剂事件")

    # 同业对比
    peers: List[dict] = Field(default_factory=list, description="同业对比")

    # 宏观背景
    macro_context: Optional[dict] = Field(default=None, description="宏观背景")

    # 信息来源
    web_sources: List[WebSource] = Field(default_factory=list, description="信息来源")

    # 主播稿
    anchor_script: str = Field(description="AI 生成的主播口播稿")
