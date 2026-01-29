"""
重试、熔断、限流工具模块

提供数据源调用的鲁棒性保障：
- CircuitBreaker: 熔断器，连续失败后短路
- RateLimiter: 令牌桶限流器
- retry_with_backoff: 指数退避重试装饰器
"""

import time
import asyncio
import functools
from typing import Callable, TypeVar, Optional, Any, Set
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import deque
import threading
import structlog

logger = structlog.get_logger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"      # 正常，允许请求
    OPEN = "open"          # 熔断，拒绝请求
    HALF_OPEN = "half_open"  # 半开，允许少量探测请求


@dataclass
class CircuitBreaker:
    """
    熔断器：连续失败 N 次后短路 M 秒

    状态转换:
    - CLOSED -> OPEN: 连续失败次数达到阈值
    - OPEN -> HALF_OPEN: 熔断时间过后
    - HALF_OPEN -> CLOSED: 探测请求成功
    - HALF_OPEN -> OPEN: 探测请求失败

    Usage:
        breaker = CircuitBreaker(name="akshare", failure_threshold=3, recovery_timeout=60)

        @breaker
        def fetch_data():
            ...
    """
    name: str
    failure_threshold: int = 5          # 连续失败次数阈值
    recovery_timeout: float = 60.0      # 熔断恢复时间（秒）
    half_open_max_calls: int = 1        # 半开状态最大探测次数

    # 内部状态
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: Optional[datetime] = field(default=None, init=False)
    _half_open_calls: int = field(default=0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    @property
    def state(self) -> CircuitState:
        with self._lock:
            return self._get_state()

    def _get_state(self) -> CircuitState:
        """获取当前状态（需在锁内调用）"""
        if self._state == CircuitState.OPEN:
            # 检查是否应该转换到半开状态
            if self._last_failure_time:
                elapsed = (datetime.now() - self._last_failure_time).total_seconds()
                if elapsed >= self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    logger.info(
                        "Circuit breaker transitioning to half-open",
                        name=self.name,
                        elapsed_seconds=elapsed
                    )
        return self._state

    def _record_success(self) -> None:
        """记录成功调用"""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                # 半开状态下成功，恢复到关闭状态
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._last_failure_time = None
                logger.info("Circuit breaker closed after successful probe", name=self.name)
            elif self._state == CircuitState.CLOSED:
                # 关闭状态下成功，重置失败计数
                self._failure_count = 0

    def _record_failure(self, error: Exception) -> None:
        """记录失败调用"""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now()

            if self._state == CircuitState.HALF_OPEN:
                # 半开状态下失败，重新打开熔断器
                self._state = CircuitState.OPEN
                logger.warning(
                    "Circuit breaker reopened after failed probe",
                    name=self.name,
                    error=str(error)
                )
            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    logger.warning(
                        "Circuit breaker opened",
                        name=self.name,
                        failure_count=self._failure_count,
                        threshold=self.failure_threshold,
                        error=str(error)
                    )

    def allow_request(self) -> bool:
        """检查是否允许请求"""
        with self._lock:
            state = self._get_state()

            if state == CircuitState.CLOSED:
                return True
            elif state == CircuitState.OPEN:
                return False
            elif state == CircuitState.HALF_OPEN:
                if self._half_open_calls < self.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
        return False

    def reset(self) -> None:
        """手动重置熔断器"""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._last_failure_time = None
            self._half_open_calls = 0
            logger.info("Circuit breaker manually reset", name=self.name)

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """装饰器模式"""
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            if not self.allow_request():
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is open, request rejected"
                )

            try:
                result = func(*args, **kwargs)
                self._record_success()
                return result
            except Exception as e:
                self._record_failure(e)
                raise

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            if not self.allow_request():
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is open, request rejected"
                )

            try:
                result = await func(*args, **kwargs)
                self._record_success()
                return result
            except Exception as e:
                self._record_failure(e)
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper


class CircuitBreakerOpenError(Exception):
    """熔断器打开异常"""
    pass


