"""
示例市场数据 Fixtures

提供用于测试的标准化市场数据样本。
"""
from datetime import datetime, timedelta
from typing import List, Dict, Any

from services.models import StockPrice, KlineData, CompanyFundamentals, NewsItem


# =============================================================================
# 股票价格样本
# =============================================================================

def get_sample_us_stock_price(symbol: str = "AAPL") -> StockPrice:
    """美股价格样本"""
    return StockPrice(
        symbol=symbol,
        price=150.0,
        change=2.0,
        change_percent=1.35,
        volume=50000000,
        timestamp=datetime.now(),
        market="US",
    )


def get_sample_cn_stock_price(symbol: str = "600519.SH") -> StockPrice:
    """A股价格样本（贵州茅台）"""
    return StockPrice(
        symbol=symbol,
        price=1800.0,
        change=20.0,
        change_percent=1.12,
        volume=5000000,
        timestamp=datetime.now(),
        market="CN",
    )


def get_sample_hk_stock_price(symbol: str = "0700.HK") -> StockPrice:
    """港股价格样本（腾讯控股）"""
    return StockPrice(
        symbol=symbol,
        price=380.0,
        change=5.0,
        change_percent=1.33,
        volume=20000000,
        timestamp=datetime.now(),
        market="HK",
    )


# =============================================================================
# K线数据样本
# =============================================================================

def get_sample_kline_data(days: int = 30, base_price: float = 150.0) -> List[KlineData]:
    """生成 K 线数据样本"""
    klines = []
    current_price = base_price

    for i in range(days):
        date = datetime.now() - timedelta(days=days - i)
        # 模拟价格波动
        open_price = current_price
        high_price = current_price * 1.02
        low_price = current_price * 0.98
        close_price = current_price * (1 + (i % 3 - 1) * 0.01)

        klines.append(KlineData(
            datetime=date,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=1000000 + (i * 10000),
        ))
        current_price = close_price

    return klines


# =============================================================================
# 公司基本面样本
# =============================================================================

def get_sample_fundamentals(symbol: str = "AAPL") -> CompanyFundamentals:
    """公司基本面数据样本"""
    samples = {
        "AAPL": CompanyFundamentals(
            symbol="AAPL",
            name="Apple Inc.",
            sector="Technology",
            industry="Consumer Electronics",
            pe_ratio=25.5,
            market_cap=2500000000000,
            dividend_yield=0.005,
            revenue_growth=0.08,
            profit_margin=0.25,
            description="Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories.",
        ),
        "600519.SH": CompanyFundamentals(
            symbol="600519.SH",
            name="贵州茅台",
            sector="Consumer Staples",
            industry="Beverages - Wineries & Distilleries",
            pe_ratio=35.0,
            market_cap=2200000000000,
            dividend_yield=0.015,
            revenue_growth=0.12,
            profit_margin=0.52,
            description="贵州茅台酒股份有限公司主要从事茅台酒及系列产品的生产与销售。",
        ),
        "0700.HK": CompanyFundamentals(
            symbol="0700.HK",
            name="腾讯控股",
            sector="Communication Services",
            industry="Internet Content & Information",
            pe_ratio=18.5,
            market_cap=3500000000000,
            dividend_yield=0.003,
            revenue_growth=0.05,
            profit_margin=0.28,
            description="腾讯控股有限公司是一家综合性互联网服务提供商。",
        ),
    }
    return samples.get(symbol, samples["AAPL"])


# =============================================================================
# 新闻数据样本
# =============================================================================

def get_sample_news(symbol: str = "AAPL", count: int = 5) -> List[NewsItem]:
    """新闻数据样本"""
    news = []
    sentiments = ["Positive", "Negative", "Neutral"]

    for i in range(count):
        news.append(NewsItem(
            title=f"Sample news title {i + 1} for {symbol}",
            content=f"This is sample news content about {symbol}. It discusses recent developments.",
            source="TestNews",
            url=f"https://example.com/news/{symbol}/{i + 1}",
            timestamp=datetime.now() - timedelta(hours=i),
            sentiment=sentiments[i % 3],
        ))

    return news


# =============================================================================
# API 响应样本
# =============================================================================

def get_sample_yfinance_fast_info() -> Dict[str, Any]:
    """yfinance fast_info 响应样本"""
    return {
        "last_price": 150.0,
        "previous_close": 148.0,
        "last_volume": 50000000,
        "market_cap": 2500000000000,
        "fifty_day_average": 145.0,
        "two_hundred_day_average": 140.0,
    }


def get_sample_yfinance_info() -> Dict[str, Any]:
    """yfinance info 响应样本"""
    return {
        "symbol": "AAPL",
        "longName": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "trailingPE": 25.5,
        "forwardPE": 22.0,
        "marketCap": 2500000000000,
        "dividendYield": 0.005,
        "revenueGrowth": 0.08,
        "profitMargins": 0.25,
        "longBusinessSummary": "Apple Inc. designs, manufactures, and markets smartphones.",
    }


def get_sample_alpha_vantage_response() -> Dict[str, Any]:
    """Alpha Vantage Global Quote 响应样本"""
    return {
        "Global Quote": {
            "01. symbol": "AAPL",
            "02. open": "148.50",
            "03. high": "151.00",
            "04. low": "147.80",
            "05. price": "150.00",
            "06. volume": "50000000",
            "07. latest trading day": "2026-01-28",
            "08. previous close": "148.00",
            "09. change": "2.00",
            "10. change percent": "1.35%",
        }
    }


def get_sample_akshare_spot_response() -> Dict[str, Any]:
    """AkShare A股实时数据响应样本（DataFrame 格式）"""
    return {
        "代码": ["600519", "000001", "601318"],
        "名称": ["贵州茅台", "平安银行", "中国平安"],
        "最新价": [1800.0, 10.5, 45.0],
        "涨跌额": [20.0, 0.15, 0.5],
        "涨跌幅": [1.12, 1.45, 1.12],
        "成交量": [5000000, 80000000, 30000000],
        "成交额": [9000000000, 840000000, 1350000000],
    }
