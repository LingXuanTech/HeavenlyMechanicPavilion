"""Middleware components for the FastAPI application."""

from .metrics import MetricsMiddleware

__all__ = ["MetricsMiddleware"]
