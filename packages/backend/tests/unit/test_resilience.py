"""Unit tests for retry and circuit breaker utilities."""

from __future__ import annotations

import asyncio

import pytest

from app.core.errors import CircuitBreakerOpenError, VendorAPIError
from app.core.resilience import CircuitBreaker, RetryPolicy, execute_with_retry


@pytest.mark.asyncio
async def test_execute_with_retry_recovers() -> None:
    attempts = 0

    async def flaky() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("temporary failure")
        return "ok"

    policy = RetryPolicy(
        max_attempts=4,
        initial_backoff=0.01,
        max_backoff=0.01,
        multiplier=1.0,
        jitter=0.0,
        retry_exceptions=(RuntimeError,),
    )

    result = await execute_with_retry(flaky, retry_policy=policy)

    assert result == "ok"
    assert attempts == 3


@pytest.mark.asyncio
async def test_execute_with_retry_exhausts() -> None:
    async def always_fail() -> None:
        raise RuntimeError("boom")

    policy = RetryPolicy(
        max_attempts=2,
        initial_backoff=0.01,
        max_backoff=0.01,
        multiplier=1.0,
        jitter=0.0,
        retry_exceptions=(RuntimeError,),
    )

    with pytest.raises(VendorAPIError) as exc_info:
        await execute_with_retry(always_fail, retry_policy=policy)

    assert exc_info.value.details["attempts"] == 2


@pytest.mark.asyncio
async def test_circuit_breaker_trips_and_recovers() -> None:
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.05, name="test")
    policy = RetryPolicy(
        max_attempts=1,
        initial_backoff=0.0,
        max_backoff=0.0,
        multiplier=1.0,
        jitter=0.0,
        retry_exceptions=(RuntimeError,),
    )

    async def failing_call() -> None:
        raise RuntimeError("failure")

    # First two failures move the breaker to open state
    with pytest.raises(VendorAPIError):
        await execute_with_retry(failing_call, retry_policy=policy, circuit_breaker=breaker)
    with pytest.raises(VendorAPIError):
        await execute_with_retry(failing_call, retry_policy=policy, circuit_breaker=breaker)

    # Third call should short-circuit due to open breaker
    with pytest.raises(CircuitBreakerOpenError):
        await execute_with_retry(failing_call, retry_policy=policy, circuit_breaker=breaker)

    # Wait for half-open transition and ensure it attempts again
    await asyncio.sleep(0.06)
    with pytest.raises(VendorAPIError):
        await execute_with_retry(failing_call, retry_policy=policy, circuit_breaker=breaker)
