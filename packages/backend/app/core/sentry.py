"""Optional Sentry integration for centralized error tracking."""

from __future__ import annotations

import logging
from typing import Any

try:  # pragma: no cover - optional dependency
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
except ImportError:  # pragma: no cover
    sentry_sdk = None  # type: ignore[assignment]
    FastApiIntegration = None  # type: ignore[assignment]

_logger = logging.getLogger(__name__)
_sentry_initialized = False


def init_sentry(settings: Any) -> None:
    """Initialize Sentry if enabled in configuration."""
    global _sentry_initialized

    if _sentry_initialized:
        return

    enabled = getattr(settings, "error_tracking_enabled", False)
    dsn = getattr(settings, "sentry_dsn", None)

    if not enabled or not dsn:
        return

    if sentry_sdk is None:
        _logger.warning("Sentry SDK is not installed but error tracking is enabled.")
        return

    sentry_sdk.init(  # type: ignore[call-arg]
        dsn=dsn,
        environment=getattr(settings, "environment", "development"),
        release=getattr(settings, "api_version", "unknown"),
        traces_sample_rate=getattr(settings, "sentry_traces_sample_rate", 0.0),
        profiles_sample_rate=getattr(settings, "sentry_profiles_sample_rate", 0.0),
        enable_tracing=getattr(settings, "sentry_traces_sample_rate", 0.0) > 0,
        integrations=[FastApiIntegration()] if FastApiIntegration else None,
    )

    _sentry_initialized = True
    _logger.info("Sentry error tracking initialized.")


def capture_exception(exc: BaseException) -> None:
    """Capture an exception with Sentry if enabled."""
    if not _sentry_initialized or sentry_sdk is None:
        return
    sentry_sdk.capture_exception(exc)  # type: ignore[call-arg]


__all__ = ["capture_exception", "init_sentry"]
