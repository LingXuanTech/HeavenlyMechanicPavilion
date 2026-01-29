from typing import Annotated, Optional, Callable, Any
import structlog
import time
import random

logger = structlog.get_logger(__name__)

# Import retry utilities
from .retry_utils import (
    CircuitBreaker,
    RateLimiter,
    CircuitBreakerOpenError,
    RateLimitExceededError,
    get_vendor_breaker,
    get_vendor_limiter,
)

# Import from vendor-specific modules
from .local import get_YFin_data, get_finnhub_news, get_finnhub_company_insider_sentiment, get_finnhub_company_insider_transactions, get_simfin_balance_sheet, get_simfin_cashflow, get_simfin_income_statements, get_reddit_global_news, get_reddit_company_news
from .y_finance import get_YFin_data_online, get_stock_stats_indicators_window, get_balance_sheet as get_yfinance_balance_sheet, get_cashflow as get_yfinance_cashflow, get_income_statement as get_yfinance_income_statement, get_insider_transactions as get_yfinance_insider_transactions
from .google import get_google_news
from .openai import get_stock_news_openai, get_global_news_openai, get_fundamentals_openai
from .alpha_vantage import (
    get_stock as get_alpha_vantage_stock,
    get_indicator as get_alpha_vantage_indicator,
    get_fundamentals as get_alpha_vantage_fundamentals,
    get_balance_sheet as get_alpha_vantage_balance_sheet,
    get_cashflow as get_alpha_vantage_cashflow,
    get_income_statement as get_alpha_vantage_income_statement,
    get_insider_transactions as get_alpha_vantage_insider_transactions,
    get_news as get_alpha_vantage_news
)
from .alpha_vantage_common import AlphaVantageRateLimitError
from .duckduckgo_search import search_market_news as ddg_search_market_news, search_stock_info as ddg_search_stock_info, search_trending_stocks as ddg_search_trending

# Configuration and routing logic
from .config import get_config

# Tools organized by category
TOOLS_CATEGORIES = {
    "core_stock_apis": {
        "description": "OHLCV stock price data",
        "tools": [
            "get_stock_data"
        ]
    },
    "technical_indicators": {
        "description": "Technical analysis indicators",
        "tools": [
            "get_indicators"
        ]
    },
    "fundamental_data": {
        "description": "Company fundamentals",
        "tools": [
            "get_fundamentals",
            "get_balance_sheet",
            "get_cashflow",
            "get_income_statement"
        ]
    },
    "news_data": {
        "description": "News (public/insiders, original/processed)",
        "tools": [
            "get_news",
            "get_global_news",
            "get_insider_sentiment",
            "get_insider_transactions",
        ]
    },
    "search_data": {
        "description": "Web search and stock discovery",
        "tools": [
            "search_market_news",
            "search_stock_info",
            "search_trending_stocks",
        ]
    }
}

VENDOR_LIST = [
    "local",
    "yfinance",
    "openai",
    "google",
    "duckduckgo"
]

# Mapping of methods to their vendor-specific implementations
VENDOR_METHODS = {
    # core_stock_apis
    "get_stock_data": {
        "alpha_vantage": get_alpha_vantage_stock,
        "yfinance": get_YFin_data_online,
        "local": get_YFin_data,
    },
    # technical_indicators
    "get_indicators": {
        "alpha_vantage": get_alpha_vantage_indicator,
        "yfinance": get_stock_stats_indicators_window,
        "local": get_stock_stats_indicators_window
    },
    # fundamental_data
    "get_fundamentals": {
        "alpha_vantage": get_alpha_vantage_fundamentals,
        "openai": get_fundamentals_openai,
    },
    "get_balance_sheet": {
        "alpha_vantage": get_alpha_vantage_balance_sheet,
        "yfinance": get_yfinance_balance_sheet,
        "local": get_simfin_balance_sheet,
    },
    "get_cashflow": {
        "alpha_vantage": get_alpha_vantage_cashflow,
        "yfinance": get_yfinance_cashflow,
        "local": get_simfin_cashflow,
    },
    "get_income_statement": {
        "alpha_vantage": get_alpha_vantage_income_statement,
        "yfinance": get_yfinance_income_statement,
        "local": get_simfin_income_statements,
    },
    # news_data
    "get_news": {
        "alpha_vantage": get_alpha_vantage_news,
        "openai": get_stock_news_openai,
        "google": get_google_news,
        "local": [get_finnhub_news, get_reddit_company_news, get_google_news],
    },
    "get_global_news": {
        "openai": get_global_news_openai,
        "local": get_reddit_global_news
    },
    "get_insider_sentiment": {
        "local": get_finnhub_company_insider_sentiment
    },
    "get_insider_transactions": {
        "alpha_vantage": get_alpha_vantage_insider_transactions,
        "yfinance": get_yfinance_insider_transactions,
        "local": get_finnhub_company_insider_transactions,
    },
    # search_data
    "search_market_news": {
        "duckduckgo": ddg_search_market_news,
    },
    "search_stock_info": {
        "duckduckgo": ddg_search_stock_info,
    },
    "search_trending_stocks": {
        "duckduckgo": ddg_search_trending,
    },
}

