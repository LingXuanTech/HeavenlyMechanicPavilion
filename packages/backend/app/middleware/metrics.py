"""Metrics middleware for tracking HTTP requests."""

from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..services.monitoring import REQUEST_COUNT, REQUEST_DURATION


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to collect HTTP request metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response from handler
        """
        # Start timer
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Extract path template (remove query parameters and path parameters)
        path = request.url.path

        # Normalize path to avoid high cardinality
        # Replace UUIDs and numeric IDs with placeholders
        import re

        path = re.sub(
            r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "/{uuid}", path
        )
        path = re.sub(r"/\d+", "/{id}", path)

        # Record metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=path,
            status=response.status_code,
        ).inc()

        REQUEST_DURATION.labels(
            method=request.method,
            endpoint=path,
        ).observe(duration)

        return response
