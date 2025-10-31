"""Service for managing streaming configuration."""

from __future__ import annotations

import json
from typing import List, Optional

from ..cache import RedisManager
from ..schemas.streaming import (
    DataType,
    InstrumentConfig,
    RefreshCadence,
    StreamingConfig,
)


class StreamingConfigService:
    """Manages streaming configuration with Redis persistence."""

    INSTRUMENTS_KEY = "streaming:instruments"
    CADENCES_KEY = "streaming:cadences"
    GLOBAL_CONFIG_KEY = "streaming:global_config"

    def __init__(self, redis: RedisManager):
        """Initialize the service.

        Args:
            redis: Redis manager instance
        """
        self.redis = redis

    async def get_config(self) -> StreamingConfig:
        """Get complete streaming configuration.

        Returns:
            StreamingConfig: Current configuration
        """
        instruments_data = await self.redis.get(self.INSTRUMENTS_KEY)
        cadences_data = await self.redis.get(self.CADENCES_KEY)
        global_data = await self.redis.get(self.GLOBAL_CONFIG_KEY)

        instruments = (
            [InstrumentConfig(**i) for i in json.loads(instruments_data)]
            if instruments_data
            else []
        )

        cadences = (
            [RefreshCadence(**c) for c in json.loads(cadences_data)]
            if cadences_data
            else self._default_cadences()
        )

        global_config = json.loads(global_data) if global_data else {}

        return StreamingConfig(
            instruments=instruments,
            cadences=cadences,
            global_enabled=global_config.get("global_enabled", True),
            max_retries=global_config.get("max_retries", 3),
            cache_ttl_seconds=global_config.get("cache_ttl_seconds", 300),
        )

    async def update_config(self, config: StreamingConfig) -> StreamingConfig:
        """Update streaming configuration.

        Args:
            config: New configuration

        Returns:
            StreamingConfig: Updated configuration
        """
        # Save instruments
        instruments_json = json.dumps([i.model_dump() for i in config.instruments])
        await self.redis.set(self.INSTRUMENTS_KEY, instruments_json)

        # Save cadences
        cadences_json = json.dumps([c.model_dump() for c in config.cadences])
        await self.redis.set(self.CADENCES_KEY, cadences_json)

        # Save global config
        global_config = {
            "global_enabled": config.global_enabled,
            "max_retries": config.max_retries,
            "cache_ttl_seconds": config.cache_ttl_seconds,
        }
        await self.redis.set(self.GLOBAL_CONFIG_KEY, json.dumps(global_config))

        return config

    async def add_instrument(self, instrument: InstrumentConfig) -> InstrumentConfig:
        """Add or update an instrument.

        Args:
            instrument: Instrument configuration

        Returns:
            InstrumentConfig: Added/updated instrument
        """
        config = await self.get_config()

        # Remove existing if present
        config.instruments = [i for i in config.instruments if i.symbol != instrument.symbol]

        # Add new
        config.instruments.append(instrument)

        await self.update_config(config)
        return instrument

    async def remove_instrument(self, symbol: str) -> bool:
        """Remove an instrument.

        Args:
            symbol: Symbol to remove

        Returns:
            bool: True if removed, False if not found
        """
        config = await self.get_config()
        original_count = len(config.instruments)

        config.instruments = [i for i in config.instruments if i.symbol != symbol]

        if len(config.instruments) < original_count:
            await self.update_config(config)
            return True

        return False

    async def get_instrument(self, symbol: str) -> Optional[InstrumentConfig]:
        """Get configuration for a specific instrument.

        Args:
            symbol: Symbol to get

        Returns:
            InstrumentConfig or None if not found
        """
        config = await self.get_config()
        for instrument in config.instruments:
            if instrument.symbol == symbol:
                return instrument
        return None

    async def list_instruments(self) -> List[InstrumentConfig]:
        """List all configured instruments.

        Returns:
            List of instrument configurations
        """
        config = await self.get_config()
        return config.instruments

    async def update_cadence(self, cadence: RefreshCadence) -> RefreshCadence:
        """Update refresh cadence for a data type.

        Args:
            cadence: Cadence configuration

        Returns:
            RefreshCadence: Updated cadence
        """
        config = await self.get_config()

        # Remove existing if present
        config.cadences = [c for c in config.cadences if c.data_type != cadence.data_type]

        # Add new
        config.cadences.append(cadence)

        await self.update_config(config)
        return cadence

    async def get_cadence(self, data_type: DataType) -> Optional[RefreshCadence]:
        """Get refresh cadence for a data type.

        Args:
            data_type: Data type to get cadence for

        Returns:
            RefreshCadence or None if not found
        """
        config = await self.get_config()
        for cadence in config.cadences:
            if cadence.data_type == data_type:
                return cadence
        return None

    def _default_cadences(self) -> List[RefreshCadence]:
        """Get default cadence configurations.

        Returns:
            List of default cadences
        """
        return [
            RefreshCadence(data_type=DataType.MARKET_DATA, interval_seconds=60),
            RefreshCadence(data_type=DataType.NEWS, interval_seconds=300),
            RefreshCadence(data_type=DataType.FUNDAMENTALS, interval_seconds=3600),
            RefreshCadence(data_type=DataType.ANALYTICS, interval_seconds=600),
            RefreshCadence(data_type=DataType.INSIDER_DATA, interval_seconds=1800),
        ]
