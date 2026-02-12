import re
import asyncio
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
from services.cache_service import cache_service
from config.settings import settings
from api.exceptions import DataSourceError
import structlog

logger = structlog.get_logger()

# 缓存 Key 规范
CACHE_KEY_PRICE = "market:price:{symbol}"
CACHE_KEY_HISTORY = "market:history:{symbol}"
CACHE_KEY_FUNDAMENTALS = "market:fundamentals:{symbol}"

# 分级缓存 TTL（秒）
_CACHE_TTL_PRICE = 30          # 价格缓存 30 秒
_CACHE_TTL_HISTORY = 5 * 60    # 历史数据缓存 5 分钟
_CACHE_TTL_FUNDAMENTALS = 24 * 60 * 60  # 基本面缓存 1 天

# 请求去重：正在进行中的请求 {key: asyncio.Future}
_pending_requests: Dict[str, asyncio.Future] = {}
_pending_lock = asyncio.Lock()

# 复用的 HTTP 客户端（避免每次请求创建新连接）
_http_client: Optional[httpx.AsyncClient] = None

# 数据源统计与熔断状态
# 结构: { provider_name: {
#   "count": 连续失败次数,
#   "last_failure": datetime,
#   "total_requests": 总请求数,
#   "successful_requests": 成功请求数,
#   "failed_requests": 失败请求数,
#   "total_latency": 总延迟(秒),
#   "last_error": 错误信息
# }}
_provider_stats: Dict[str, Dict[str, Any]] = {}
_FAILURE_THRESHOLD = 5      # 连续失败次数阈值
_FAILURE_COOLDOWN = 60.0    # 熔断冷却时间（秒）


def _init_provider_stats(provider: str):
    """初始化数据源统计信息"""
    if provider not in _provider_stats:
        _provider_stats[provider] = {
            "count": 0,
            "last_failure": None,
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_latency": 0.0,
            "last_error": None
        }


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


async def coalesce_request(key: str, fetch_func, *args, **kwargs):
    """
    请求去重：多个并发请求同一数据时，只执行一次实际请求

    Args:
        key: 请求唯一标识（如 "price:AAPL"）
        fetch_func: 实际获取数据的协程函数
        *args, **kwargs: 传递给 fetch_func 的参数

    Returns:
        获取的数据

    Example:
        # 多个并发调用只会触发一次实际请求
        price = await coalesce_request(f"price:{symbol}", _fetch_price_impl, symbol)
    """
    global _pending_requests

    async with _pending_lock:
        # 检查是否有正在进行的相同请求
        if key in _pending_requests:
            future = _pending_requests[key]
            logger.debug("Coalescing request, waiting for pending", key=key)
        else:
            # 创建新的 Future 并注册
            future = asyncio.get_event_loop().create_future()
            _pending_requests[key] = future

            # 在后台执行实际请求
            async def execute_and_resolve():
                try:
                    result = await fetch_func(*args, **kwargs)
                    future.set_result(result)
                except Exception as e:
                    future.set_exception(e)
                finally:
                    # 清理 pending 请求
                    async with _pending_lock:
                        _pending_requests.pop(key, None)

            asyncio.create_task(execute_and_resolve())

    # 等待结果
    return await future


def _is_provider_available(provider: str) -> bool:
    """检查数据源是否可用（未被熔断）"""
    _init_provider_stats(provider)
    stats = _provider_stats[provider]

    if stats["count"] < _FAILURE_THRESHOLD:
        return True

    # 检查冷却时间
    last_failure = stats.get("last_failure")
    if last_failure:
        elapsed = (datetime.now() - last_failure).total_seconds()
        if elapsed >= _FAILURE_COOLDOWN:
            # 冷却期过，重置连续失败计数器并允许重试
            logger.info(
                "Provider cooldown expired, resetting",
                provider=provider,
                cooldown_seconds=_FAILURE_COOLDOWN
            )
            stats["count"] = 0
            return True

    logger.warning(
        "Provider is circuit-broken",
        provider=provider,
        failure_count=stats["count"],
        threshold=_FAILURE_THRESHOLD
    )
    return False


def _record_provider_success(provider: str, latency: float = 0.0):
    """记录数据源成功"""
    _init_provider_stats(provider)
    stats = _provider_stats[provider]
    stats["count"] = 0
    stats["total_requests"] += 1
    stats["successful_requests"] += 1
    stats["total_latency"] += latency

    # 同步到健康监控历史
    from services.health_monitor import health_monitor
    health_monitor.record_provider_call(provider, latency * 1000, success=True)


