"""另类数据相关的 Pydantic Schema 定义"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ============ AH 溢价 ============

class AHPremiumStock(BaseModel):
    """AH 溢价个股数据"""
    a_code: str = Field(..., description="A 股代码")
    h_code: str = Field(..., description="H 股代码")
    name: str = Field(..., description="公司名称")
    a_price: float = Field(..., description="A 股价格")
    h_price: float = Field(..., description="H 股价格")
    premium_rate: float = Field(..., description="溢价率")
    premium_pct: float = Field(..., description="溢价百分比")


class AHPremiumStats(BaseModel):
    """AH 溢价统计数据"""
    avg_premium_pct: float = Field(..., description="平均溢价百分比")
    max_premium_pct: float = Field(..., description="最大溢价百分比")
    min_premium_pct: float = Field(..., description="最小溢价百分比")
    median_premium_pct: float = Field(..., description="中位数溢价百分比")
    discount_count: int = Field(..., description="折价股票数量")
    premium_count: int = Field(..., description="溢价股票数量")
    total_count: int = Field(..., description="总数量")


class AHPremiumListResponse(BaseModel):
    """AH 溢价排行榜响应"""
    timestamp: str = Field(..., description="数据时间戳")
    total: int = Field(..., description="总数量")
    stocks: List[AHPremiumStock] = Field(default_factory=list, description="股票列表")
    stats: AHPremiumStats = Field(..., description="统计数据")


class ArbitrageSignal(BaseModel):
    """套利信号"""
    signal: str = Field(..., description="信号类型")
    description: str = Field(..., description="信号描述")
    percentile: Optional[float] = Field(None, description="百分位")
    current_premium_pct: Optional[float] = Field(None, description="当前溢价百分比")
    historical_avg: Optional[float] = Field(None, description="历史平均值")


class AHPremiumHistoryPoint(BaseModel):
    """AH 溢价历史数据点"""
    date: str = Field(..., description="日期")
    ratio: float = Field(..., description="溢价比率")


class AHPremiumDetailResponse(BaseModel):
    """AH 溢价详情响应"""
    found: bool = Field(..., description="是否找到")
    current: AHPremiumStock = Field(..., description="当前数据")
    history: List[AHPremiumHistoryPoint] = Field(default_factory=list, description="历史数据")
    signal: ArbitrageSignal = Field(..., description="套利信号")
    timestamp: str = Field(..., description="数据时间戳")


# ============ 专利监控 ============

class PatentNewsItem(BaseModel):
    """专利新闻条目"""
    title: str = Field(..., description="标题")
    body: str = Field(..., description="内容")
    url: str = Field(..., description="链接")


class PatentAnalysisResponse(BaseModel):
    """专利分析响应"""
    symbol: str = Field(..., description="股票代码")
    company_name: str = Field(..., description="公司名称")
    timestamp: str = Field(..., description="时间戳")
    patent_news: List[PatentNewsItem] = Field(default_factory=list, description="专利新闻")
    tech_trends: List[PatentNewsItem] = Field(default_factory=list, description="技术趋势")
    analysis_hint: str = Field("", description="分析提示")
