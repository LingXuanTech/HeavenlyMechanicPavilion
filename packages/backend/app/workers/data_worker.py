"""Data worker for polling vendor data and publishing to Redis."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

from ..cache import RedisManager
from ..schemas.streaming import (
    DataType,
    InstrumentConfig,
    RefreshCadence,
    StreamMessage,
    TelemetryRecord,
    UpdateType,
    WorkerStatus,
)
from ..services.streaming_config import StreamingConfigService

logger = logging.getLogger(__name__)


class DataWorker:
    """Background worker for polling vendor data."""

    def __init__(
        self,
        worker_id: str,
        data_type: DataType,
        redis: RedisManager,
        config_service: StreamingConfigService,
    ):
        """Initialize the data worker.

        Args:
            worker_id: Unique worker identifier
            data_type: Type of data to poll
            redis: Redis manager
            config_service: Configuration service
        """
        self.worker_id = worker_id
        self.data_type = data_type
        self.redis = redis
        self.config_service = config_service
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._status = WorkerStatus(
            worker_id=worker_id,
            data_type=data_type,
            status="stopped",
        )

    def start(self) -> None:
        """Start the worker."""
        if self._running:
            logger.warning(f"Worker {self.worker_id} already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run())
        self._status.status = "running"
        logger.info(f"Started worker {self.worker_id} for {self.data_type}")

    async def stop(self) -> None:
        """Stop the worker."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        self._status.status = "stopped"
        logger.info(f"Stopped worker {self.worker_id}")

    def get_status(self) -> WorkerStatus:
        """Get worker status.

        Returns:
            WorkerStatus: Current status
        """
        return self._status

    async def _run(self) -> None:
        """Main worker loop."""
        logger.info(f"Worker {self.worker_id} starting main loop")

        while self._running:
            try:
                # Get current configuration
                config = await self.config_service.get_config()

                if not config.global_enabled:
                    await asyncio.sleep(10)
                    continue

                # Get cadence for this data type
                cadence = await self.config_service.get_cadence(self.data_type)
                if not cadence or not cadence.enabled:
                    await asyncio.sleep(60)
                    continue

                # Calculate next run time
                self._status.next_run = datetime.utcnow()

                # Get enabled instruments for this data type
                instruments = [
                    inst
                    for inst in config.instruments
                    if inst.enabled and self.data_type in inst.data_types
                ]

                if not instruments:
                    await asyncio.sleep(cadence.interval_seconds)
                    continue

                # Poll data for each instrument
                for instrument in instruments:
                    if not self._running:
                        break

                    try:
                        await self._poll_instrument(instrument, cadence, config)
                    except Exception as e:
                        logger.error(
                            f"Error polling {instrument.symbol} for {self.data_type}: {e}",
                            exc_info=True,
                        )

                # Update status
                self._status.last_run = datetime.utcnow()
                self._status.next_run = None

                # Sleep until next interval
                await asyncio.sleep(cadence.interval_seconds)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in worker {self.worker_id}: {e}", exc_info=True)
                self._status.status = "error"
                self._status.last_error = str(e)
                self._status.error_count += 1
                await asyncio.sleep(60)

    async def _poll_instrument(
        self,
        instrument: InstrumentConfig,
        cadence: RefreshCadence,
        config: Any,
    ) -> None:
        """Poll data for a specific instrument.

        Args:
            instrument: Instrument configuration
            cadence: Refresh cadence
            config: Global configuration
        """
        symbol = instrument.symbol
        retry_count = 0
        max_retries = min(cadence.retry_attempts, config.max_retries)

        while retry_count <= max_retries:
            start_time = time.time()
            vendor_name = "unknown"

            try:
                # Get data from vendor plugin
                data, vendor_name = await self._fetch_data(symbol, instrument.custom_config)

                if data is None:
                    raise ValueError(f"No data returned for {symbol}")

                # Calculate latency
                latency_ms = (time.time() - start_time) * 1000

                # Create stream message
                message = StreamMessage(
                    channel=self._get_channel_name(symbol),
                    data_type=self.data_type,
                    update_type=UpdateType.SNAPSHOT,
                    timestamp=datetime.utcnow(),
                    symbol=symbol,
                    data=data,
                    vendor=vendor_name,
                    metadata={
                        "worker_id": self.worker_id,
                        "retry_count": retry_count,
                    },
                )

                # Publish to Redis
                await self._publish_message(message, config.cache_ttl_seconds)

                # Record telemetry
                await self._record_telemetry(
                    TelemetryRecord(
                        vendor=vendor_name,
                        data_type=self.data_type,
                        symbol=symbol,
                        timestamp=datetime.utcnow(),
                        success=True,
                        latency_ms=latency_ms,
                        retry_count=retry_count,
                        fallback_used=retry_count > 0 and cadence.vendor_fallback,
                    )
                )

                self._status.success_count += 1
                self._status.current_vendor = vendor_name
                break

            except Exception as e:
                latency_ms = (time.time() - start_time) * 1000

                # Record telemetry for failure
                await self._record_telemetry(
                    TelemetryRecord(
                        vendor=vendor_name,
                        data_type=self.data_type,
                        symbol=symbol,
                        timestamp=datetime.utcnow(),
                        success=False,
                        latency_ms=latency_ms,
                        error=str(e),
                        retry_count=retry_count,
                        fallback_used=False,
                    )
                )

                retry_count += 1

                if retry_count > max_retries:
                    logger.error(
                        f"Failed to fetch {self.data_type} for {symbol} after {max_retries} retries: {e}"
                    )
                    self._status.error_count += 1
                    self._status.last_error = str(e)
                    break

                # Exponential backoff
                backoff = cadence.retry_backoff_multiplier**retry_count
                await asyncio.sleep(min(backoff, 60))

    async def _fetch_data(
        self,
        symbol: str,
        custom_config: Dict[str, Any],
    ) -> tuple[Dict[str, Any], str]:
        """Fetch data from vendor plugin.

        Args:
            symbol: Symbol to fetch
            custom_config: Custom configuration

        Returns:
            Tuple of (data dict, vendor name)
        """
        # Import here to avoid circular imports
        from tradingagents.plugins import PluginCapability, get_registry

        registry = get_registry()

        # Map data type to capability
        capability_map = {
            DataType.MARKET_DATA: PluginCapability.STOCK_DATA,
            DataType.NEWS: PluginCapability.NEWS,
            DataType.FUNDAMENTALS: PluginCapability.FUNDAMENTALS,
            DataType.ANALYTICS: PluginCapability.INDICATORS,
            DataType.INSIDER_DATA: PluginCapability.INSIDER_SENTIMENT,
        }

        capability = capability_map.get(self.data_type)
        if not capability:
            raise ValueError(f"Unknown data type: {self.data_type}")

        # Get plugins for this capability
        plugins = registry.get_plugins_with_capability(capability)
        if not plugins:
            raise ValueError(f"No plugins available for {capability}")

        # Try each plugin
        for plugin in plugins:
            try:
                # Call appropriate method based on data type
                if self.data_type == DataType.MARKET_DATA:
                    # Use last 30 days for market data
                    from datetime import timedelta

                    end_date = datetime.utcnow()
                    start_date = end_date - timedelta(days=30)
                    result = plugin.get_stock_data(
                        symbol,
                        start_date.strftime("%Y-%m-%d"),
                        end_date.strftime("%Y-%m-%d"),
                    )
                elif self.data_type == DataType.NEWS:
                    result = plugin.get_news(symbol, limit=10)
                elif self.data_type == DataType.FUNDAMENTALS:
                    result = plugin.get_fundamentals(
                        symbol,
                        datetime.utcnow().strftime("%Y-%m-%d"),
                    )
                elif self.data_type == DataType.ANALYTICS:
                    from datetime import timedelta

                    end_date = datetime.utcnow()
                    start_date = end_date - timedelta(days=30)
                    result = plugin.get_indicators(
                        symbol,
                        start_date.strftime("%Y-%m-%d"),
                        end_date.strftime("%Y-%m-%d"),
                    )
                elif self.data_type == DataType.INSIDER_DATA:
                    result = plugin.get_insider_sentiment(symbol)
                else:
                    continue

                # Parse result (it's a formatted string from plugins)
                # For now, wrap it in a dict
                return {"raw_data": result, "symbol": symbol}, plugin.provider

            except NotImplementedError:
                continue
            except Exception as e:
                logger.debug(f"Plugin {plugin.provider} failed for {symbol}: {e}")
                continue

        raise ValueError(f"All plugins failed for {symbol}")

    def _get_channel_name(self, symbol: Optional[str] = None) -> str:
        """Get Redis channel name.

        Args:
            symbol: Optional symbol for symbol-specific channels

        Returns:
            Channel name
        """
        if symbol:
            return f"stream:{self.data_type.value}:{symbol}"
        return f"stream:{self.data_type.value}"

    async def _publish_message(self, message: StreamMessage, ttl: int) -> None:
        """Publish message to Redis.

        Args:
            message: Message to publish
            ttl: Cache TTL in seconds
        """
        # Serialize message
        message_json = json.dumps(message.model_dump(), default=str)

        # Publish to channel
        await self.redis.publish(message.channel, message_json)

        # Also cache the latest snapshot
        cache_key = f"latest:{message.channel}"
        await self.redis.set(cache_key, message_json, expire=ttl)

    async def _record_telemetry(self, record: TelemetryRecord) -> None:
        """Record telemetry data.

        Args:
            record: Telemetry record
        """
        # Store telemetry in Redis list (keep last 1000 records)
        telemetry_key = f"telemetry:{self.data_type.value}"
        record_json = json.dumps(record.model_dump(), default=str)

        await self.redis.client.lpush(telemetry_key, record_json)
        await self.redis.client.ltrim(telemetry_key, 0, 999)
