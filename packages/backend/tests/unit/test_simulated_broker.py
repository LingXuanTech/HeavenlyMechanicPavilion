from __future__ import annotations

from datetime import datetime

import pytest

from app.core.errors import ValidationError
from app.services.broker_adapter import MarketPrice, SimulatedBroker
from app.services.market_data import MarketDataService


class StubMarketDataService:
    def __init__(self, price: MarketPrice) -> None:
        self._price = price
        self.calls: list[str] = []

    async def get_latest_price(self, symbol: str) -> MarketPrice:
        self.calls.append(symbol)
        return MarketPrice(
            symbol=symbol.upper(),
            bid=self._price.bid,
            ask=self._price.ask,
            last=self._price.last,
            timestamp=datetime.utcnow(),
        )


@pytest.mark.asyncio
async def test_simulated_broker_uses_injected_market_data_service() -> None:
    base_price = MarketPrice(
        symbol="IGNORED",
        bid=99.5,
        ask=100.5,
        last=100.0,
        timestamp=datetime.utcnow(),
    )
    data_service = StubMarketDataService(price=base_price)
    broker = SimulatedBroker(market_data_service=data_service)

    quote = await broker.get_market_price("AAPL")

    assert data_service.calls == ["AAPL"]
    assert quote.symbol == "AAPL"
    assert quote.last == pytest.approx(base_price.last)
    assert quote.bid == pytest.approx(base_price.bid)
    assert quote.ask == pytest.approx(base_price.ask)


@pytest.mark.asyncio
async def test_simulated_broker_validates_symbol() -> None:
    broker = SimulatedBroker(market_data_service=MarketDataService())

    with pytest.raises(ValidationError):
        await broker.get_market_price(" ")
