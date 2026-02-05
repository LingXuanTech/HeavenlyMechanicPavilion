"""宏观经济相关的 Pydantic Schema 定义"""
from typing import List, Optional
from pydantic import BaseModel, Field


class MacroIndicator(BaseModel):
    """宏观经济指标"""
    name: str = Field(..., description="指标名称")
    value: float = Field(..., description="当前值")
    previous_value: Optional[float] = Field(None, description="前值")
    change: Optional[float] = Field(None, description="变化值")
    change_percent: Optional[float] = Field(None, description="变化百分比")
    unit: str = Field("", description="单位")
    date: str = Field(..., description="日期")
    source: str = Field(..., description="数据源")
    trend: str = Field("stable", description="趋势: up/down/stable")


class MacroOverview(BaseModel):
    """宏观经济概览"""
    fed_rate: Optional[MacroIndicator] = None
    gdp_growth: Optional[MacroIndicator] = None
    cpi: Optional[MacroIndicator] = None
    unemployment: Optional[MacroIndicator] = None
    pmi: Optional[MacroIndicator] = None
    treasury_10y: Optional[MacroIndicator] = None
    vix: Optional[MacroIndicator] = None
    dxy: Optional[MacroIndicator] = None
    sentiment: str = Field("Neutral", description="整体情绪")
    summary: str = Field("", description="宏观概要")
    last_updated: str = Field("", description="最后更新时间")


class MacroImpact(BaseModel):
    """宏观因素对市场的影响评估"""
    indicator: str = Field(..., description="影响因素/指标")
    impact_level: str = Field(..., description="影响程度: High/Medium/Low")
    direction: str = Field(..., description="影响方向: Bullish/Bearish/Neutral")
    reasoning: str = Field(..., description="分析逻辑")


class MacroAnalysisResult(BaseModel):
    """宏观分析结果"""
    overview: MacroOverview = Field(..., description="宏观概览")
    impacts: List[MacroImpact] = Field(default_factory=list, description="影响分析列表")
    market_outlook: str = Field(..., description="市场展望")
    risk_factors: List[str] = Field(default_factory=list, description="风险因素")
    opportunities: List[str] = Field(default_factory=list, description="机会")
