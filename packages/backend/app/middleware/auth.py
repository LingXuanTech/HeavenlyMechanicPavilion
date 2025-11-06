"""Authentication and rate limiting middleware."""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import get_settings
from ..db.session import get_session
from ..security.dependencies import get_current_user_from_api_key, get_current_user_from_token
from ..security.rate_limit import check_ip_rate_limit

logger = logging.getLogger(__name__)
settings = get_settings()


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware for authentication and access logging."""

    def __init__(self, app, public_paths: list[str] | None = None):
        """Initialize auth middleware with public paths.
        
        Args:
            app: FastAPI application
            public_paths: List of path prefixes that don't require authentication
        """
        super().__init__(app)
        self.public_paths = public_paths or [
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/api/auth/login",
            "/api/auth/register",
        ]

    def _is_public_path(self, path: str) -> bool:
        """Check if path is public (no auth required).
        
        Args:
            path: Request path
            
        Returns:
            True if path is public
        """
        return any(path.startswith(public) for public in self.public_paths)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with authentication and logging.

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

        # Skip auth for public paths
        if self._is_public_path(path):
            response = await call_next(request)
            logger.info(f"Response: {method} {path} - {response.status_code} (public)")
            return response

        # Perform authentication
        try:
            # Create a temporary database session for auth check
            async for db in get_session():
                # Try to authenticate user via token or API key
                user = None
                
                # Check for Bearer token
                auth_header = request.headers.get("authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    from fastapi.security import HTTPAuthorizationCredentials
                    credentials = HTTPAuthorizationCredentials(
                        scheme="Bearer",
                        credentials=auth_header.split(" ")[1]
                    )
                    user = await get_current_user_from_token(credentials, db)
                
                # If no token, check for API key
                if not user:
                    api_key = request.headers.get("x-api-key")
                    if api_key:
                        user = await get_current_user_from_api_key(api_key, db)
                
                # If still no user, return 401
                if not user:
                    logger.warning(f"Unauthorized access attempt to {path} from {ip_address}")
                    return JSONResponse(
                        status_code=401,
                        content={
                            "detail": "Not authenticated",
                            "message": "Please provide a valid Bearer token or X-API-Key header"
                        },
                        headers={"WWW-Authenticate": "Bearer"}
                    )
                
                # Check if user is active
                if not user.is_active:
                    logger.warning(f"Inactive user {user.username} attempted to access {path}")
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Inactive user"}
                    )
                
                # Store user in request state for downstream handlers
                request.state.user = user
                
                # Break after first iteration (we only need one session)
                break
                
        except Exception as e:
            logger.error(f"Authentication error for {path}: {e}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal authentication error"}
            )

        # Continue to next middleware/handler
        response = await call_next(request)
        logger.info(f"Response: {method} {path} - {response.status_code} (authenticated as {user.username})")

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
