"""
AkShare 鲁棒性增强封装

提供带有重试、熔断、限流功能的 AkShare API 封装：
- 自动重试（指数退避）
- 熔断保护（防止雪崩）
- 请求限流（防止触发 API 限制）
- 统一异常处理
"""

import asyncio
from typing import Callable, TypeVar, Any, Optional
from functools import wraps
import pandas as pd
import structlog

from .retry_utils import (
    CircuitBreaker,
    RateLimiter,
    CircuitBreakerOpenError,
    RateLimitExceededError,
    retry_with_backoff,
    akshare_breaker,
    akshare_limiter,
)

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class AkShareError(Exception):
    """AkShare 调用异常"""
    def __init__(self, function: str, message: str, original_error: Optional[Exception] = None):
        self.function = function
        self.original_error = original_error
        super().__init__(f"AkShare {function}: {message}")


class AkShareEmptyDataError(AkShareError):
    """AkShare 返回空数据"""
    pass


class AkShareConnectionError(AkShareError):
    """AkShare 连接异常"""
    pass


class AkShareRateLimitError(AkShareError):
    """AkShare 限流异常"""
    pass


def _is_retryable_error(error: Exception) -> bool:
    """判断是否为可重试的异常"""
    retryable_messages = [
        "connection",
        "timeout",
        "reset",
        "refused",
        "unavailable",
        "temporary",
        "rate limit",
        "too many requests",
        "503",
        "502",
        "500",
    ]
    error_str = str(error).lower()
    return any(msg in error_str for msg in retryable_messages)


def robust_akshare_call(
    func_name: str,
    max_retries: int = 3,
    base_delay: float = 1.0,
    require_data: bool = True,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    AkShare 函数鲁棒性装饰器

    Args:
        func_name: AkShare 函数名称（用于日志）
        max_retries: 最大重试次数
        base_delay: 基础重试延迟（秒）
        require_data: 是否要求返回非空数据

    Usage:
        @robust_akshare_call("stock_zh_a_spot_em")
        def get_stock_data():
            return ak.stock_zh_a_spot_em()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # 检查熔断器
            if not akshare_breaker.allow_request():
                logger.warning(
                    "AkShare circuit breaker is open",
                    function=func_name,
                    state=akshare_breaker.state.value
                )
                raise CircuitBreakerOpenError(
                    f"AkShare circuit breaker is open for {func_name}"
                )

            # 限流
            if not akshare_limiter.acquire(block=True, timeout=30.0):
                raise AkShareRateLimitError(func_name, "Rate limit exceeded")

            last_error: Optional[Exception] = None

            for attempt in range(max_retries + 1):
                try:
                    result = func(*args, **kwargs)

                    # 检查返回数据
                    if require_data:
                        if result is None:
                            raise AkShareEmptyDataError(func_name, "Returned None")
                        if isinstance(result, pd.DataFrame) and result.empty:
                            raise AkShareEmptyDataError(func_name, "Returned empty DataFrame")

                    # 成功，记录到熔断器
                    akshare_breaker._record_success()

                    logger.debug(
                        "AkShare call succeeded",
                        function=func_name,
                        attempt=attempt + 1
                    )
                    return result

                except (CircuitBreakerOpenError, RateLimitExceededError):
                    raise
                except AkShareEmptyDataError:
                    # 空数据不重试
                    akshare_breaker._record_failure(last_error or Exception("Empty data"))
                    raise
                except Exception as e:
                    last_error = e

                    if attempt == max_retries:
                        # 最后一次尝试失败
                        akshare_breaker._record_failure(e)
                        logger.error(
                            "AkShare call failed after retries",
                            function=func_name,
                            attempts=attempt + 1,
                            error=str(e)
                        )
                        raise AkShareError(func_name, str(e), e)

                    if not _is_retryable_error(e):
                        # 不可重试的错误
                        akshare_breaker._record_failure(e)
                        raise AkShareError(func_name, str(e), e)

                    # 计算重试延迟
                    import random
                    delay = min(base_delay * (2 ** attempt), 30.0)
                    delay = delay * (0.5 + random.random())

                    logger.warning(
                        "AkShare call failed, retrying",
                        function=func_name,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay=delay,
                        error=str(e)
                    )

                    import time
                    time.sleep(delay)

            raise AkShareError(func_name, "Max retries exceeded", last_error)

        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            """异步版本：在线程池中执行同步的 AkShare 调用"""
            return await asyncio.to_thread(wrapper, *args, **kwargs)

        # 返回异步版本
        return async_wrapper

    return decorator


# ============ 预封装的 AkShare 函数 ============

import akshare as ak


@robust_akshare_call("stock_zh_a_spot_em")
def _get_a_stock_realtime() -> pd.DataFrame:
    """A 股实时行情"""
    return ak.stock_zh_a_spot_em()


@robust_akshare_call("stock_zh_a_hist")
def _get_a_stock_history(symbol: str, period: str = "daily", adjust: str = "qfq") -> pd.DataFrame:
    """A 股历史行情"""
    return ak.stock_zh_a_hist(symbol=symbol, period=period, adjust=adjust)


@robust_akshare_call("stock_hsgt_north_net_flow_in_em")
def _get_north_money_flow() -> pd.DataFrame:
    """北向资金流向"""
    return ak.stock_hsgt_north_net_flow_in_em()


@robust_akshare_call("stock_hsgt_hold_stock_em")
def _get_north_holding(market: str = "北向", indicator: str = "今日排行") -> pd.DataFrame:
    """北向持股"""
    return ak.stock_hsgt_hold_stock_em(market=market, indicator=indicator)


@robust_akshare_call("stock_lhb_detail_em")
def _get_lhb_detail(start_date: str, end_date: str) -> pd.DataFrame:
    """龙虎榜明细"""
    return ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)


