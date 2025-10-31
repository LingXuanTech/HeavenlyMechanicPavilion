"""Application-wide exception handling middleware."""

from __future__ import annotations

import logging
import uuid
from typing import Any, Dict

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..core.context import reset_correlation_id, set_correlation_id
from ..core.errors import TradingAgentsError, ValidationError
from ..core.sentry import capture_exception


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Transforms uncaught exceptions into structured API responses."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self.logger = logging.getLogger("app.error")

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        token = set_correlation_id(correlation_id)
        request.state.correlation_id = correlation_id

        try:
            response = await call_next(request)
        except TradingAgentsError as exc:
            response = self._handle_tradingagents_error(exc, correlation_id, request)
        except RequestValidationError as exc:
            ta_exc = ValidationError(
                message="Request validation failed.",
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                details={"errors": exc.errors()},
            )
            response = self._handle_tradingagents_error(ta_exc, correlation_id, request)
        except HTTPException as exc:
            response = self._handle_http_exception(exc, correlation_id, request)
        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.exception(
                "Unhandled application error",
                extra={
                    "correlation_id": correlation_id,
                    "path": str(request.url.path),
                },
            )
            capture_exception(exc)
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": {
                        "code": "internal_server_error",
                        "message": "An unexpected error occurred.",
                        "details": {"type": exc.__class__.__name__},
                    },
                    "correlation_id": correlation_id,
                },
            )
        finally:
            reset_correlation_id(token)

        response.headers.setdefault("X-Correlation-ID", correlation_id)
        return response

    def _handle_tradingagents_error(
        self,
        exc: TradingAgentsError,
        correlation_id: str,
        request: Request,
    ) -> JSONResponse:
        """Format a TradingAgentsError into a JSON response."""
        log_extra = {
            "correlation_id": correlation_id,
            "code": exc.code,
            "path": str(request.url.path),
        }

        log_method = self.logger.warning if exc.status_code < 500 else self.logger.error
        log_method(f"Handled application error: {exc.message}", extra=log_extra)

        if exc.status_code >= 500:
            capture_exception(exc)

        payload = exc.to_dict()
        content = {
            "error": payload,
            "correlation_id": correlation_id,
        }
        return JSONResponse(status_code=exc.status_code, content=content)

    def _handle_http_exception(
        self,
        exc: HTTPException,
        correlation_id: str,
        request: Request,
    ) -> JSONResponse:
        """Normalize FastAPI HTTPException responses."""
        log_extra = {
            "correlation_id": correlation_id,
            "status": exc.status_code,
            "path": str(request.url.path),
        }
        log_level = self.logger.warning if exc.status_code < 500 else self.logger.error
        log_level(f"HTTPException encountered: {exc.detail}", extra=log_extra)

        details: Dict[str, Any] = {}
        if isinstance(exc.detail, dict):
            details = exc.detail
            message = exc.detail.get("message", "An HTTP error occurred.")
        elif isinstance(exc.detail, list):
            details = {"errors": exc.detail}
            message = "Request validation failed."
        else:
            message = str(exc.detail)

        content = {
            "error": {
                "code": "http_error",
                "message": message,
            },
            "correlation_id": correlation_id,
        }

        if details:
            content["error"]["details"] = details

        if exc.status_code >= 500:
            capture_exception(exc)

        return JSONResponse(status_code=exc.status_code, content=content)


__all__ = ["ErrorHandlingMiddleware"]
