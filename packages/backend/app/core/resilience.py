"""Resilience utilities: retries with exponential backoff and circuit breakers."""

from __future__ import annotations

import asyncio
import inspect
import logging
import random
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple, Type, TypeVar

from .errors import CircuitBreakerOpenError, TAE, TradingAgentsError, VendorAPIError

T = TypeVar("T")


@dataclass(slots=True)
class RetryPolicy:
    """Configuration for retrying operations with exponential backoff."""

    max_attempts: int = 3
    initial_backoff: float = 0.5
    max_backoff: float = 30.0
    multiplier: float = 2.0
    jitter: float = 0.1
    retry_exceptions: Tuple[type[BaseException], ...] = (Exception,)

    def backoff(self, attempt: int) -> float:
        """Calculate the backoff delay for a given attempt (1-indexed)."""
        base = self.initial_backoff * (self.multiplier ** max(attempt - 1, 0))
        delay = min(base, self.max_backoff)
        if self.jitter > 0:
            delay += random.uniform(0, self.jitter)
        return delay


class CircuitBreakerState(str, Enum):
    """Finite state machine for a circuit breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Tracks failures for an external dependency and trips when unstable."""

    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_success_threshold: int = 1,
        name: str | None = None,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_success_threshold = max(1, half_open_success_threshold)
        self.name = name or "dependency"

        self.state: CircuitBreakerState = CircuitBreakerState.CLOSED
        self._consecutive_failures = 0
        self._half_open_successes = 0
        self._opened_at: float | None = None

    def allows_request(self) -> bool:
        """Determine whether an operation is permitted at this time."""
        if self.state == CircuitBreakerState.OPEN:
            if self._opened_at is None:
                return False
            if (time.monotonic() - self._opened_at) >= self.recovery_timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                self._half_open_successes = 0
                return True
            return False
        return True

    def record_success(self) -> None:
        """Reset counters on success and potentially close the breaker."""
        self._consecutive_failures = 0
        if self.state == CircuitBreakerState.HALF_OPEN:
            self._half_open_successes += 1
            if self._half_open_successes >= self.half_open_success_threshold:
                self.close()
        elif self.state == CircuitBreakerState.OPEN:
            self.close()

    def record_failure(self) -> None:
        """Increment failure counters and open the breaker if needed."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.open()
            return

        self._consecutive_failures += 1
        if self._consecutive_failures >= self.failure_threshold:
            self.open()

    def open(self) -> None:
        """Trip the breaker into the OPEN state."""
        self.state = CircuitBreakerState.OPEN
        self._opened_at = time.monotonic()
        self._consecutive_failures = 0
        self._half_open_successes = 0

    def close(self) -> None:
        """Close the breaker and reset counters."""
        self.state = CircuitBreakerState.CLOSED
        self._opened_at = None
        self._consecutive_failures = 0
        self._half_open_successes = 0


async def _invoke_callable(
    func: Callable[..., Awaitable[T] | T],
    *,
    run_in_executor: bool,
    args: Tuple[Any, ...],
    kwargs: Dict[str, Any],
) -> T:
    """Execute a callable that may be sync or async."""
    if run_in_executor:
        return await asyncio.to_thread(func, *args, **kwargs)

    result = func(*args, **kwargs)
    if inspect.isawaitable(result):
        return await result  # type: ignore[return-value]
    return result  # type: ignore[return-value]


async def execute_with_retry(
    func: Callable[..., Awaitable[T] | T],
    *args: Any,
    retry_policy: RetryPolicy,
    circuit_breaker: Optional[CircuitBreaker] = None,
    logger: Optional[logging.Logger] = None,
    metadata: Optional[Dict[str, Any]] = None,
    failure_exception_cls: Type[TAE] = VendorAPIError,
    run_in_executor: bool = False,
    **kwargs: Any,
) -> T:
    """Execute a callable with retries, backoff, and optional circuit breaker."""

    attempts = max(1, retry_policy.max_attempts)
    metadata = metadata or {}
    last_error: BaseException | None = None

    for attempt in range(1, attempts + 1):
        if circuit_breaker and not circuit_breaker.allows_request():
            raise CircuitBreakerOpenError(
                message="Circuit breaker open.",
                details={"circuit": circuit_breaker.name, **metadata},
            )

        try:
            result = await _invoke_callable(
                func,
                run_in_executor=run_in_executor,
                args=args,
                kwargs=kwargs,
            )
        except retry_policy.retry_exceptions as exc:  # type: ignore[arg-type]
            last_error = exc
            if circuit_breaker:
                circuit_breaker.record_failure()

            if attempt >= attempts:
                break

            delay = retry_policy.backoff(attempt)
            if logger:
                logger.warning(
                    "Retryable error on attempt %s/%s: %s",
                    attempt,
                    attempts,
                    exc,
                    extra={"metadata": metadata},
                )
            await asyncio.sleep(delay)
            continue
        except Exception as exc:  # pragma: no cover - defensive guard
            if circuit_breaker:
                circuit_breaker.record_failure()
            raise
        else:
            if circuit_breaker:
                circuit_breaker.record_success()
            return result

    details = {**metadata, "attempts": attempts}
    if last_error is not None:
        details["last_error"] = repr(last_error)

    if not issubclass(failure_exception_cls, TradingAgentsError):  # pragma: no cover - safety
        failure_exception_cls = VendorAPIError

    raise failure_exception_cls(
        message=f"Operation failed after {attempts} attempts.",
        details=details,
    ) from last_error


__all__ = [
    "CircuitBreaker",
    "CircuitBreakerOpenError",
    "CircuitBreakerState",
    "RetryPolicy",
    "execute_with_retry",
]
