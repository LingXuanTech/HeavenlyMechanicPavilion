from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class StockPrice(BaseModel):
    symbol: str
    price: float
    change: float
    change_percent: float
    volume: int
    timestamp: datetime
    market: str # CN, HK, US

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
    sentiment: Optional[str] = None # Positive, Negative, Neutral

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
