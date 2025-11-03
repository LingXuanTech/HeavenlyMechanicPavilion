"""Performance optimization utilities for the backend."""

from __future__ import annotations

import asyncio
import functools
import hashlib
import json
import logging
import time
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def cached_property(func: Callable) -> property:
    """Decorator to cache property values after first access.

    Args:
        func: The property method to cache.

    Returns:
        A cached property.
    """
    attr_name = f"_cached_{func.__name__}"

    @functools.wraps(func)
    def wrapper(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, func(self))
        return getattr(self, attr_name)

    return property(wrapper)


def memoize(maxsize: int = 128, typed: bool = False):
    """Decorator to memoize function results with LRU cache.

    Args:
        maxsize: Maximum cache size.
        typed: If True, arguments of different types cached separately.

    Returns:
        Decorated function with caching.
    """

    def decorator(func: Callable) -> Callable:
        return functools.lru_cache(maxsize=maxsize, typed=typed)(func)

    return decorator


def async_memoize(maxsize: int = 128):
    """Decorator to memoize async function results.

    Args:
        maxsize: Maximum cache size.

    Returns:
        Decorated async function with caching.
    """

    def decorator(func: Callable) -> Callable:
        cache: dict[str, Any] = {}
        cache_order: list[str] = []

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Create cache key from arguments
            key_data = json.dumps(
                {"args": args, "kwargs": kwargs}, sort_keys=True, default=str
            )
            cache_key = hashlib.md5(key_data.encode()).hexdigest()

            # Return cached result if available
            if cache_key in cache:
                logger.debug(f"Cache hit for {func.__name__}")
                return cache[cache_key]

            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache[cache_key] = result
            cache_order.append(cache_key)

            # Evict oldest entries if cache is full
            while len(cache) > maxsize:
                oldest_key = cache_order.pop(0)
                cache.pop(oldest_key, None)

            return result

        return wrapper

    return decorator


def timed_lru_cache(seconds: int, maxsize: int = 128):
    """Decorator to cache function results with time-based expiration.

    Args:
        seconds: Cache expiration time in seconds.
        maxsize: Maximum cache size.

    Returns:
        Decorated function with time-based caching.
    """

    def decorator(func: Callable) -> Callable:
        func = functools.lru_cache(maxsize=maxsize)(func)
        func.lifetime = seconds
        func.expiration = time.time() + seconds

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if time.time() >= func.expiration:
                func.cache_clear()
                func.expiration = time.time() + func.lifetime
            return func(*args, **kwargs)

        wrapper.cache_info = func.cache_info
        wrapper.cache_clear = func.cache_clear
        return wrapper

    return decorator


async def batch_execute(
    items: list[T],
    async_func: Callable[[T], Any],
    batch_size: int = 10,
    delay: float = 0.1,
) -> list[Any]:
    """Execute async function on items in batches to avoid overwhelming resources.

    Args:
        items: List of items to process.
        async_func: Async function to apply to each item.
        batch_size: Number of items to process concurrently.
        delay: Delay between batches in seconds.

    Returns:
        List of results from processing all items.
    """
    results = []

    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        batch_results = await asyncio.gather(
            *[async_func(item) for item in batch], return_exceptions=True
        )
        results.extend(batch_results)

        # Add delay between batches to avoid rate limits
        if i + batch_size < len(items) and delay > 0:
            await asyncio.sleep(delay)

    return results


class PerformanceTimer:
    """Context manager for timing code execution."""

    def __init__(self, name: str = "Operation", log_level: int = logging.DEBUG):
        """Initialize the performance timer.

        Args:
            name: Name of the operation being timed.
            log_level: Logging level for the timing message.
        """
        self.name = name
        self.log_level = log_level
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def __enter__(self):
        """Start the timer."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop the timer and log the duration."""
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        logger.log(self.log_level, f"{self.name} completed in {duration:.3f}s")

    @property
    def duration(self) -> Optional[float]:
        """Get the duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None


def rate_limit(calls: int, period: int):
    """Decorator to rate limit function calls.

    Args:
        calls: Number of calls allowed.
        period: Time period in seconds.

    Returns:
        Decorated function with rate limiting.
    """
    call_times: list[float] = []

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            now = time.time()
            # Remove old calls outside the time window
            while call_times and call_times[0] < now - period:
                call_times.pop(0)

            # Check rate limit
            if len(call_times) >= calls:
                sleep_time = call_times[0] + period - now
                logger.warning(
                    f"Rate limit reached for {func.__name__}, "
                    f"sleeping {sleep_time:.2f}s"
                )
                await asyncio.sleep(sleep_time)

            call_times.append(now)
            return await func(*args, **kwargs)

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            now = time.time()
            while call_times and call_times[0] < now - period:
                call_times.pop(0)

            if len(call_times) >= calls:
                sleep_time = call_times[0] + period - now
                logger.warning(
                    f"Rate limit reached for {func.__name__}, "
                    f"sleeping {sleep_time:.2f}s"
                )
                time.sleep(sleep_time)

            call_times.append(now)
            return func(*args, **kwargs)

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