@robust_akshare_call("stock_lhb_jgmmtj_em")
def _get_lhb_institution(start_date: str, end_date: str) -> pd.DataFrame:
    """龙虎榜机构买卖统计"""
    return ak.stock_lhb_jgmmtj_em(start_date=start_date, end_date=end_date)


@robust_akshare_call("stock_restricted_release_calendar_em", require_data=False)
def _get_jiejin_calendar(start_date: str, end_date: str) -> pd.DataFrame:
    """限售解禁日历"""
    return ak.stock_restricted_release_calendar_em(start_date=start_date, end_date=end_date)


@robust_akshare_call("index_zh_a_hist")
def _get_index_history(symbol: str, period: str = "daily") -> pd.DataFrame:
    """指数历史行情"""
    return ak.index_zh_a_hist(symbol=symbol, period=period)


@robust_akshare_call("stock_individual_info_em")
def _get_stock_info(symbol: str) -> pd.DataFrame:
    """个股基本信息"""
    return ak.stock_individual_info_em(symbol=symbol)


@robust_akshare_call("stock_news_em")
def _get_stock_news(symbol: str) -> pd.DataFrame:
    """个股新闻"""
    return ak.stock_news_em(symbol=symbol)


# ============ 公开 API ============

class RobustAkShare:
    """
    AkShare 鲁棒性封装类

    所有方法都是异步的，自带重试、熔断、限流保护。

    Usage:
        aks = RobustAkShare()
        df = await aks.get_a_stock_realtime()
    """

    async def get_a_stock_realtime(self) -> pd.DataFrame:
        """获取 A 股实时行情"""
        return await _get_a_stock_realtime()

    async def get_a_stock_history(
        self,
        symbol: str,
        period: str = "daily",
        adjust: str = "qfq"
    ) -> pd.DataFrame:
        """获取 A 股历史行情"""
        return await _get_a_stock_history(symbol, period, adjust)

    async def get_north_money_flow(self) -> pd.DataFrame:
        """获取北向资金流向"""
        return await _get_north_money_flow()

    async def get_north_holding(
        self,
        market: str = "北向",
        indicator: str = "今日排行"
    ) -> pd.DataFrame:
        """获取北向持股"""
        return await _get_north_holding(market, indicator)

    async def get_lhb_detail(self, start_date: str, end_date: str) -> pd.DataFrame:
        """获取龙虎榜明细"""
        return await _get_lhb_detail(start_date, end_date)

    async def get_lhb_institution(self, start_date: str, end_date: str) -> pd.DataFrame:
        """获取龙虎榜机构买卖统计"""
        return await _get_lhb_institution(start_date, end_date)

    async def get_jiejin_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        """获取限售解禁日历"""
        return await _get_jiejin_calendar(start_date, end_date)

    async def get_index_history(self, symbol: str, period: str = "daily") -> pd.DataFrame:
        """获取指数历史行情"""
        return await _get_index_history(symbol, period)

    async def get_stock_info(self, symbol: str) -> pd.DataFrame:
        """获取个股基本信息"""
        return await _get_stock_info(symbol)

    async def get_stock_news(self, symbol: str) -> pd.DataFrame:
        """获取个股新闻"""
        return await _get_stock_news(symbol)

    @staticmethod
    def get_circuit_breaker_status() -> dict:
        """获取熔断器状态"""
        return {
            "state": akshare_breaker.state.value,
            "failure_count": akshare_breaker._failure_count,
            "failure_threshold": akshare_breaker.failure_threshold,
            "recovery_timeout": akshare_breaker.recovery_timeout,
        }

    @staticmethod
    def reset_circuit_breaker():
        """重置熔断器"""
        akshare_breaker.reset()


# 单例实例
robust_akshare = RobustAkShare()
