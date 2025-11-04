from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest

from app.services.market_data import MarketDataService


@pytest.mark.asyncio
async def test_market_data_service_parses_vendor_payload() -> None:
    service = MarketDataService()
    payload = """# Stock data for TEST
Date,Open,High,Low,Close,Adj Close,Volume
2024-01-02,100.0,101.0,99.0,100.5,100.5,1000
2024-01-03,101.0,103.0,100.5,102.25,102.25,1200
"""

    with patch("app.services.market_data.route_to_vendor", return_value=payload):
        quote = await service.get_latest_price("test")

    assert quote.symbol == "TEST"
    assert quote.last == pytest.approx(102.25)
    assert quote.bid < quote.last < quote.ask
    assert isinstance(quote.timestamp, datetime)


@pytest.mark.asyncio
async def test_market_data_service_uses_configured_fallback() -> None:
    service = MarketDataService(fallback_prices={"MSFT": 250.0})

    with patch("app.services.market_data.route_to_vendor", side_effect=RuntimeError("boom")):
        quote = await service.get_latest_price("msft")

    assert quote.symbol == "MSFT"
    assert quote.last == pytest.approx(250.0)
    assert quote.bid < quote.ask


@pytest.mark.asyncio
async def test_market_data_service_reuses_cached_quote_on_failure() -> None:
    service = MarketDataService()
    payload = """Date,Open,High,Low,Close,Adj Close,Volume
2024-02-05,50,51,49,50.5,50.5,900
"""

    with patch("app.services.market_data.route_to_vendor", return_value=payload):
        first_quote = await service.get_latest_price("cache")

    with patch("app.services.market_data.route_to_vendor", side_effect=RuntimeError("fail")):
        second_quote = await service.get_latest_price("cache")

    assert second_quote.symbol == first_quote.symbol
    assert second_quote.last == pytest.approx(first_quote.last)
    assert second_quote.bid == pytest.approx(first_quote.bid)
    assert second_quote.ask == pytest.approx(first_quote.ask)
    assert second_quote is not first_quote
    assert second_quote.timestamp >= first_quote.timestamp
