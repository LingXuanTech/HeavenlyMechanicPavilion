"""系统健康监控 API 路由"""
import structlog
from fastapi import APIRouter, HTTPException, Query

from services.health_monitor import (
    health_monitor,
    HealthStatus
)
from api.schemas.health import (
    HealthReport,
    HealthErrorsResponse,
    HealthQuickResponse,
    ComponentHealthResponse,
    SystemUptimeResponse
)
from services.api_metrics import api_metrics

router = APIRouter(prefix="/health", tags=["Health Monitor"])
logger = structlog.get_logger()


@router.get("/", response_model=HealthQuickResponse)
async def quick_health_check():
    """
    快速健康检查

    返回简单的健康状态，适用于负载均衡器健康探针。
    """
    try:
        report = await health_monitor.get_health_report()

        if report.overall_status == HealthStatus.UNHEALTHY:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": report.overall_status.value,
                    "message": "System unhealthy"
                }
            )

        return HealthQuickResponse(
            status=report.overall_status.value,
            uptime_seconds=report.uptime_seconds
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=500, detail="Health check failed")


@router.get("/report", response_model=HealthReport)
async def get_full_health_report(force_refresh: bool = Query(False)):
    """
    获取完整健康报告

    返回所有组件的健康状态、系统指标和最近错误。
    """
    try:
        report = await health_monitor.get_health_report(force_refresh)
        return report

    except Exception as e:
        logger.error("Failed to get health report", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取健康报告失败: {str(e)}")


@router.get("/components", response_model=ComponentHealthResponse)
async def get_component_health():
    """
    获取各组件健康状态

    返回每个组件的详细健康信息。
    """
    try:
        report = await health_monitor.get_health_report()

        return ComponentHealthResponse(
            overall=report.overall_status.value,
            components={
                c.name: {
                    "status": c.status.value,
                    "message": c.message,
                    "latency_ms": c.latency_ms,
                    "last_check": c.last_check.isoformat()
                }
                for c in report.components
            }
        )

    except Exception as e:
        logger.error("Failed to get component health", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取组件健康失败: {str(e)}")


@router.get("/metrics")
async def get_system_metrics():
    """
    获取系统指标

    返回 CPU、内存、磁盘使用情况。
    """
    try:
        metrics = health_monitor.get_system_metrics()

        return {
            "cpu": {
                "percent": metrics.cpu_percent
            },
            "memory": {
                "percent": metrics.memory_percent,
                "used_mb": metrics.memory_used_mb,
                "total_mb": metrics.memory_total_mb
            },
            "disk": {
                "percent": metrics.disk_percent,
                "used_gb": metrics.disk_used_gb,
                "total_gb": metrics.disk_total_gb
            }
        }

    except Exception as e:
        logger.error("Failed to get system metrics", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取系统指标失败: {str(e)}")


@router.get("/errors", response_model=HealthErrorsResponse)
async def get_recent_errors(limit: int = Query(10, ge=1, le=100)):
    """
    获取最近的错误记录
    """
    try:
        report = await health_monitor.get_health_report()

        errors = report.recent_errors[-limit:]

        return HealthErrorsResponse(
            errors=[
                {
                    "timestamp": e.timestamp,
                    "component": e.component,
                    "error_type": e.error_type,
                    "message": e.message,
                    "count": e.count
                }
                for e in errors
            ],
            total=len(errors)
        )

    except Exception as e:
        logger.error("Failed to get errors", error=str(e))
        raise HTTPException(status_code=500, detail=f"获取错误记录失败: {str(e)}")


@router.delete("/errors")
async def clear_errors():
    """
    清除错误历史记录
    """
    try:
        count = health_monitor.clear_errors()
        return {
            "status": "success",
            "message": f"已清除 {count} 条错误记录",
            "cleared_count": count
        }

    except Exception as e:
        logger.error("Failed to clear errors", error=str(e))
        raise HTTPException(status_code=500, detail=f"清除错误失败: {str(e)}")


@router.get("/uptime", response_model=SystemUptimeResponse)
async def get_uptime():
    """
    获取系统运行时间
    """
    uptime = health_monitor.get_uptime()
    return SystemUptimeResponse(**uptime)


@router.get("/liveness")
async def liveness_probe():
    """
    Kubernetes liveness 探针

    只要应用在运行就返回 200。
    """
    return {"status": "alive"}


@router.get("/readiness")
async def readiness_probe():
    """
    Kubernetes readiness 探针

    检查核心组件是否就绪。
    """
    try:
        report = await health_monitor.get_health_report()

        # 检查核心组件
        core_components = ["database", "scheduler"]
        for comp in report.components:
            if comp.name in core_components and comp.status == HealthStatus.UNHEALTHY:
                raise HTTPException(
                    status_code=503,
                    detail=f"Core component {comp.name} is unhealthy"
                )

        return {
            "status": "ready",
            "components": len(report.components)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Not ready")


# =============================================================================
# API 性能指标端点
# =============================================================================


@router.get("/api-metrics")
async def get_api_metrics():
    """
    获取 API 性能指标

    返回请求统计、延迟分布、错误率等。
    适用于监控仪表板和告警系统。
    """
    return api_metrics.get_metrics()


@router.get("/api-metrics/slow-requests")
async def get_slow_requests(
    threshold_ms: float = Query(default=1000.0, ge=100.0, description="慢请求阈值（毫秒）"),
    limit: int = Query(default=10, ge=1, le=50, description="返回数量")
):
    """
    获取慢请求列表

    返回响应时间超过阈值的请求。
    """
    return {
        "threshold_ms": threshold_ms,
        "slow_requests": api_metrics.get_slow_requests(threshold_ms, limit)
    }


@router.delete("/api-metrics")
async def reset_api_metrics():
    """
    重置 API 指标

    清除所有统计数据，重新开始计数。
    """
    api_metrics.reset()
    return {"status": "success", "message": "API metrics reset"}
