"""Market calendar service for checking trading hours and market status."""

from __future__ import annotations

import logging
from datetime import datetime, time, timezone
from typing import Optional

from alpaca.trading.client import TradingClient

from ..core.errors import ExternalServiceError

logger = logging.getLogger(__name__)


class MarketCalendarService:
    """Service for checking market hours and trading calendar."""

    def __init__(self, trading_client: Optional[TradingClient] = None):
        """Initialize market calendar service.
        
        Args:
            trading_client: Alpaca trading client (optional for testing)
        """
        self.trading_client = trading_client
        self._cached_clock = None
        self._cache_timestamp = None
        self._cache_ttl_seconds = 60  # Cache clock data for 1 minute

    async def is_market_open(self) -> bool:
        """Check if the market is currently open.
        
        Returns:
            True if market is open, False otherwise
            
        Raises:
            ExternalServiceError: If unable to get market status
        """
        try:
            clock = await self._get_clock()
            return clock.is_open
            
        except Exception as e:
            logger.error(f"Failed to check market status: {e}")
            raise ExternalServiceError(
                f"Unable to determine market status: {e}",
                details={"error": str(e)}
            )

    async def get_next_market_open(self) -> datetime:
        """Get the next market open time.
        
        Returns:
            Next market open datetime (UTC)
            
        Raises:
            ExternalServiceError: If unable to get market calendar
        """
        try:
            clock = await self._get_clock()
            return clock.next_open
            
        except Exception as e:
            logger.error(f"Failed to get next market open time: {e}")
            raise ExternalServiceError(
                f"Unable to get next market open time: {e}",
                details={"error": str(e)}
            )

    async def get_next_market_close(self) -> datetime:
        """Get the next market close time.
        
        Returns:
            Next market close datetime (UTC)
            
        Raises:
            ExternalServiceError: If unable to get market calendar
        """
        try:
            clock = await self._get_clock()
            return clock.next_close
            
        except Exception as e:
            logger.error(f"Failed to get next market close time: {e}")
            raise ExternalServiceError(
                f"Unable to get next market close time: {e}",
                details={"error": str(e)}
            )

    async def get_market_status(self) -> dict:
        """Get comprehensive market status information.
        
        Returns:
            Dictionary containing:
            - is_open: Whether market is currently open
            - timestamp: Current time (UTC)
            - next_open: Next market open time
            - next_close: Next market close time
            
        Raises:
            ExternalServiceError: If unable to get market status
        """
        try:
            clock = await self._get_clock()
            
            return {
                "is_open": clock.is_open,
                "timestamp": clock.timestamp,
                "next_open": clock.next_open,
                "next_close": clock.next_close,
            }
            
        except Exception as e:
            logger.error(f"Failed to get market status: {e}")
            raise ExternalServiceError(
                f"Unable to get market status: {e}",
                details={"error": str(e)}
            )

    async def is_regular_trading_hours(self) -> bool:
        """Check if current time is within regular trading hours (9:30 AM - 4:00 PM ET).
        
        Returns:
            True if within regular trading hours, False otherwise
        """
        try:
            clock = await self._get_clock()
            
            if not clock.is_open:
                return False
            
            # Get current time in ET
            current_time = clock.timestamp.time()
            
            # Regular trading hours: 9:30 AM - 4:00 PM ET
            market_open = time(9, 30)
            market_close = time(16, 0)
            
            return market_open <= current_time < market_close
            
        except Exception as e:
            logger.error(f"Failed to check trading hours: {e}")
            return False

    async def _get_clock(self):
        """Get clock data from Alpaca API with caching.
        
        Returns:
            Alpaca Clock object
            
        Raises:
            ExternalServiceError: If trading client not configured or API fails
        """
        if not self.trading_client:
            raise ExternalServiceError(
                "Trading client not configured",
                details={"service": "MarketCalendarService"}
            )
        
        # Check cache
        now = datetime.now(timezone.utc)
        if (
            self._cached_clock is not None
            and self._cache_timestamp is not None
            and (now - self._cache_timestamp).total_seconds() < self._cache_ttl_seconds
        ):
            return self._cached_clock
        
        # Fetch fresh data
        try:
            clock = self.trading_client.get_clock()
            self._cached_clock = clock
            self._cache_timestamp = now
            
            logger.debug(
                f"Market status: {'OPEN' if clock.is_open else 'CLOSED'}, "
                f"next_open={clock.next_open}, next_close={clock.next_close}"
            )
            
            return clock
            
        except Exception as e:
            logger.error(f"Failed to get clock from Alpaca: {e}")
            raise ExternalServiceError(
                f"Failed to get market clock: {e}",
                details={"error": str(e)}
            )


class SimulatedMarketCalendar(MarketCalendarService):
    """Simulated market calendar for testing (always open)."""

    def __init__(self):
        """Initialize simulated calendar."""
        super().__init__(trading_client=None)
        logger.info("Using SimulatedMarketCalendar (always open)")

    async def is_market_open(self) -> bool:
        """Always returns True for simulation."""
        return True

    async def get_next_market_open(self) -> datetime:
        """Return current time for simulation."""
        return datetime.now(timezone.utc)

    async def get_next_market_close(self) -> datetime:
        """Return far future time for simulation."""
        return datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    async def get_market_status(self) -> dict:
        """Return simulated market status (always open)."""
        now = datetime.now(timezone.utc)
        return {
            "is_open": True,
            "timestamp": now,
            "next_open": now,
            "next_close": datetime(2099, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
        }

    async def is_regular_trading_hours(self) -> bool:
        """Always returns True for simulation."""
        return True