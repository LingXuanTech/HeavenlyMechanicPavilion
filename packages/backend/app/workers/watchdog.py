"""Worker watchdog for monitoring background tasks."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Dict, Optional

from ..config.settings import get_settings
from ..dependencies import get_alerting_service
from ..services.alerting import AlertLevel

logger = logging.getLogger(__name__)


class WorkerWatchdog:
    """Monitors background workers and triggers alerts for failures."""

    def __init__(self):
        """Initialize the watchdog."""
        self.settings = get_settings()
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._worker_last_seen: Dict[str, float] = {}
        self._worker_task_counts: Dict[str, int] = {}

    def start(self):
        """Start the watchdog monitoring loop."""
        if self._running:
            logger.warning("Watchdog already running")
            return

        if not self.settings.watchdog_enabled:
            logger.info("Watchdog is disabled in settings")
            return

        self._running = True
        self._task = asyncio.create_task(self._monitoring_loop())
        logger.info("Worker watchdog started")

    async def stop(self):
        """Stop the watchdog monitoring loop."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Worker watchdog stopped")

    async def _monitoring_loop(self):
        """Main monitoring loop."""
        try:
            while self._running:
                await self._check_workers()
                await asyncio.sleep(self.settings.watchdog_check_interval)
        except asyncio.CancelledError:
            logger.info("Watchdog monitoring loop cancelled")
        except Exception as e:
            logger.error(f"Watchdog monitoring loop error: {e}")
            # Try to send alert about watchdog failure
            try:
                from ..config.settings import get_settings
                settings = get_settings()
                alerting_service = get_alerting_service(settings)
                await alerting_service.send_alert(
                    title="Worker Watchdog Failure",
                    message=f"Watchdog monitoring loop encountered an error: {str(e)}",
                    level=AlertLevel.CRITICAL,
                )
            except Exception:
                pass

    async def _check_workers(self):
        """Check all workers for health issues."""
        try:
            from . import get_worker_manager
            
            worker_manager = get_worker_manager()
            if not worker_manager:
                logger.debug("Worker manager not initialized, skipping check")
                return

            current_time = time.time()
            from ..config.settings import get_settings
            settings = get_settings()
            alerting_service = get_alerting_service(settings)

            for worker_name, worker in worker_manager._workers.items():
                # Check if worker is running
                is_running = worker.is_running()
                
                if not is_running:
                    # Worker is stopped - check if it was expected
                    if worker_name in self._worker_last_seen:
                        # Worker was running before but stopped
                        await alerting_service.send_alert(
                            title=f"Worker Stopped: {worker_name}",
                            message=f"Background worker '{worker_name}' has stopped unexpectedly.",
                            level=AlertLevel.ERROR,
                            details={
                                "worker": worker_name,
                                "last_seen": datetime.fromtimestamp(
                                    self._worker_last_seen[worker_name], 
                                    tz=timezone.utc
                                ).isoformat(),
                            },
                        )
                        # Remove from tracking
                        del self._worker_last_seen[worker_name]
                        if worker_name in self._worker_task_counts:
                            del self._worker_task_counts[worker_name]
                    continue

                # Worker is running - update last seen
                self._worker_last_seen[worker_name] = current_time

                # Check for stuck tasks
                current_tasks = getattr(worker, "_current_tasks", 0)
                previous_count = self._worker_task_counts.get(worker_name, 0)

                # If current tasks are the same as before and non-zero, worker might be stuck
                if current_tasks > 0 and current_tasks == previous_count:
                    # Check if it's been too long
                    last_seen = self._worker_last_seen.get(worker_name, current_time)
                    time_stuck = current_time - last_seen
                    
                    if time_stuck > self.settings.watchdog_task_timeout:
                        await alerting_service.send_alert(
                            title=f"Worker Task Timeout: {worker_name}",
                            message=f"Worker '{worker_name}' appears to have stuck tasks (timeout: {self.settings.watchdog_task_timeout}s).",
                            level=AlertLevel.WARNING,
                            details={
                                "worker": worker_name,
                                "current_tasks": current_tasks,
                                "time_stuck_seconds": round(time_stuck, 2),
                            },
                        )
                        # Reset timer to avoid repeated alerts
                        self._worker_last_seen[worker_name] = current_time

                # Update task count
                self._worker_task_counts[worker_name] = current_tasks

        except Exception as e:
            logger.error(f"Error checking workers: {e}")

    def record_worker_activity(self, worker_name: str):
        """Record that a worker has completed activity.
        
        Args:
            worker_name: Name of the worker
        """
        self._worker_last_seen[worker_name] = time.time()

    def get_worker_status(self) -> Dict[str, Dict[str, any]]:
        """Get current status of all tracked workers.
        
        Returns:
            Dictionary of worker statuses
        """
        current_time = time.time()
        statuses = {}
        
        for worker_name, last_seen in self._worker_last_seen.items():
            time_since_activity = current_time - last_seen
            statuses[worker_name] = {
                "last_seen_seconds_ago": round(time_since_activity, 2),
                "current_tasks": self._worker_task_counts.get(worker_name, 0),
                "status": "healthy" if time_since_activity < self.settings.watchdog_task_timeout else "warning",
            }
        
        return statuses


# Global watchdog instance
_watchdog: Optional[WorkerWatchdog] = None


def get_watchdog() -> WorkerWatchdog:
    """Get or create the global watchdog instance.
    
    Returns:
        WorkerWatchdog instance
    """
    global _watchdog
    if _watchdog is None:
        _watchdog = WorkerWatchdog()
    return _watchdog


def start_watchdog():
    """Start the global watchdog."""
    watchdog = get_watchdog()
    watchdog.start()


async def stop_watchdog():
    """Stop the global watchdog."""
    watchdog = get_watchdog()
    await watchdog.stop()
