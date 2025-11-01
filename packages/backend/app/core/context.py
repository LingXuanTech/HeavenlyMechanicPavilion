"""Request-scoped context helpers."""

from __future__ import annotations

from contextvars import ContextVar, Token


_correlation_id_ctx: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def set_correlation_id(correlation_id: str) -> Token:
    """Bind the correlation identifier to the current context."""
    return _correlation_id_ctx.set(correlation_id)


def get_correlation_id() -> str | None:
    """Retrieve the correlation identifier for the current context."""
    return _correlation_id_ctx.get()


def reset_correlation_id(token: Token) -> None:
    """Reset the correlation identifier context to a previous state."""
    _correlation_id_ctx.reset(token)
