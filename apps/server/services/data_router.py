import re
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from functools import lru_cache
import httpx
import yfinance as yf
import akshare as ak
import time
import random
from services.models import StockPrice, KlineData, CompanyFundamentals, NewsItem
from config.settings import settings
import structlog

logger = structlog.get_logger()

# 简单的内存缓存（生产环境可换成 Redis）
_price_cache: Dict[str, tuple] = {}  # {symbol: (StockPrice, timestamp)}
_CACHE_TTL_SECONDS = 60  # 缓存有效期 60 秒

# 复用的 HTTP 客户端（避免每次请求创建新连接）
_http_client: Optional[httpx.AsyncClient] = None

# 数据源失败计数（简易熔断）
_provider_failures: Dict[str, Dict[str, Any]] = {}
_FAILURE_THRESHOLD = 5      # 连续失败次数阈值
_FAILURE_COOLDOWN = 60.0    # 熔断冷却时间（秒）


async def get_http_client() -> httpx.AsyncClient:
    """获取或创建共享的 HTTP 客户端"""
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
    return _http_client


async def close_http_client():
    """关闭 HTTP 客户端（应用退出时调用）"""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


class DataSourceError(Exception):
    """数据源错误"""
    def __init__(self, source: str, message: str):
        self.source = source
        super().__init__(f"[{source}] {message}")


def _is_provider_available(provider: str) -> bool:
    """检查数据源是否可用（未被熔断）"""
    if provider not in _provider_failures:
        return True

    failure_info = _provider_failures[provider]
    if failure_info["count"] < _FAILURE_THRESHOLD:
        return True

    # 检查冷却时间
    last_failure = failure_info.get("last_failure")
    if last_failure:
        elapsed = (datetime.now() - last_failure).total_seconds()
        if elapsed >= _FAILURE_COOLDOWN:
            # 冷却期过，重置计数器并允许重试
            logger.info(
                "Provider cooldown expired, resetting",
                provider=provider,
                cooldown_seconds=_FAILURE_COOLDOWN
            )
            _provider_failures[provider] = {"count": 0, "last_failure": None}
            return True

    logger.warning(
        "Provider is circuit-broken",
        provider=provider,
        failure_count=failure_info["count"],
        threshold=_FAILURE_THRESHOLD
    )
    return False


def _record_provider_success(provider: str):
    """记录数据源成功"""
    if provider in _provider_failures:
        _provider_failures[provider] = {"count": 0, "last_failure": None}


def _record_provider_failure(provider: str, error: Exception):
    """记录数据源失败"""
    if provider not in _provider_failures:
        _provider_failures[provider] = {"count": 0, "last_failure": None}

    _provider_failures[provider]["count"] += 1
    _provider_failures[provider]["last_failure"] = datetime.now()

    logger.warning(
        "Provider failure recorded",
        provider=provider,
        failure_count=_provider_failures[provider]["count"],
        error=str(error)
    )


