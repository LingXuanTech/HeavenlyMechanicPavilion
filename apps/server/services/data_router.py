import re
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from functools import lru_cache
import yfinance as yf
import akshare as ak
from services.models import StockPrice, KlineData, CompanyFundamentals, NewsItem
from config.settings import settings
import structlog

logger = structlog.get_logger()

# 简单的内存缓存（生产环境可换成 Redis）
_price_cache: Dict[str, tuple] = {}  # {symbol: (StockPrice, timestamp)}
_CACHE_TTL_SECONDS = 60  # 缓存有效期 60 秒


class DataSourceError(Exception):
    """数据源错误"""
    def __init__(self, source: str, message: str):
        self.source = source
        super().__init__(f"[{source}] {message}")


class MarketRouter:
    """
    智能市场数据路由器

    支持多数据源降级：
    - CN (A股): AkShare -> yfinance (备选)
    - HK (港股): yfinance -> AkShare (备选)
    - US (美股): yfinance -> Alpha Vantage (备选)
    """

    @staticmethod
    def get_market(symbol: str) -> str:
        """
        根据股票代码后缀识别市场。
        - .SH / .SZ -> CN (A股)
        - .HK -> HK (港股)
        - 其他 -> US (美股)
        """
        if re.search(r'\.(SH|SZ)$', symbol, re.IGNORECASE):
            return "CN"
        elif re.search(r'\.HK$', symbol, re.IGNORECASE):
            return "HK"
        else:
            return "US"

    @staticmethod
    def _get_providers_for_market(market: str) -> List[str]:
        """根据市场返回数据源优先级列表"""
        providers = {
            "CN": ["akshare", "yfinance"],
            "HK": ["yfinance", "akshare"],
            "US": ["yfinance", "alpha_vantage"]
        }
        return providers.get(market, ["yfinance"])

    @staticmethod
    def _get_cached_price(symbol: str) -> Optional[StockPrice]:
        """从缓存获取价格"""
        cached = _price_cache.get(symbol)
        if cached:
            price, timestamp = cached
            if (datetime.now() - timestamp).total_seconds() < _CACHE_TTL_SECONDS:
                logger.debug("Using cached price", symbol=symbol)
                return price
        return None

    @staticmethod
    def _set_cached_price(symbol: str, price: StockPrice):
        """设置价格缓存"""
        _price_cache[symbol] = (price, datetime.now())

    @classmethod
    async def _get_price_akshare(cls, symbol: str) -> StockPrice:
        """通过 AkShare 获取 A 股价格"""
        try:
            df = ak.stock_zh_a_spot_em()
            code = symbol.split('.')[0]
            row = df[df['代码'] == code]

            if row.empty:
                raise DataSourceError("akshare", f"Symbol {symbol} not found")

            return StockPrice(
                symbol=symbol,
                price=float(row['最新价'].values[0]),
                change=float(row['涨跌额'].values[0]),
                change_percent=float(row['涨跌幅'].values[0]),
                volume=int(row['成交量'].values[0]),
                timestamp=datetime.now(),
                market="CN"
            )
        except Exception as e:
            raise DataSourceError("akshare", str(e))

    @classmethod
    async def _get_price_yfinance(cls, symbol: str, market: str) -> StockPrice:
        """通过 yfinance 获取价格"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info

            if info['last_price'] is None:
                raise DataSourceError("yfinance", f"No price data for {symbol}")

            return StockPrice(
                symbol=symbol,
                price=info['last_price'],
                change=info['last_price'] - info['previous_close'],
                change_percent=((info['last_price'] / info['previous_close']) - 1) * 100,
                volume=info['last_volume'] or 0,
                timestamp=datetime.now(),
                market=market
            )
        except Exception as e:
            raise DataSourceError("yfinance", str(e))

    @classmethod
    async def _get_price_alpha_vantage(cls, symbol: str) -> StockPrice:
        """通过 Alpha Vantage 获取价格（需要 API Key）"""
        import requests

        api_key = settings.ALPHA_VANTAGE_API_KEY
        if not api_key:
            raise DataSourceError("alpha_vantage", "API key not configured")

        try:
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"
            response = requests.get(url, timeout=10)
            data = response.json()

            quote = data.get("Global Quote", {})
            if not quote:
                raise DataSourceError("alpha_vantage", f"No data for {symbol}")

            price = float(quote.get("05. price", 0))
            prev_close = float(quote.get("08. previous close", 0))
            change = price - prev_close
            change_pct = float(quote.get("10. change percent", "0").replace("%", ""))

            return StockPrice(
                symbol=symbol,
                price=price,
                change=change,
                change_percent=change_pct,
                volume=int(quote.get("06. volume", 0)),
                timestamp=datetime.now(),
                market="US"
            )
        except Exception as e:
            raise DataSourceError("alpha_vantage", str(e))

    @classmethod
    async def get_stock_price(cls, symbol: str) -> StockPrice:
        """
        获取股票价格（带降级机制）

        优先级：
        - CN: akshare -> yfinance
        - HK/US: yfinance -> alpha_vantage

        失败时尝试使用缓存数据。
        """
        market = cls.get_market(symbol)
        providers = cls._get_providers_for_market(market)

        logger.info("Fetching stock price", symbol=symbol, market=market, providers=providers)

        last_error = None

        for provider in providers:
            try:
                if provider == "akshare":
                    price = await cls._get_price_akshare(symbol)
                elif provider == "yfinance":
                    price = await cls._get_price_yfinance(symbol, market)
                elif provider == "alpha_vantage":
                    price = await cls._get_price_alpha_vantage(symbol)
                else:
                    continue

                # 成功获取，缓存并返回
                cls._set_cached_price(symbol, price)
                logger.info("Price fetched successfully", symbol=symbol, provider=provider)
                return price

            except DataSourceError as e:
                logger.warning("Data source failed, trying next", symbol=symbol, source=e.source, error=str(e))
                last_error = e
                continue
            except Exception as e:
                logger.warning("Unexpected error, trying next provider", symbol=symbol, provider=provider, error=str(e))
                last_error = DataSourceError(provider, str(e))
                continue

        # 所有数据源都失败，尝试使用缓存
        cached = cls._get_cached_price(symbol)
        if cached:
            logger.warning("All providers failed, using stale cache", symbol=symbol)
            return cached

        # 完全失败
        raise last_error or Exception(f"All data sources failed for {symbol}")

    @classmethod
    async def get_history(cls, symbol: str, period: str = "1mo") -> List[KlineData]:
        """获取历史 K 线数据（带降级机制）"""
        market = cls.get_market(symbol)

        # 尝试主数据源
        if market == "CN":
            try:
                return await cls._get_history_akshare(symbol)
            except Exception as e:
                logger.warning("AkShare history failed, trying yfinance", symbol=symbol, error=str(e))

        # 降级到 yfinance
        try:
            return await cls._get_history_yfinance(symbol, period)
        except Exception as e:
            logger.error("All history sources failed", symbol=symbol, error=str(e))
            raise

    @classmethod
    async def _get_history_akshare(cls, symbol: str) -> List[KlineData]:
        """通过 AkShare 获取 A 股历史数据"""
        code = symbol.split('.')[0]
        df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")

        klines = []
        for _, row in df.tail(30).iterrows():
            klines.append(KlineData(
                datetime=pd.to_datetime(row['日期']),
                open=row['开盘'],
                high=row['最高'],
                low=row['最低'],
                close=row['收盘'],
                volume=row['成交量']
            ))
        return klines

    @classmethod
    async def _get_history_yfinance(cls, symbol: str, period: str) -> List[KlineData]:
        """通过 yfinance 获取历史数据"""
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period)

        klines = []
        for dt, row in hist.iterrows():
            klines.append(KlineData(
                datetime=dt,
                open=row['Open'],
                high=row['High'],
                low=row['Low'],
                close=row['Close'],
                volume=row['Volume']
            ))
        return klines

    @classmethod
    async def get_fundamentals(cls, symbol: str) -> CompanyFundamentals:
        """获取公司基本面数据"""
        market = cls.get_market(symbol)
        ticker = yf.Ticker(symbol)
        info = ticker.info

        return CompanyFundamentals(
            symbol=symbol,
            name=info.get('longName', symbol),
            sector=info.get('sector'),
            industry=info.get('industry'),
            pe_ratio=info.get('trailingPE'),
            market_cap=info.get('marketCap'),
            dividend_yield=info.get('dividendYield'),
            revenue_growth=info.get('revenueGrowth'),
            profit_margin=info.get('profitMargins'),
            description=info.get('longBusinessSummary')
        )

    @classmethod
    def clear_cache(cls):
        """清除价格缓存"""
        global _price_cache
        _price_cache.clear()
        logger.info("Price cache cleared")
