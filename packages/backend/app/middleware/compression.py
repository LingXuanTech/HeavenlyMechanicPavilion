"""Compression middleware for response optimization."""

from __future__ import annotations

import gzip
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.datastructures import MutableHeaders
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class CompressionMiddleware(BaseHTTPMiddleware):
    """Middleware to compress HTTP responses using gzip."""

    def __init__(
        self,
        app: ASGIApp,
        minimum_size: int = 500,
        compression_level: int = 6,
    ) -> None:
        """Initialize compression middleware.

        Args:
            app: The ASGI application.
            minimum_size: Minimum response size in bytes to compress.
            compression_level: Gzip compression level (1-9, default 6).
        """
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compression_level = compression_level

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process request and compress response if applicable.

        Args:
            request: The incoming HTTP request.
            call_next: The next middleware/endpoint to call.

        Returns:
            The HTTP response, potentially compressed.
        """
        # Check if client accepts gzip encoding
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding.lower():
            return await call_next(request)

        # Get the response
        response = await call_next(request)

        # Skip compression for these scenarios
        if (
            response.status_code < 200
            or response.status_code >= 300
            or "content-encoding" in response.headers
            or "content-range" in response.headers
        ):
            return response

        # Check content type - only compress text-based responses
        content_type = response.headers.get("content-type", "")
        compressible_types = [
            "text/",
            "application/json",
            "application/javascript",
            "application/xml",
            "application/x-yaml",
            "application/yaml",
        ]

        if not any(ct in content_type for ct in compressible_types):
            return response

        # Get response body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        # Only compress if body size exceeds minimum
        if len(body) < self.minimum_size:
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        # Compress the response
        try:
            compressed_body = gzip.compress(
                body, compresslevel=self.compression_level
            )

            # Calculate compression ratio
            original_size = len(body)
            compressed_size = len(compressed_body)
            ratio = (1 - compressed_size / original_size) * 100

            # Update headers
            headers = MutableHeaders(response.headers)
            headers["content-encoding"] = "gzip"
            headers["content-length"] = str(compressed_size)
            headers["vary"] = "Accept-Encoding"

            logger.debug(
                f"Compressed response: {original_size} -> {compressed_size} bytes "
                f"({ratio:.1f}% reduction)"
            )

            return Response(
                content=compressed_body,
                status_code=response.status_code,
                headers=dict(headers),
                media_type=response.media_type,
            )
        except Exception as e:
            logger.warning(f"Failed to compress response: {e}")
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
