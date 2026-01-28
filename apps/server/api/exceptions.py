"""统一异常体系

提供结构化的异常类型，支持：
- 标准化错误码
- HTTP 状态码映射
- 前端友好的错误消息
"""
from typing import Optional, Dict, Any


class AppException(Exception):
    """应用基础异常类"""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 JSON 响应）"""
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "details": self.details
            }
        }


# =============================================================================
# 数据源相关异常
# =============================================================================

class DataSourceError(AppException):
    """数据源错误（yfinance, akshare, alpha vantage 等）"""

    def __init__(self, source: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="DATA_SOURCE_ERROR",
            message=f"[{source}] {message}",
            status_code=502,
            details={"source": source, **(details or {})}
        )
        self.source = source


class DataNotFoundError(AppException):
    """数据未找到"""

    def __init__(self, resource: str, identifier: str):
        super().__init__(
            code="DATA_NOT_FOUND",
            message=f"{resource} not found: {identifier}",
            status_code=404,
            details={"resource": resource, "identifier": identifier}
        )


# =============================================================================
# 分析相关异常
# =============================================================================

class AnalysisError(AppException):
    """分析流程错误"""

    def __init__(self, message: str, symbol: Optional[str] = None, stage: Optional[str] = None):
        super().__init__(
            code="ANALYSIS_ERROR",
            message=message,
            status_code=500,
            details={"symbol": symbol, "stage": stage}
        )


class AnalysisTimeoutError(AnalysisError):
    """分析超时"""

    def __init__(self, symbol: str, timeout_seconds: int):
        super().__init__(
            message=f"Analysis timeout for {symbol} after {timeout_seconds}s",
            symbol=symbol,
            stage="timeout"
        )
        self.code = "ANALYSIS_TIMEOUT"
        self.status_code = 504


# =============================================================================
# 认证相关异常
# =============================================================================

class AuthenticationError(AppException):
    """认证错误"""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            code="AUTHENTICATION_ERROR",
            message=message,
            status_code=401
        )


class AuthorizationError(AppException):
    """授权错误"""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            code="AUTHORIZATION_ERROR",
            message=message,
            status_code=403
        )


# =============================================================================
# 验证相关异常
# =============================================================================

class ValidationError(AppException):
    """请求验证错误"""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=422,
            details={"field": field} if field else {}
        )


class InvalidSymbolError(ValidationError):
    """无效的股票代码"""

    def __init__(self, symbol: str):
        super().__init__(
            message=f"Invalid stock symbol: {symbol}",
            field="symbol"
        )
        self.code = "INVALID_SYMBOL"


# =============================================================================
# 资源相关异常
# =============================================================================

class ResourceExistsError(AppException):
    """资源已存在"""

    def __init__(self, resource: str, identifier: str):
        super().__init__(
            code="RESOURCE_EXISTS",
            message=f"{resource} already exists: {identifier}",
            status_code=409,
            details={"resource": resource, "identifier": identifier}
        )


class ResourceNotFoundError(AppException):
    """资源不存在"""

    def __init__(self, resource: str, identifier: str):
        super().__init__(
            code="RESOURCE_NOT_FOUND",
            message=f"{resource} not found: {identifier}",
            status_code=404,
            details={"resource": resource, "identifier": identifier}
        )


# =============================================================================
# 外部服务异常
# =============================================================================

class ExternalServiceError(AppException):
    """外部服务错误（LLM API 等）"""

    def __init__(self, service: str, message: str):
        super().__init__(
            code="EXTERNAL_SERVICE_ERROR",
            message=f"[{service}] {message}",
            status_code=503,
            details={"service": service}
        )


class RateLimitError(AppException):
    """频率限制"""

    def __init__(self, service: str, retry_after: Optional[int] = None):
        super().__init__(
            code="RATE_LIMIT_ERROR",
            message=f"Rate limit exceeded for {service}",
            status_code=429,
            details={"service": service, "retry_after": retry_after}
        )