def get_category_for_method(method: str) -> str:
    """Get the category that contains the specified method."""
    for category, info in TOOLS_CATEGORIES.items():
        if method in info["tools"]:
            return category
    raise ValueError(f"Method '{method}' not found in any category")


def _call_with_retry(
    func: Callable[..., Any],
    vendor: str,
    max_retries: int = 3,
    base_delay: float = 1.0,
    *args,
    **kwargs
) -> Any:
    """
    Call a vendor function with retry, circuit breaker, and rate limiting.

    Args:
        func: The function to call
        vendor: Vendor name (for breaker/limiter lookup)
        max_retries: Maximum number of retry attempts
        base_delay: Base delay between retries (seconds)
        *args, **kwargs: Arguments to pass to the function

    Returns:
        The function result

    Raises:
        CircuitBreakerOpenError: If circuit breaker is open
        RateLimitExceededError: If rate limit exceeded
        Exception: The last exception if all retries fail
    """
    # Get vendor-specific breaker and limiter
    breaker = get_vendor_breaker(vendor)
    limiter = get_vendor_limiter(vendor)

    # Check circuit breaker
    if breaker and not breaker.allow_request():
        logger.warning(
            "Circuit breaker is open",
            vendor=vendor,
            function=func.__name__
        )
        raise CircuitBreakerOpenError(f"Circuit breaker for {vendor} is open")

    # Rate limiting
    if limiter and not limiter.acquire(block=True, timeout=30.0):
        raise RateLimitExceededError(f"Rate limit exceeded for {vendor}")

    last_error: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        try:
            result = func(*args, **kwargs)

            # Record success to circuit breaker
            if breaker:
                breaker._record_success()

            return result

        except (CircuitBreakerOpenError, RateLimitExceededError):
            raise
        except Exception as e:
            last_error = e

            # Record failure to circuit breaker
            if breaker:
                breaker._record_failure(e)

            if attempt == max_retries:
                logger.error(
                    "All retry attempts failed",
                    vendor=vendor,
                    function=func.__name__,
                    attempts=attempt + 1,
                    error=str(e)
                )
                raise

            # Check if error is retryable
            error_str = str(e).lower()
            retryable_keywords = [
                "connection", "timeout", "reset", "refused",
                "unavailable", "temporary", "rate limit",
                "too many requests", "503", "502", "500"
            ]
            is_retryable = any(kw in error_str for kw in retryable_keywords)

            if not is_retryable:
                logger.debug(
                    "Non-retryable error, not retrying",
                    vendor=vendor,
                    function=func.__name__,
                    error=str(e)
                )
                raise

            # Calculate delay with jitter
            delay = min(base_delay * (2 ** attempt), 30.0)
            delay = delay * (0.5 + random.random())

            logger.warning(
                "Vendor call failed, retrying",
                vendor=vendor,
                function=func.__name__,
                attempt=attempt + 1,
                max_retries=max_retries,
                delay=round(delay, 2),
                error=str(e)
            )

            time.sleep(delay)

    raise last_error  # type: ignore

def get_vendor(category: str, method: str = None) -> str:
    """Get the configured vendor for a data category or specific tool method.
    Tool-level configuration takes precedence over category-level.
    """
    config = get_config()

    # Check tool-level configuration first (if method provided)
    if method:
        tool_vendors = config.get("tool_vendors", {})
        if method in tool_vendors:
            return tool_vendors[method]

    # Fall back to category-level configuration
    return config.get("data_vendors", {}).get(category, "default")

