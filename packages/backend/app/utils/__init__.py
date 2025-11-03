"""Utility modules for the backend application."""

# Lazy imports for performance optimization
# Import utilities only when needed to reduce startup time

__all__ = [
    "PerformanceTimer",
    "batch_execute",
    "memoize",
    "async_memoize",
    "timed_lru_cache",
    "cached_property",
    "rate_limit",
]


def __getattr__(name: str):
    """Lazy load utility functions on first access."""
    if name in __all__:
        from .performance import (
            PerformanceTimer,
            async_memoize,
            batch_execute,
            cached_property,
            memoize,
            rate_limit,
            timed_lru_cache,
        )

        globals().update(
            {
                "PerformanceTimer": PerformanceTimer,
                "batch_execute": batch_execute,
                "memoize": memoize,
                "async_memoize": async_memoize,
                "timed_lru_cache": timed_lru_cache,
                "cached_property": cached_property,
                "rate_limit": rate_limit,
            }
        )
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
