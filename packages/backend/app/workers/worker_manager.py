"""Manager for coordinating multiple data workers."""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from ..cache import RedisManager
from ..schemas.streaming import DataType, WorkerStatus
from ..services.streaming_config import StreamingConfigService
from .data_worker import DataWorker

logger = logging.getLogger(__name__)


class WorkerManager:
    """Manages multiple data workers."""

    def __init__(
        self,
        redis: RedisManager,
        config_service: StreamingConfigService,
    ):
        """Initialize the worker manager.

        Args:
            redis: Redis manager
            config_service: Configuration service
        """
        self.redis = redis
        self.config_service = config_service
        self._workers: Dict[str, DataWorker] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize workers based on configuration."""
        if self._initialized:
            logger.warning("Worker manager already initialized")
            return

        logger.info("Initializing worker manager")

        # Create workers for each data type
        data_types = [
            DataType.MARKET_DATA,
            DataType.NEWS,
            DataType.FUNDAMENTALS,
            DataType.ANALYTICS,
            DataType.INSIDER_DATA,
        ]

        for data_type in data_types:
            worker_id = f"worker_{data_type.value}"
            worker = DataWorker(
                worker_id=worker_id,
                data_type=data_type,
                redis=self.redis,
                config_service=self.config_service,
            )
            self._workers[worker_id] = worker

        self._initialized = True
        logger.info(f"Initialized {len(self._workers)} workers")

    def start_all(self) -> None:
        """Start all workers."""
        if not self._initialized:
            raise RuntimeError("Worker manager not initialized")

        logger.info("Starting all workers")
        for worker_id, worker in self._workers.items():
            try:
                worker.start()
            except Exception as e:
                logger.error(f"Failed to start worker {worker_id}: {e}")

    async def stop_all(self) -> None:
        """Stop all workers."""
        logger.info("Stopping all workers")
        for worker_id, worker in self._workers.items():
            try:
                await worker.stop()
            except Exception as e:
                logger.error(f"Failed to stop worker {worker_id}: {e}")

    def start_worker(self, worker_id: str) -> bool:
        """Start a specific worker.

        Args:
            worker_id: Worker ID to start

        Returns:
            True if started successfully
        """
        worker = self._workers.get(worker_id)
        if not worker:
            logger.error(f"Worker {worker_id} not found")
            return False

        try:
            worker.start()
            return True
        except Exception as e:
            logger.error(f"Failed to start worker {worker_id}: {e}")
            return False

    async def stop_worker(self, worker_id: str) -> bool:
        """Stop a specific worker.

        Args:
            worker_id: Worker ID to stop

        Returns:
            True if stopped successfully
        """
        worker = self._workers.get(worker_id)
        if not worker:
            logger.error(f"Worker {worker_id} not found")
            return False

        try:
            await worker.stop()
            return True
        except Exception as e:
            logger.error(f"Failed to stop worker {worker_id}: {e}")
            return False

    def get_worker_status(self, worker_id: str) -> Optional[WorkerStatus]:
        """Get status of a specific worker.

        Args:
            worker_id: Worker ID

        Returns:
            WorkerStatus or None if not found
        """
        worker = self._workers.get(worker_id)
        if not worker:
            return None
        return worker.get_status()

    def get_all_statuses(self) -> List[WorkerStatus]:
        """Get status of all workers.

        Returns:
            List of worker statuses
        """
        return [worker.get_status() for worker in self._workers.values()]

    def list_workers(self) -> List[str]:
        """List all worker IDs.

        Returns:
            List of worker IDs
        """
        return list(self._workers.keys())


# Global worker manager instance
_worker_manager: Optional[WorkerManager] = None


def init_worker_manager(
    redis: RedisManager,
    config_service: StreamingConfigService,
) -> WorkerManager:
    """Initialize the global worker manager.

    Args:
        redis: Redis manager
        config_service: Configuration service

    Returns:
        WorkerManager instance
    """
    global _worker_manager
    _worker_manager = WorkerManager(redis, config_service)
    return _worker_manager


def get_worker_manager() -> Optional[WorkerManager]:
    """Get the global worker manager instance.

    Returns:
        WorkerManager or None if not initialized
    """
    return _worker_manager
