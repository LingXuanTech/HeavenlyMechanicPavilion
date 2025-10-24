"""Monitoring and metrics collection service."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from ..cache import get_redis_manager
from ..db import get_db_manager

logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter(
    "tradingagents_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)

REQUEST_DURATION = Histogram(
    "tradingagents_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
)

DB_LATENCY = Histogram(
    "tradingagents_db_latency_seconds",
    "Database query latency in seconds",
    ["operation"],
)

REDIS_LATENCY = Histogram(
    "tradingagents_redis_latency_seconds",
    "Redis operation latency in seconds",
    ["operation"],
)

VENDOR_REQUESTS = Counter(
    "tradingagents_vendor_requests_total",
    "Total vendor API requests",
    ["vendor", "status"],
)

VENDOR_ERRORS = Counter(
    "tradingagents_vendor_errors_total",
    "Total vendor API errors",
    ["vendor", "error_type"],
)

WORKER_TASKS = Gauge(
    "tradingagents_worker_tasks_active",
    "Number of active worker tasks",
    ["worker_type"],
)

QUEUE_SIZE = Gauge(
    "tradingagents_queue_size",
    "Number of items in queue",
    ["queue_name"],
)

SERVICE_UP = Gauge(
    "tradingagents_service_up",
    "Service availability (1 = up, 0 = down)",
    ["service"],
)


class MonitoringService:
    """Service for collecting and exposing monitoring metrics."""

    def __init__(self):
        """Initialize the monitoring service."""
        self._start_time = time.time()
        self._vendor_stats: Dict[str, Dict[str, Any]] = {}
        self._service_checks: Dict[str, bool] = {}

    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status of all services.
        
        Returns:
            Dictionary containing health status for all services
        """
        db_health = await self._check_database_health()
        redis_health = await self._check_redis_health()
        vendor_health = await self._check_vendor_health()
        worker_health = await self._check_worker_health()

        # Determine overall status
        all_critical_healthy = db_health["status"] == "healthy"
        
        if redis_health.get("enabled", False):
            all_critical_healthy = all_critical_healthy and redis_health["status"] == "healthy"
        
        overall_status = "healthy" if all_critical_healthy else "degraded"
        
        # Check for errors
        if db_health["status"] == "error":
            overall_status = "error"

        return {
            "status": overall_status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "uptime_seconds": time.time() - self._start_time,
            "services": {
                "database": db_health,
                "redis": redis_health,
                "vendors": vendor_health,
                "workers": worker_health,
            },
        }

    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database health and latency.
        
        Returns:
            Dictionary with database health information
        """
        try:
            db_manager = get_db_manager()
            if not db_manager:
                return {
                    "status": "error",
                    "message": "Database not initialized",
                }

            start_time = time.time()
            
            # Simple health check query
            from sqlalchemy import text
            async for session in db_manager.get_session():
                await session.execute(text("SELECT 1"))
                break
            
            latency_ms = (time.time() - start_time) * 1000
            
            # Record metric
            DB_LATENCY.labels(operation="health_check").observe(latency_ms / 1000)
            SERVICE_UP.labels(service="database").set(1)

            status = "healthy" if latency_ms < 100 else "degraded"

            return {
                "status": status,
                "latency_ms": round(latency_ms, 2),
                "message": "Database is accessible",
            }

        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            SERVICE_UP.labels(service="database").set(0)
            return {
                "status": "error",
                "message": str(e),
            }

    async def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis health and latency.
        
        Returns:
            Dictionary with Redis health information
        """
        redis_manager = get_redis_manager()
        
        if not redis_manager:
            return {
                "status": "not_configured",
                "enabled": False,
                "message": "Redis not enabled",
            }

        try:
            start_time = time.time()
            is_up = await redis_manager.ping()
            latency_ms = (time.time() - start_time) * 1000

            if is_up:
                # Get Redis info
                info = await redis_manager.client.info()
                
                # Record metric
                REDIS_LATENCY.labels(operation="ping").observe(latency_ms / 1000)
                SERVICE_UP.labels(service="redis").set(1)

                status = "healthy" if latency_ms < 50 else "degraded"

                return {
                    "status": status,
                    "enabled": True,
                    "latency_ms": round(latency_ms, 2),
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory_mb": round(info.get("used_memory", 0) / (1024 * 1024), 2),
                    "uptime_days": round(info.get("uptime_in_seconds", 0) / 86400, 2),
                }
            else:
                SERVICE_UP.labels(service="redis").set(0)
                return {
                    "status": "error",
                    "enabled": True,
                    "message": "Redis ping failed",
                }

        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            SERVICE_UP.labels(service="redis").set(0)
            return {
                "status": "error",
                "enabled": True,
                "message": str(e),
            }

    async def _check_vendor_health(self) -> Dict[str, Any]:
        """Check vendor plugin availability and error rates.
        
        Returns:
            Dictionary with vendor health information
        """
        try:
            from tradingagents.plugins import get_registry
            
            registry = get_registry()
            plugins = registry.list_plugins()
            
            vendor_statuses = {}
            total_vendors = len(plugins)
            healthy_vendors = 0
            
            for plugin in plugins:
                vendor_name = plugin.name
                
                # Get stats from internal tracking
                stats = self._vendor_stats.get(vendor_name, {})
                
                total_requests = stats.get("total_requests", 0)
                total_errors = stats.get("total_errors", 0)
                error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
                
                status = "healthy"
                if error_rate > 50:
                    status = "error"
                elif error_rate > 20:
                    status = "degraded"
                else:
                    healthy_vendors += 1
                
                vendor_statuses[vendor_name] = {
                    "status": status,
                    "provider": plugin.provider,
                    "total_requests": total_requests,
                    "total_errors": total_errors,
                    "error_rate_percent": round(error_rate, 2),
                    "rate_limits": plugin.get_rate_limits(),
                }
            
            overall_status = "healthy"
            if healthy_vendors < total_vendors * 0.5:
                overall_status = "degraded"
            elif healthy_vendors == 0 and total_vendors > 0:
                overall_status = "error"
            
            SERVICE_UP.labels(service="vendors").set(1 if overall_status != "error" else 0)
            
            return {
                "status": overall_status,
                "total_vendors": total_vendors,
                "healthy_vendors": healthy_vendors,
                "vendors": vendor_statuses,
            }

        except Exception as e:
            logger.error(f"Vendor health check failed: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def _check_worker_health(self) -> Dict[str, Any]:
        """Check background worker health and queue status.
        
        Returns:
            Dictionary with worker health information
        """
        try:
            from ..workers import get_worker_manager
            
            worker_manager = get_worker_manager()
            
            if not worker_manager:
                return {
                    "status": "not_configured",
                    "message": "Workers not initialized",
                }
            
            worker_statuses = {}
            total_workers = 0
            running_workers = 0
            
            for worker_name, worker in worker_manager._workers.items():
                total_workers += 1
                is_running = worker.is_running()
                
                if is_running:
                    running_workers += 1
                
                worker_statuses[worker_name] = {
                    "status": "running" if is_running else "stopped",
                    "tasks_processed": getattr(worker, "_tasks_processed", 0),
                    "current_tasks": getattr(worker, "_current_tasks", 0),
                }
                
                # Update Prometheus metrics
                if is_running:
                    WORKER_TASKS.labels(worker_type=worker_name).set(
                        getattr(worker, "_current_tasks", 0)
                    )
            
            overall_status = "healthy" if running_workers == total_workers else "degraded"
            
            SERVICE_UP.labels(service="workers").set(1 if running_workers > 0 else 0)
            
            return {
                "status": overall_status,
                "total_workers": total_workers,
                "running_workers": running_workers,
                "workers": worker_statuses,
            }

        except Exception as e:
            logger.error(f"Worker health check failed: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    async def get_queue_metrics(self) -> Dict[str, Any]:
        """Get queue backlog metrics.
        
        Returns:
            Dictionary with queue metrics
        """
        redis_manager = get_redis_manager()
        
        if not redis_manager:
            return {
                "status": "not_available",
                "message": "Redis not enabled",
            }

        try:
            queues = {}
            
            # Check common queue patterns
            queue_patterns = [
                "queue:data_fetch:*",
                "queue:analysis:*",
                "queue:trading:*",
            ]
            
            for pattern in queue_patterns:
                keys = await redis_manager.client.keys(pattern)
                for key in keys:
                    queue_name = key.replace("queue:", "")
                    size = await redis_manager.client.llen(key)
                    queues[queue_name] = size
                    
                    # Update Prometheus metric
                    QUEUE_SIZE.labels(queue_name=queue_name).set(size)
            
            total_items = sum(queues.values())
            
            return {
                "status": "ok",
                "total_items": total_items,
                "queues": queues,
            }

        except Exception as e:
            logger.error(f"Failed to get queue metrics: {e}")
            return {
                "status": "error",
                "message": str(e),
            }

    def record_vendor_request(self, vendor_name: str, success: bool, error_type: Optional[str] = None):
        """Record a vendor API request for metrics.
        
        Args:
            vendor_name: Name of the vendor
            success: Whether the request was successful
            error_type: Type of error if request failed
        """
        if vendor_name not in self._vendor_stats:
            self._vendor_stats[vendor_name] = {
                "total_requests": 0,
                "total_errors": 0,
            }
        
        self._vendor_stats[vendor_name]["total_requests"] += 1
        
        status = "success" if success else "error"
        VENDOR_REQUESTS.labels(vendor=vendor_name, status=status).inc()
        
        if not success:
            self._vendor_stats[vendor_name]["total_errors"] += 1
            if error_type:
                VENDOR_ERRORS.labels(vendor=vendor_name, error_type=error_type).inc()

    def get_prometheus_metrics(self) -> tuple[bytes, str]:
        """Get Prometheus-formatted metrics.
        
        Returns:
            Tuple of (metrics_bytes, content_type)
        """
        return generate_latest(), CONTENT_TYPE_LATEST


# Global monitoring service instance
_monitoring_service: Optional[MonitoringService] = None


def get_monitoring_service() -> MonitoringService:
    """Get or create the global monitoring service instance.
    
    Returns:
        MonitoringService instance
    """
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    return _monitoring_service
