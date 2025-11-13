from __future__ import annotations

import csv
import hashlib
import logging
from datetime import datetime, timedelta
from io import StringIO
from typing import TYPE_CHECKING, Dict, Optional

from tradingagents.plugins import route_to_vendor
from ..dependencies.services import get_cache_service
from ..cache import get_redis_manager

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .broker_adapter import MarketPrice


class MarketDataService:
    """Service responsible for retrieving deterministic market quotes.

    The service coordinates with the vendor plugin registry to obtain the latest
    market data for a given symbol. If vendor data is unavailable it falls back
    to a deterministic baseline so simulated trades remain reproducible.
    """

    def __init__(
        self,
        lookback_days: int = 5,
        spread_bps: float = 10.0,
        min_spread: float = 0.01,
        fallback_prices: Optional[Dict[str, float]] = None,
        use_redis_cache: bool = True,
    ) -> None:
        """Initialize the market data service.

        Args:
            lookback_days: Number of days of history to request from vendors.
            spread_bps: Bid/ask spread width in basis points (0.01% = 1 bps).
            min_spread: Minimum absolute spread applied when deriving bid/ask.
            fallback_prices: Optional static price map used when vendors fail.
            use_redis_cache: Whether to use Redis for caching market data.
        """
        self.lookback_days = lookback_days
        self.spread_bps = spread_bps
        self.min_spread = min_spread
        self.use_redis_cache = use_redis_cache
        self._fallback_prices = {
            symbol.upper(): float(price)
            for symbol, price in (fallback_prices or {}).items()
        }
        self._quote_cache: Dict[str, MarketPrice] = {}

    async def get_latest_price(self, symbol: str) -> MarketPrice:
        """Retrieve the latest market price for a symbol.

        Args:
            symbol: Equity ticker symbol.

        Returns:
            MarketPrice instance containing bid/ask/last quotes.
        """
        normalized_symbol = self._normalize_symbol(symbol)
        
        # Try to get from Redis cache first (if enabled)
        if self.use_redis_cache and get_redis_manager():
            try:
                cached_data = await self._get_cached_market_data(normalized_symbol)
                if cached_data:
                    logger.info("Using Redis cached market data for %s", normalized_symbol)
                    return self._dict_to_price(cached_data)
            except Exception as exc:
                logger.warning("Redis cache lookup failed for %s: %s", normalized_symbol, exc)
        
        # Try to get from memory cache
        cached_quote = self._quote_cache.get(normalized_symbol)
        if cached_quote is not None:
            logger.info("Using memory cached market data for %s", normalized_symbol)
            return self._clone_price(cached_quote)

        # Get from vendor
        quote: Optional[MarketPrice] = None
        try:
            quote = self._get_price_from_vendors(normalized_symbol)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "Market data vendor lookup failed for %s: %s",
                normalized_symbol,
                exc,
            )

        if quote is not None:
            # Cache in memory
            self._quote_cache[normalized_symbol] = quote
            
            # Cache in Redis (if enabled)
            if self.use_redis_cache and get_redis_manager():
                try:
                    await self._cache_market_data(normalized_symbol, quote)
                except Exception as exc:
                    logger.warning("Failed to cache market data in Redis for %s: %s", normalized_symbol, exc)
            
            return quote

        # Use fallback
        fallback_quote = self._build_fallback_price(normalized_symbol)
        self._quote_cache[normalized_symbol] = fallback_quote
        return fallback_quote

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _get_price_from_vendors(self, symbol: str) -> Optional[MarketPrice]:
        start_date = (datetime.utcnow() - timedelta(days=self.lookback_days)).strftime("%Y-%m-%d")
        end_date = datetime.utcnow().strftime("%Y-%m-%d")

        payload = route_to_vendor(
            "get_stock_data",
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
        )
        if not payload:
            return None

        try:
            return self._parse_vendor_payload(symbol, payload)
        except ValueError as exc:
            logger.warning("Unable to parse vendor response for %s: %s", symbol, exc)
            return None

    def _parse_vendor_payload(self, symbol: str, payload: str) -> MarketPrice:
        csv_lines = self._extract_primary_csv_lines(payload)
        if not csv_lines:
            raise ValueError("Vendor response did not contain tabular price data")

        reader = csv.DictReader(StringIO("\n".join(csv_lines)))
        rows = [row for row in reader if row]
        if not rows:
            raise ValueError("Vendor response missing price rows")

        latest_row = rows[-1]
        last_value = self._coerce_float(
            latest_row.get("Adj Close")
            or latest_row.get("Close")
            or latest_row.get("close")
            or latest_row.get("adj_close")
        )
        if last_value is None:
            raise ValueError("Vendor response missing closing price")

        timestamp = self._parse_timestamp(latest_row)
        return self._build_price(symbol, last_value, timestamp)

    def _extract_primary_csv_lines(self, payload: str) -> list[str]:
        lines = payload.splitlines()
        csv_lines: list[str] = []
        header_found = False

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                if header_found and csv_lines:
                    break
                continue

            if line.startswith("#"):
                if header_found:
                    break
                continue

            if not header_found:
                if line.startswith("Date") or line.startswith("date"):
                    header_found = True
                    csv_lines.append(line)
                continue

            if header_found and (line.startswith("Date") or line.startswith("date")):
                break

            csv_lines.append(line)

        return csv_lines

    def _coerce_float(self, value: Optional[str]) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _parse_timestamp(self, row: Dict[str, str]) -> datetime:
        timestamp_fields = ("Datetime", "Date", "date", "timestamp", "Timestamp")
        for field in timestamp_fields:
            raw_value = row.get(field)
            if not raw_value:
                continue

            candidate = str(raw_value).strip()
            if not candidate:
                continue

            candidate = candidate.replace("Z", "")

            try:
                return datetime.fromisoformat(candidate)
            except ValueError:
                pass

            for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(candidate, fmt)
                except ValueError:
                    continue

        return datetime.utcnow()

    def _build_price(
        self,
        symbol: str,
        last: float,
        timestamp: Optional[datetime] = None,
    ) -> MarketPrice:
        from .broker_adapter import MarketPrice

        last_value = round(float(last), 4)
        spread_value = max(last_value * (self.spread_bps / 10000), self.min_spread)
        half_spread = spread_value / 2
        bid = max(0.0, round(last_value - half_spread, 4))
        ask = round(last_value + half_spread, 4)
        resolved_timestamp = timestamp or datetime.utcnow()

        return MarketPrice(
            symbol=symbol,
            bid=bid,
            ask=ask,
            last=last_value,
            timestamp=resolved_timestamp,
        )

    def _build_fallback_price(self, symbol: str) -> MarketPrice:
        baseline = self._fallback_prices.get(symbol)
        if baseline is None:
            baseline = self._derive_baseline(symbol)
        return self._build_price(symbol, baseline)

    def _derive_baseline(self, symbol: str) -> float:
        digest = hashlib.sha256(symbol.encode("utf-8")).hexdigest()
        scaled = int(digest[:8], 16) % 5000  # Range 0 - 4999
        baseline = 50 + (scaled / 10)  # Deterministic baseline between 50 and 549.9
        return round(baseline, 4)

    def _clone_price(self, price: MarketPrice) -> MarketPrice:
        from .broker_adapter import MarketPrice

        return MarketPrice(
            symbol=price.symbol,
            bid=price.bid,
            ask=price.ask,
            last=price.last,
            timestamp=datetime.utcnow(),
        )

    def _normalize_symbol(self, symbol: str) -> str:
        stripped = (symbol or "").strip()
        if not stripped:
            raise ValueError("Symbol must be provided")
        return stripped.upper()

    async def _get_cached_market_data(self, symbol: str) -> Optional[dict]:
        """Get market data from Redis cache."""
        try:
            cache_service = get_cache_service()
            date_key = datetime.utcnow().strftime("%Y-%m-%d")
            return await cache_service.get_market_data(symbol, date_key)
        except Exception:
            return None

    async def _cache_market_data(self, symbol: str, quote: MarketPrice) -> None:
        """Cache market data in Redis."""
        try:
            cache_service = get_cache_service()
            date_key = datetime.utcnow().strftime("%Y-%m-%d")
            
            data = {
                "symbol": quote.symbol,
                "bid": quote.bid,
                "ask": quote.ask,
                "last": quote.last,
                "timestamp": quote.timestamp.isoformat(),
            }
            
            await cache_service.cache_market_data(symbol, date_key, data, expire=300)  # 5 minutes
        except Exception as exc:
            logger.warning("Failed to cache market data for %s: %s", symbol, exc)

    def _dict_to_price(self, data: dict) -> MarketPrice:
        """Convert dictionary to MarketPrice object."""
        from .broker_adapter import MarketPrice
        
        return MarketPrice(
            symbol=data["symbol"],
            bid=float(data["bid"]),
            ask=float(data["ask"]),
            last=float(data["last"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


__all__ = ["MarketDataService"]
