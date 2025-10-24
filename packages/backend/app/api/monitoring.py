"""API endpoints for monitoring and metrics."""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse

from ..services.alerting import get_alerting_service
from ..services.monitoring import get_monitoring_service
from ..workers.watchdog import get_watchdog

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=Dict[str, Any])
async def get_comprehensive_health():
    """Get comprehensive health status of all services.
    
    Returns detailed health information for:
    - Database (with latency)
    - Redis (if enabled)
    - Vendor plugins
    - Background workers
    """
    monitoring_service = get_monitoring_service()
    return await monitoring_service.get_health_status()


@router.get("/metrics")
async def get_prometheus_metrics():
    """Get Prometheus-formatted metrics.
    
    Returns metrics in Prometheus exposition format including:
    - HTTP request counts and durations
    - Database query latencies
    - Redis operation latencies
    - Vendor request counts and error rates
    - Worker task counts
    - Queue sizes
    - Service availability
    """
    monitoring_service = get_monitoring_service()
    metrics_bytes, content_type = monitoring_service.get_prometheus_metrics()
    
    return Response(content=metrics_bytes, media_type=content_type)


@router.get("/vendors", response_model=Dict[str, Any])
async def get_vendor_status():
    """Get vendor availability and error rates.
    
    Returns detailed information about each vendor plugin including:
    - Current status
    - Request counts
    - Error rates
    - Rate limits
    """
    monitoring_service = get_monitoring_service()
    health_status = await monitoring_service.get_health_status()
    return health_status.get("services", {}).get("vendors", {})


@router.get("/workers", response_model=Dict[str, Any])
async def get_worker_status():
    """Get background worker status.
    
    Returns information about:
    - Worker running status
    - Current active tasks
    - Tasks processed
    - Watchdog status
    """
    monitoring_service = get_monitoring_service()
    health_status = await monitoring_service.get_health_status()
    
    # Also get watchdog status
    watchdog = get_watchdog()
    watchdog_status = watchdog.get_worker_status()
    
    worker_data = health_status.get("services", {}).get("workers", {})
    worker_data["watchdog"] = {
        "enabled": watchdog._running,
        "tracked_workers": watchdog_status,
    }
    
    return worker_data


@router.get("/queues", response_model=Dict[str, Any])
async def get_queue_metrics():
    """Get queue backlog metrics.
    
    Returns information about:
    - Queue sizes
    - Total items across all queues
    """
    monitoring_service = get_monitoring_service()
    return await monitoring_service.get_queue_metrics()


@router.get("/database", response_model=Dict[str, Any])
async def get_database_metrics():
    """Get database health and metrics.
    
    Returns:
    - Connection status
    - Query latency
    - Health status
    """
    monitoring_service = get_monitoring_service()
    health_status = await monitoring_service.get_health_status()
    return health_status.get("services", {}).get("database", {})


@router.get("/redis", response_model=Dict[str, Any])
async def get_redis_metrics():
    """Get Redis health and metrics.
    
    Returns:
    - Connection status
    - Latency
    - Memory usage
    - Connected clients
    """
    monitoring_service = get_monitoring_service()
    health_status = await monitoring_service.get_health_status()
    return health_status.get("services", {}).get("redis", {})


@router.get("/alerts/history", response_model=List[Dict[str, Any]])
async def get_alert_history(limit: int = 50):
    """Get recent alert history.
    
    Args:
        limit: Maximum number of alerts to return (default: 50)
    
    Returns:
        List of recent alerts with timestamps and details
    """
    alerting_service = get_alerting_service()
    return alerting_service.get_alert_history(limit)


@router.post("/alerts/test", response_model=Dict[str, Any])
async def send_test_alert():
    """Send a test alert to verify alerting configuration.
    
    Returns:
        Status of the test alert
    """
    from ..services.alerting import AlertLevel
    
    alerting_service = get_alerting_service()
    
    success = await alerting_service.send_alert(
        title="Test Alert",
        message="This is a test alert from TradingAgents monitoring system.",
        level=AlertLevel.INFO,
        details={
            "source": "API test endpoint",
            "purpose": "Configuration verification",
        },
    )
    
    return {
        "success": success,
        "message": "Test alert sent" if success else "Failed to send test alert",
    }


@router.get("/uptime", response_model=Dict[str, Any])
async def get_uptime():
    """Get system uptime information.
    
    Returns:
        Uptime in seconds and formatted string
    """
    monitoring_service = get_monitoring_service()
    import time
    
    uptime_seconds = time.time() - monitoring_service._start_time
    
    days = int(uptime_seconds // 86400)
    hours = int((uptime_seconds % 86400) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    seconds = int(uptime_seconds % 60)
    
    return {
        "uptime_seconds": round(uptime_seconds, 2),
        "uptime_formatted": f"{days}d {hours}h {minutes}m {seconds}s",
        "uptime_days": round(uptime_seconds / 86400, 2),
    }