async def _call_with_retry(
    coro_func,
    provider: str,
    max_retries: int = 3,
    base_delay: float = 1.0,
    *args,
    **kwargs
) -> Any:
    """
    带重试的异步调用

    Args:
        coro_func: 协程函数
        provider: 数据源名称
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）

    Returns:
        调用结果

    Raises:
        DataSourceError: 所有重试失败后抛出
    """
    import asyncio

    last_error = None

    for attempt in range(max_retries + 1):
        try:
            result = await coro_func(*args, **kwargs)
            _record_provider_success(provider)
            return result
        except Exception as e:
            last_error = e
            _record_provider_failure(provider, e)

            if attempt == max_retries:
                raise DataSourceError(provider, str(e))

            # 判断是否可重试
            error_str = str(e).lower()
            retryable = any(kw in error_str for kw in [
                "connection", "timeout", "reset", "refused",
                "unavailable", "temporary", "rate limit"
            ])

            if not retryable:
                raise DataSourceError(provider, str(e))

            # 指数退避 + 抖动
            delay = min(base_delay * (2 ** attempt), 30.0)
            delay = delay * (0.5 + random.random())

            logger.warning(
                "Provider call failed, retrying",
                provider=provider,
                attempt=attempt + 1,
                max_retries=max_retries,
                delay=round(delay, 2),
                error=str(e)
            )

            await asyncio.sleep(delay)

    raise DataSourceError(provider, str(last_error))


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
        api_key = settings.ALPHA_VANTAGE_API_KEY
        if not api_key:
            raise DataSourceError("alpha_vantage", "API key not configured")

        try:
            url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"
            client = await get_http_client()
            response = await client.get(url)
            response.raise_for_status()
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
        except httpx.HTTPError as e:
            raise DataSourceError("alpha_vantage", f"HTTP error: {str(e)}")
        except Exception as e:
            raise DataSourceError("alpha_vantage", str(e))

    @classmethod
    async def get_stock_price(cls, symbol: str) -> StockPrice:
        """
        获取股票价格（带降级和熔断机制）

        优先级：
        - CN: akshare -> yfinance
        - HK/US: yfinance -> alpha_vantage

        特性：
        - 熔断保护：连续失败 5 次后跳过该数据源 60 秒
        - 失败时尝试使用缓存数据
        """
        market = cls.get_market(symbol)
        providers = cls._get_providers_for_market(market)

        logger.info("Fetching stock price", symbol=symbol, market=market, providers=providers)

        last_error = None
        attempted_providers = []

        for provider in providers:
            # 检查熔断状态
            if not _is_provider_available(provider):
                logger.debug(
                    "Skipping circuit-broken provider",
                    symbol=symbol,
                    provider=provider
                )
                continue

            attempted_providers.append(provider)

            try:
                if provider == "akshare":
                    price = await cls._get_price_akshare(symbol)
                elif provider == "yfinance":
                    price = await cls._get_price_yfinance(symbol, market)
                elif provider == "alpha_vantage":
                    price = await cls._get_price_alpha_vantage(symbol)
                else:
                    continue

                # 成功获取，记录成功并缓存
                _record_provider_success(provider)
                cls._set_cached_price(symbol, price)
                logger.info("Price fetched successfully", symbol=symbol, provider=provider)
                return price

            except DataSourceError as e:
                _record_provider_failure(provider, e)
                logger.warning("Data source failed, trying next", symbol=symbol, source=e.source, error=str(e))
                last_error = e
                continue
            except Exception as e:
                _record_provider_failure(provider, e)
                logger.warning("Unexpected error, trying next provider", symbol=symbol, provider=provider, error=str(e))
                last_error = DataSourceError(provider, str(e))
                continue

        # 所有数据源都失败，尝试使用缓存
        cached = cls._get_cached_price(symbol)
        if cached:
            logger.warning(
                "All providers failed, using stale cache",
                symbol=symbol,
                attempted=attempted_providers
            )
            return cached

        # 完全失败
        raise last_error or Exception(f"All data sources failed for {symbol}")

    @classmethod
    async def get_history(cls, symbol: str, period: str = "1mo") -> List[KlineData]:
        """获取历史 K 线数据（带降级和熔断机制）"""
        market = cls.get_market(symbol)

        # 尝试主数据源（A 股用 AkShare）
        if market == "CN" and _is_provider_available("akshare"):
            try:
                result = await cls._get_history_akshare(symbol)
                _record_provider_success("akshare")
                return result
            except Exception as e:
                _record_provider_failure("akshare", e)
                logger.warning("AkShare history failed, trying yfinance", symbol=symbol, error=str(e))

        # 降级到 yfinance
        if _is_provider_available("yfinance"):
            try:
                result = await cls._get_history_yfinance(symbol, period)
                _record_provider_success("yfinance")
                return result
            except Exception as e:
                _record_provider_failure("yfinance", e)
                logger.error("yfinance history failed", symbol=symbol, error=str(e))
                raise

        raise DataSourceError("all", f"All history sources unavailable for {symbol}")

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

    @staticmethod
    def get_provider_status() -> Dict[str, Any]:
        """获取所有数据源的状态"""
        status = {}
        for provider in ["akshare", "yfinance", "alpha_vantage"]:
            if provider in _provider_failures:
                failure_info = _provider_failures[provider]
                is_available = _is_provider_available(provider)
                status[provider] = {
                    "available": is_available,
                    "failure_count": failure_info["count"],
                    "threshold": _FAILURE_THRESHOLD,
                    "last_failure": failure_info["last_failure"].isoformat() if failure_info["last_failure"] else None,
                    "cooldown_seconds": _FAILURE_COOLDOWN,
                }
            else:
                status[provider] = {
                    "available": True,
                    "failure_count": 0,
                    "threshold": _FAILURE_THRESHOLD,
                    "last_failure": None,
                    "cooldown_seconds": _FAILURE_COOLDOWN,
                }
        return status

    @staticmethod
    def reset_provider(provider: str):
        """重置指定数据源的熔断状态"""
        if provider in _provider_failures:
            _provider_failures[provider] = {"count": 0, "last_failure": None}
            logger.info("Provider reset", provider=provider)

    @staticmethod
    def reset_all_providers():
        """重置所有数据源的熔断状态"""
        global _provider_failures
        _provider_failures.clear()
        logger.info("All providers reset")