def _record_provider_failure(provider: str, error: Exception, latency: float = 0.0):
    """记录数据源失败"""
    _init_provider_stats(provider)
    stats = _provider_stats[provider]
    stats["count"] += 1
    stats["last_failure"] = datetime.now()
    stats["total_requests"] += 1
    stats["failed_requests"] += 1
    stats["total_latency"] += latency
    stats["last_error"] = str(error)

    # 同步到健康监控历史
    from services.health_monitor import health_monitor
    health_monitor.record_provider_call(provider, latency * 1000, success=False, error=str(error))

    logger.warning(
        "Provider failure recorded",
        provider=provider,
        failure_count=stats["count"],
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
        start_time = time.time()
        try:
            result = await coro_func(*args, **kwargs)
            latency = time.time() - start_time
            _record_provider_success(provider, latency)
            return result
        except Exception as e:
            latency = time.time() - start_time
            last_error = e
            _record_provider_failure(provider, e, latency)

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
    async def _get_cached_price(symbol: str) -> Optional[StockPrice]:
        """从缓存获取价格"""
        key = CACHE_KEY_PRICE.format(symbol=symbol)
        data = await cache_service.get_json(key)
        if data:
            logger.debug("Using cached price", symbol=symbol)
            # 处理 datetime 转换
            if isinstance(data.get('timestamp'), str):
                data['timestamp'] = datetime.fromisoformat(data['timestamp'])
            return StockPrice(**data)
        return None

    @staticmethod
    async def _set_cached_price(symbol: str, price: StockPrice):
        """设置价格缓存"""
        key = CACHE_KEY_PRICE.format(symbol=symbol)
        await cache_service.set_json(key, price.dict(), ttl=_CACHE_TTL_PRICE)

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
            # yfinance 对上交所使用 .SS 后缀（非 .SH）
            yf_symbol = re.sub(r'\.SH$', '.SS', symbol, flags=re.IGNORECASE)
            ticker = yf.Ticker(yf_symbol)
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
        获取股票价格（带请求去重、降级和熔断机制）

        优先级：
        - CN: akshare -> yfinance
        - HK/US: yfinance -> alpha_vantage

        特性：
        - 请求去重：多个并发请求同一股票只发起一次实际请求
        - 熔断保护：连续失败 5 次后跳过该数据源 60 秒
        - 失败时尝试使用缓存数据
        """
        # 1. 先检查缓存
        cached = await cls._get_cached_price(symbol)
        if cached:
            return cached

        # 2. 使用请求去重获取数据
        return await coalesce_request(
            f"price:{symbol}",
            cls._fetch_stock_price_impl,
            symbol
        )

    @classmethod
    async def _fetch_stock_price_impl(cls, symbol: str) -> StockPrice:
        """实际获取股票价格的实现（内部方法）"""
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

            start_time = time.time()
            try:
                if provider == "akshare":
                    price = await cls._get_price_akshare(symbol)
                elif provider == "yfinance":
                    price = await cls._get_price_yfinance(symbol, market)
                elif provider == "alpha_vantage":
                    price = await cls._get_price_alpha_vantage(symbol)
                else:
                    continue

                latency = time.time() - start_time
                _record_provider_success(provider, latency)
                # 成功获取，记录成功并缓存
                await cls._set_cached_price(symbol, price)
                logger.info("Price fetched successfully", symbol=symbol, provider=provider)
                return price

            except DataSourceError as e:
                latency = time.time() - start_time
                _record_provider_failure(provider, e, latency)
                logger.warning("Data source failed, trying next", symbol=symbol, source=e.source, error=str(e))
                last_error = e
                continue
            except Exception as e:
                latency = time.time() - start_time
                _record_provider_failure(provider, e, latency)
                logger.warning("Unexpected error, trying next provider", symbol=symbol, provider=provider, error=str(e))
                last_error = DataSourceError(provider, str(e))
                continue

        # 所有数据源都失败，尝试使用缓存（即使已过期，作为降级方案）
        # 注意：cache_service.get 会自动处理 TTL，如果需要 stale cache，
        # 可能需要 cache_service 支持获取过期数据，或者这里直接返回失败。
        # 目前 cache_service 不支持获取过期数据，所以这里如果缓存失效就真的失效了。
        cached = await cls._get_cached_price(symbol)
        if cached:
            logger.warning(
                "All providers failed, using cache",
                symbol=symbol,
                attempted=attempted_providers
            )
            return cached

        # 完全失败
        raise last_error or Exception(f"All data sources failed for {symbol}")

    @classmethod
    async def get_history(cls, symbol: str, period: str = "1mo") -> List[KlineData]:
        """获取历史 K 线数据（带降级和熔断机制）"""
        # 1. 检查缓存
        key = CACHE_KEY_HISTORY.format(symbol=symbol)
        cached = await cache_service.get_json(key)
        if cached:
            logger.debug("Using cached history", symbol=symbol)
            return [KlineData(**item) for item in cached]

        # 2. 获取数据
        market = cls.get_market(symbol)
        result = None

        # 尝试主数据源（A 股用 AkShare）
        if market == "CN" and _is_provider_available("akshare"):
            start_time = time.time()
            try:
                result = await cls._get_history_akshare(symbol)
                latency = time.time() - start_time
                _record_provider_success("akshare", latency)
            except Exception as e:
                latency = time.time() - start_time
                _record_provider_failure("akshare", e, latency)
                logger.warning("AkShare history failed, trying yfinance", symbol=symbol, error=str(e))

        # 降级到 yfinance
        if not result and _is_provider_available("yfinance"):
            start_time = time.time()
            try:
                result = await cls._get_history_yfinance(symbol, period)
                latency = time.time() - start_time
                _record_provider_success("yfinance", latency)
            except Exception as e:
                latency = time.time() - start_time
                _record_provider_failure("yfinance", e, latency)
                logger.error("yfinance history failed", symbol=symbol, error=str(e))

        if result:
            # 写入缓存
            await cache_service.set_json(key, [item.dict() for item in result], ttl=_CACHE_TTL_HISTORY)
            return result

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
        yf_symbol = re.sub(r'\.SH$', '.SS', symbol, flags=re.IGNORECASE)
        ticker = yf.Ticker(yf_symbol)
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
        # 1. 检查缓存
        key = CACHE_KEY_FUNDAMENTALS.format(symbol=symbol)
        cached = await cache_service.get_json(key)
        if cached:
            logger.debug("Using cached fundamentals", symbol=symbol)
            return CompanyFundamentals(**cached)

        # 2. 获取数据
        market = cls.get_market(symbol)
        ticker = yf.Ticker(symbol)
        info = ticker.info

        result = CompanyFundamentals(
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

        # 3. 写入缓存
        await cache_service.set_json(key, result.dict(), ttl=_CACHE_TTL_FUNDAMENTALS)
        return result

    @classmethod
    async def clear_cache(cls):
        """清除所有数据缓存"""
        # 清除匹配模式的键
        for pattern in ["market:price:*", "market:history:*", "market:fundamentals:*"]:
            keys = await cache_service.keys(pattern)
            for key in keys:
                await cache_service.delete(key)
        logger.info("All data caches cleared")

    @staticmethod
    def get_provider_status() -> Dict[str, Any]:
        """获取所有数据源的状态"""
        status = {}
        for provider in ["akshare", "yfinance", "alpha_vantage"]:
            _init_provider_stats(provider)
            stats = _provider_stats[provider]
            is_available = _is_provider_available(provider)
            
            avg_latency = 0
            if stats["total_requests"] > 0:
                avg_latency = (stats["total_latency"] / stats["total_requests"]) * 1000 # 转为毫秒

            status[provider] = {
                "available": is_available,
                "failure_count": stats["count"],
                "threshold": _FAILURE_THRESHOLD,
                "last_failure": stats["last_failure"].isoformat() if stats["last_failure"] else None,
                "cooldown_seconds": _FAILURE_COOLDOWN,
                "total_requests": stats["total_requests"],
                "successful_requests": stats["successful_requests"],
                "failed_requests": stats["failed_requests"],
                "avg_latency_ms": round(avg_latency, 2),
                "last_error": stats["last_error"]
            }
        return status

    @staticmethod
    def reset_provider(provider: str):
        """重置指定数据源的熔断状态"""
        if provider in _provider_stats:
            _provider_stats[provider]["count"] = 0
            _provider_stats[provider]["last_failure"] = None
            logger.info("Provider reset", provider=provider)

    @staticmethod
    def reset_all_providers():
        """重置所有数据源的熔断状态"""
        for provider in _provider_stats:
            _provider_stats[provider]["count"] = 0
            _provider_stats[provider]["last_failure"] = None
        logger.info("All providers reset")
