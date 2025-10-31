"""Authentication and rate limiting middleware."""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import get_settings
from ..security.rate_limit import check_ip_rate_limit

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for authentication and access logging."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log access.

        Args:
            request: FastAPI request
            call_next: Next middleware or route handler

        Returns:
            Response
        """
        ip_address = request.client.host if request.client else "unknown"
        path = request.url.path
        method = request.method

        logger.info(f"Request: {method} {path} from {ip_address}")

        response = await call_next(request)

        logger.info(f"Response: {method} {path} - {response.status_code}")

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware for global rate limiting."""

    def __init__(self, app, excluded_paths: list[str] = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or ["/health", "/docs", "/openapi.json"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting.

        Args:
            request: FastAPI request
            call_next: Next middleware or route handler

        Returns:
            Response
        """
        if not settings.rate_limit_enabled:
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(excluded) for excluded in self.excluded_paths):
            return await call_next(request)

        ip_address = request.client.host if request.client else "unknown"

        try:
            await check_ip_rate_limit(ip_address, request)
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")

        response = await call_next(request)
        return response
