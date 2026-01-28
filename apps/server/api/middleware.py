"""
请求追踪中间件

为每个 HTTP 请求生成唯一的追踪 ID，并在日志中传播
同时收集 API 性能指标
"""
import time
import uuid
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import structlog

from services.api_metrics import api_metrics

logger = structlog.get_logger()


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """请求追踪中间件 - 为每个请求添加唯一 ID 并记录请求/响应日志"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 1. 从 Header 获取或生成请求 ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # 2. 将 request_id 注入到 request.state（可在路由中访问）
        request.state.request_id = request_id

        # 3. 绑定到 structlog 上下文（所有后续日志会自动包含 request_id）
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # 4. 记录请求开始
        start_time = time.time()
        logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            query=str(request.url.query) if request.url.query else None,
            client_ip=request.client.host if request.client else None,
        )

        # 5. 调用实际的路由处理
        try:
            response = await call_next(request)
        except Exception as exc:
            # 异常处理（会被全局异常处理器捕获，但这里记录追踪 ID）
            duration = time.time() - start_time
            logger.error(
                "Request failed",
                method=request.method,
                path=request.url.path,
                duration_ms=round(duration * 1000, 2),
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise

        # 6. 记录请求完成
        duration = time.time() - start_time
        duration_ms = round(duration * 1000, 2)

        logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        # 7. 收集 API 性能指标
        api_metrics.record_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )

        # 8. 在响应 Header 中返回 request_id（方便客户端追踪）
        response.headers["X-Request-ID"] = request_id

        # 9. 清理上下文（避免线程泄漏）
        structlog.contextvars.clear_contextvars()

        return response
