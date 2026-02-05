"""健康监控相关的 Pydantic Schema 定义"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from services.health_monitor import HealthStatus


class ComponentHealth(BaseModel):
    """组件健康状态"""
    name: str
    status: HealthStatus
    message: Optional[str] = None
    latency_ms: Optional[float] = None
    last_check: datetime


class ErrorRecord(BaseModel):
    """错误记录"""
    timestamp: datetime
    component: str
    error_type: str
    message: str
    count: int = 1


class SystemMetrics(BaseModel):
    """系统指标"""
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float
    disk_used_gb: float
    disk_total_gb: float


class HealthReport(BaseModel):
    """完整健康报告"""
    overall_status: HealthStatus
    uptime_seconds: int
    uptime_formatted: str
    components: List[ComponentHealth]
    metrics: SystemMetrics
    recent_errors: List[ErrorRecord]
    timestamp: datetime


class HealthErrorsResponse(BaseModel):
    """错误记录响应"""
    errors: List[ErrorRecord]
    total: int


class HealthQuickResponse(BaseModel):
    """快速健康检查响应"""
    status: str
    uptime_seconds: int


class ComponentHealthResponse(BaseModel):
    """组件健康状态响应"""
    overall: str
    components: Dict[str, Any]


class SystemUptimeResponse(BaseModel):
    """系统运行时间响应"""
    start_time: datetime
    uptime_seconds: float
    uptime_formatted: str
    current_time: datetime
