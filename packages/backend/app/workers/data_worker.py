"""Data worker for polling vendor data and publishing to Redis."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from ..cache import RedisManager
from ..config import get_settings
from ..core.errors import CircuitBreakerOpenError, VendorAPIError
from ..core.resilience import CircuitBreaker, RetryPolicy, execute_with_retry
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
        self._settings = get_settings()
        self._vendor_breakers: Dict[str, CircuitBreaker] = {}

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
        start_time = time.time()

        try:
            data, vendor_name, retry_count = await self._fetch_data(
                symbol, instrument.custom_config, cadence, config
            )
            latency_ms = (time.time() - start_time) * 1000

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

            await self._publish_message(message, config.cache_ttl_seconds)

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

        except CircuitBreakerOpenError as exc:
            latency_ms = (time.time() - start_time) * 1000
            vendor_name = exc.details.get("vendor", "unknown")
            await self._record_telemetry(
                TelemetryRecord(
                    vendor=vendor_name,
                    data_type=self.data_type,
                    symbol=symbol,
                    timestamp=datetime.utcnow(),
                    success=False,
                    latency_ms=latency_ms,
                    error=exc.message,
                    retry_count=exc.details.get("attempts", 1) - 1,
                    fallback_used=False,
                )
            )
            self._status.error_count += 1
            self._status.last_error = exc.message
            logger.warning(
                "Circuit breaker open for vendor %s on %s: %s",
                vendor_name,
                symbol,
                exc.message,
            )
        except VendorAPIError as exc:
            latency_ms = (time.time() - start_time) * 1000
            vendor_name = exc.details.get("vendor", "unknown")
            await self._record_telemetry(
                TelemetryRecord(
                    vendor=vendor_name,
                    data_type=self.data_type,
                    symbol=symbol,
                    timestamp=datetime.utcnow(),
                    success=False,
                    latency_ms=latency_ms,
                    error=exc.message,
                    retry_count=max(0, exc.details.get("attempts", 1) - 1),
                    fallback_used=False,
                )
            )
            self._status.error_count += 1
            self._status.last_error = exc.message
            logger.error(
                "Vendor API failure for %s/%s: %s",
                vendor_name,
                symbol,
                exc.message,
            )

    async def _fetch_data(
        self,
        symbol: str,
        custom_config: Dict[str, Any],
        cadence: RefreshCadence,
        config: Any,
    ) -> tuple[Dict[str, Any], str, int]:
        """Fetch data from vendor plugins with retries and circuit breakers."""
        from tradingagents.plugins import PluginCapability, get_registry

        registry = get_registry()

        capability_map = {
            DataType.MARKET_DATA: PluginCapability.STOCK_DATA,
            DataType.NEWS: PluginCapability.NEWS,
            DataType.FUNDAMENTALS: PluginCapability.FUNDAMENTALS,
            DataType.ANALYTICS: PluginCapability.INDICATORS,
            DataType.INSIDER_DATA: PluginCapability.INSIDER_SENTIMENT,
        }

        capability = capability_map.get(self.data_type)
        if not capability:
            raise VendorAPIError(
                f"Unknown data type: {self.data_type}",
                details={"data_type": self.data_type.value, "symbol": symbol},
            )

        plugins = registry.get_plugins_with_capability(capability)
        if not plugins:
            raise VendorAPIError(
                f"No plugins available for capability {capability.value}",
                details={"data_type": self.data_type.value, "symbol": symbol},
            )

        last_error: Optional[VendorAPIError] = None
        breaker_error: Optional[CircuitBreakerOpenError] = None

        for plugin in plugins:
            vendor_name = plugin.provider
            retry_policy = self._build_retry_policy(cadence, config)
            circuit_breaker = self._get_circuit_breaker(vendor_name)
            attempt_counter = {"count": 0}

            def plugin_call() -> Any:
                attempt_counter["count"] += 1
                return self._invoke_plugin(plugin, symbol, custom_config)

            metadata = {
                "vendor": vendor_name,
                "symbol": symbol,
                "data_type": self.data_type.value,
            }

            try:
                result = await execute_with_retry(
                    plugin_call,
                    retry_policy=retry_policy,
                    circuit_breaker=circuit_breaker,
                    logger=logger,
                    metadata=metadata,
                    failure_exception_cls=VendorAPIError,
                    run_in_executor=True,
                )
                retry_count = max(0, attempt_counter["count"] - 1)
                payload = {"raw_data": result, "symbol": symbol}
                return payload, vendor_name, retry_count
            except CircuitBreakerOpenError as exc:
                exc.details.setdefault("vendor", vendor_name)
                exc.details.setdefault("symbol", symbol)
                breaker_error = exc
                continue
            except VendorAPIError as exc:
                exc.details.setdefault("vendor", vendor_name)
                exc.details.setdefault("symbol", symbol)
                last_error = exc
                continue

        if last_error is not None:
            raise last_error
        if breaker_error is not None:
            raise breaker_error

        raise VendorAPIError(
            f"All plugins failed for {symbol}",
            details={"symbol": symbol, "data_type": self.data_type.value},
        )

    def _build_retry_policy(self, cadence: RefreshCadence, config: Any) -> RetryPolicy:
        attempts = max(1, min(cadence.retry_attempts or 1, config.max_retries or 1))
        return RetryPolicy(
            max_attempts=attempts,
            initial_backoff=self._settings.retry_default_backoff_seconds,
            max_backoff=self._settings.retry_max_backoff_seconds,
            multiplier=max(1.0, cadence.retry_backoff_multiplier),
            jitter=min(1.0, self._settings.retry_default_backoff_seconds),
            retry_exceptions=(Exception,),
        )

    def _get_circuit_breaker(self, vendor_name: str) -> CircuitBreaker:
        if vendor_name not in self._vendor_breakers:
            self._vendor_breakers[vendor_name] = CircuitBreaker(
                failure_threshold=self._settings.circuit_breaker_failure_threshold,
                recovery_timeout=self._settings.circuit_breaker_recovery_seconds,
                half_open_success_threshold=self._settings.circuit_breaker_half_open_successes,
                name=vendor_name,
            )
        return self._vendor_breakers[vendor_name]

    def _invoke_plugin(
        self,
        plugin: Any,
        symbol: str,
        custom_config: Dict[str, Any],
    ) -> Any:
        if self.data_type == DataType.MARKET_DATA:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            return plugin.get_stock_data(
                symbol,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
            )
        if self.data_type == DataType.NEWS:
            limit = custom_config.get("limit", 10)
            return plugin.get_news(symbol, limit=limit)
        if self.data_type == DataType.FUNDAMENTALS:
            return plugin.get_fundamentals(symbol, datetime.utcnow().strftime("%Y-%m-%d"))
        if self.data_type == DataType.ANALYTICS:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=30)
            return plugin.get_indicators(
                symbol,
                start_date.strftime("%Y-%m-%d"),
                end_date.strftime("%Y-%m-%d"),
            )
        if self.data_type == DataType.INSIDER_DATA:
            return plugin.get_insider_sentiment(symbol)
        raise VendorAPIError(
            f"Unsupported data type {self.data_type.value}",
            details={"data_type": self.data_type.value},
        )

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