def route_to_vendor(method: str, *args, **kwargs):
    """Route method calls to appropriate vendor implementation with fallback support."""
    category = get_category_for_method(method)
    vendor_config = get_vendor(category, method)

    # Handle comma-separated vendors
    primary_vendors = [v.strip() for v in vendor_config.split(',')]

    if method not in VENDOR_METHODS:
        raise ValueError(f"Method '{method}' not supported")

    # Get all available vendors for this method for fallback
    all_available_vendors = list(VENDOR_METHODS[method].keys())
    
    # Create fallback vendor list: primary vendors first, then remaining vendors as fallbacks
    fallback_vendors = primary_vendors.copy()
    for vendor in all_available_vendors:
        if vendor not in fallback_vendors:
            fallback_vendors.append(vendor)

    # Log fallback ordering
    logger.debug(
        "Vendor routing configured",
        method=method,
        primary_vendors=primary_vendors,
        fallback_order=fallback_vendors
    )

    # Track results and execution state
    results = []
    vendor_attempt_count = 0
    any_primary_vendor_attempted = False
    successful_vendor = None

    for vendor in fallback_vendors:
        if vendor not in VENDOR_METHODS[method]:
            if vendor in primary_vendors:
                logger.info(
                    "Vendor not supported for method, falling back",
                    vendor=vendor,
                    method=method
                )
            continue

        vendor_impl = VENDOR_METHODS[method][vendor]
        is_primary_vendor = vendor in primary_vendors
        vendor_attempt_count += 1

        # Track if we attempted any primary vendor
        if is_primary_vendor:
            any_primary_vendor_attempted = True

        logger.debug(
            "Attempting vendor",
            vendor=vendor,
            method=method,
            vendor_type="primary" if is_primary_vendor else "fallback",
            attempt_number=vendor_attempt_count
        )

        # Handle list of methods for a vendor
        if isinstance(vendor_impl, list):
            vendor_methods = [(impl, vendor) for impl in vendor_impl]
            logger.debug("Vendor has multiple implementations", vendor=vendor, count=len(vendor_methods))
        else:
            vendor_methods = [(vendor_impl, vendor)]

        # Run methods for this vendor with retry support
        vendor_results = []
        for impl_func, vendor_name in vendor_methods:
            try:
                logger.debug("Calling vendor function", function=impl_func.__name__, vendor=vendor_name)
                # Use retry wrapper for robustness
                result = _call_with_retry(impl_func, vendor_name, 3, 1.0, *args, **kwargs)
                vendor_results.append(result)
                logger.info("Vendor function succeeded", function=impl_func.__name__, vendor=vendor_name)

            except CircuitBreakerOpenError as e:
                logger.warning(
                    "Circuit breaker open, skipping vendor",
                    vendor=vendor_name,
                    error=str(e)
                )
                continue
            except RateLimitExceededError as e:
                logger.warning(
                    "Rate limit exceeded, skipping vendor",
                    vendor=vendor_name,
                    error=str(e)
                )
                continue
            except AlphaVantageRateLimitError as e:
                if vendor == "alpha_vantage":
                    logger.warning(
                        "Alpha Vantage rate limit exceeded, falling back",
                        error=str(e)
                    )
                # Continue to next vendor for fallback
                continue
            except Exception as e:
                # Log error but continue with other implementations
                logger.warning(
                    "Vendor function failed",
                    function=impl_func.__name__,
                    vendor=vendor_name,
                    error=str(e)
                )
                continue

        # Add this vendor's results
        if vendor_results:
            results.extend(vendor_results)
            successful_vendor = vendor
            logger.info(
                "Vendor succeeded",
                vendor=vendor,
                result_count=len(vendor_results)
            )

            # Stopping logic: Stop after first successful vendor for single-vendor configs
            # Multiple vendor configs (comma-separated) may want to collect from multiple sources
            if len(primary_vendors) == 1:
                logger.debug("Stopping after successful vendor (single-vendor config)", vendor=vendor)
                break
        else:
            logger.debug("Vendor produced no results", vendor=vendor)

    # Final result summary
    if not results:
        logger.error(
            "All vendor attempts failed",
            method=method,
            attempts=vendor_attempt_count
        )
        raise RuntimeError(f"All vendor implementations failed for method '{method}'")
    else:
        logger.info(
            "Method completed",
            method=method,
            result_count=len(results),
            vendor_attempts=vendor_attempt_count
        )

    # Return single result if only one, otherwise concatenate as string
    if len(results) == 1:
        return results[0]
    else:
        # Convert all results to strings and concatenate
        return '\n'.join(str(result) for result in results)