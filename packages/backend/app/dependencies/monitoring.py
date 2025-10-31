"""监控服务依赖注入 - 已弃用,请使用 dependencies.services."""

import warnings

warnings.warn(
    "Importing from app.dependencies.monitoring is deprecated. "
    "Use 'from app.dependencies import get_monitoring_service' instead.",
    DeprecationWarning,
    stacklevel=2,
)

from .services import get_monitoring_service

__all__ = ["get_monitoring_service"]