@dataclass
class RateLimiter:
    """
    令牌桶限流器

    Usage:
        limiter = RateLimiter(rate=10, per=60)  # 每 60 秒最多 10 次请求

        @limiter
        def fetch_data():
            ...

        # 或手动检查
        if limiter.acquire():
            fetch_data()
    """
    rate: int                           # 令牌数量
    per: float = 60.0                   # 时间窗口（秒）

    _tokens: float = field(init=False)
    _last_update: float = field(init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def __post_init__(self) -> None:
        self._tokens = float(self.rate)
        self._last_update = time.monotonic()

    def _refill(self) -> None:
        """补充令牌（需在锁内调用）"""
        now = time.monotonic()
        elapsed = now - self._last_update
        refill_amount = elapsed * (self.rate / self.per)
        self._tokens = min(self.rate, self._tokens + refill_amount)
        self._last_update = now

    def acquire(self, tokens: int = 1, block: bool = True, timeout: Optional[float] = None) -> bool:
        """
        获取令牌

        Args:
            tokens: 需要的令牌数量
            block: 是否阻塞等待
            timeout: 最大等待时间（秒）

        Returns:
            是否成功获取令牌
        """
        deadline = time.monotonic() + (timeout or float('inf')) if block else time.monotonic()

        while True:
            with self._lock:
                self._refill()

                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True

                if not block or time.monotonic() >= deadline:
                    return False

                # 计算需要等待的时间
                tokens_needed = tokens - self._tokens
                wait_time = tokens_needed * (self.per / self.rate)

            # 在锁外等待
            time.sleep(min(wait_time, 0.1))

    async def acquire_async(self, tokens: int = 1, timeout: Optional[float] = None) -> bool:
        """异步获取令牌"""
        deadline = time.monotonic() + (timeout or float('inf'))

        while True:
            with self._lock:
                self._refill()

                if self._tokens >= tokens:
                    self._tokens -= tokens
                    return True

                if time.monotonic() >= deadline:
                    return False

                tokens_needed = tokens - self._tokens
                wait_time = tokens_needed * (self.per / self.rate)

            await asyncio.sleep(min(wait_time, 0.1))

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """装饰器模式"""
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            if not self.acquire(block=True, timeout=30.0):
                raise RateLimitExceededError("Rate limit exceeded, request rejected")
            return func(*args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            if not await self.acquire_async(timeout=30.0):
                raise RateLimitExceededError("Rate limit exceeded, request rejected")
            return func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper


class RateLimitExceededError(Exception):
    """限流超出异常"""
    pass


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (Exception,),
    non_retryable_exceptions: tuple = (),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    指数退避重试装饰器

    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        exponential_base: 指数基数
        jitter: 是否添加随机抖动
        retryable_exceptions: 可重试的异常类型
        non_retryable_exceptions: 不可重试的异常类型（优先级高于 retryable_exceptions）
        on_retry: 重试回调函数

    Usage:
        @retry_with_backoff(max_retries=3, base_delay=1.0)
        def fetch_data():
            ...
    """
    import random

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except non_retryable_exceptions:
                    raise
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            "Max retries exceeded",
                            function=func.__name__,
                            attempts=attempt + 1,
                            error=str(e)
                        )
                        raise

                    # 计算延迟
                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        "Retry attempt",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay=delay,
                        error=str(e)
                    )

                    if on_retry:
                        on_retry(e, attempt + 1)

                    time.sleep(delay)

            raise last_exception  # type: ignore

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except non_retryable_exceptions:
                    raise
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        logger.error(
                            "Max retries exceeded",
                            function=func.__name__,
                            attempts=attempt + 1,
                            error=str(e)
                        )
                        raise

                    delay = min(base_delay * (exponential_base ** attempt), max_delay)
                    if jitter:
                        delay = delay * (0.5 + random.random())

                    logger.warning(
                        "Retry attempt",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay=delay,
                        error=str(e)
                    )

                    if on_retry:
                        on_retry(e, attempt + 1)

                    await asyncio.sleep(delay)

            raise last_exception  # type: ignore

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return wrapper

    return decorator


# ============ 预配置的熔断器和限流器实例 ============

# AkShare 熔断器（连续 5 次失败后熔断 60 秒）
akshare_breaker = CircuitBreaker(
    name="akshare",
    failure_threshold=5,
    recovery_timeout=60.0
)

# AkShare 限流器（每分钟最多 30 次请求）
akshare_limiter = RateLimiter(rate=30, per=60.0)

# yfinance 熔断器
yfinance_breaker = CircuitBreaker(
    name="yfinance",
    failure_threshold=5,
    recovery_timeout=60.0
)

# yfinance 限流器（每分钟最多 60 次请求）
yfinance_limiter = RateLimiter(rate=60, per=60.0)

# Alpha Vantage 限流器（免费版：每分钟 5 次）
alpha_vantage_limiter = RateLimiter(rate=5, per=60.0)

# Alpha Vantage 熔断器
alpha_vantage_breaker = CircuitBreaker(
    name="alpha_vantage",
    failure_threshold=3,
    recovery_timeout=120.0
)


def get_vendor_breaker(vendor: str) -> Optional[CircuitBreaker]:
    """根据 vendor 名称获取对应的熔断器"""
    breakers = {
        "akshare": akshare_breaker,
        "yfinance": yfinance_breaker,
        "alpha_vantage": alpha_vantage_breaker,
    }
    return breakers.get(vendor)


def get_vendor_limiter(vendor: str) -> Optional[RateLimiter]:
    """根据 vendor 名称获取对应的限流器"""
    limiters = {
        "akshare": akshare_limiter,
        "yfinance": yfinance_limiter,
        "alpha_vantage": alpha_vantage_limiter,
    }
    return limiters.get(vendor)


# ============ 组合装饰器 ============

def robust_call(
    vendor: str,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    组合装饰器：限流 + 熔断 + 重试

    Usage:
        @robust_call("akshare")
        def fetch_data():
            ...
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        breaker = get_vendor_breaker(vendor)
        limiter = get_vendor_limiter(vendor)

        # 应用重试
        retried_func = retry_with_backoff(
            max_retries=max_retries,
            base_delay=base_delay,
            non_retryable_exceptions=(CircuitBreakerOpenError, RateLimitExceededError),
        )(func)

        # 应用熔断
        if breaker:
            retried_func = breaker(retried_func)

        # 应用限流
        if limiter:
            retried_func = limiter(retried_func)

        return retried_func

    return decorator
