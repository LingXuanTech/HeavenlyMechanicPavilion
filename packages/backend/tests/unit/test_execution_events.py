"""Unit tests for execution event schemas and publishing."""

from datetime import datetime
from unittest.mock import Mock, MagicMock

import pytest

from app.schemas.execution_events import (
    ExecutionEvent,
    ExecutionEventType,
    OrderEventData,
    PositionEventData,
    RiskEventData,
    PortfolioEventData,
)
from app.services.events import SessionEventManager


class TestExecutionEventSchemas:
    """Test execution event schemas."""

    def test_order_event_data_creation(self):
        """Test creating order event data."""
        order_data = OrderEventData(
            symbol="AAPL",
            action="BUY",
            quantity=100.0,
            order_type="MARKET",
            status="FILLED",
            order_id="ord_123",
            filled_quantity=100.0,
            average_fill_price=150.50,
            commission=1.00,
            fees=0.10,
        )

        assert order_data.symbol == "AAPL"
        assert order_data.action == "BUY"
        assert order_data.quantity == 100.0
        assert order_data.order_type == "MARKET"
        assert order_data.status == "FILLED"
        assert order_data.order_id == "ord_123"
        assert order_data.filled_quantity == 100.0
        assert order_data.average_fill_price == 150.50
        assert order_data.commission == 1.00
        assert order_data.fees == 0.10

    def test_position_event_data_creation(self):
        """Test creating position event data."""
        position_data = PositionEventData(
            symbol="AAPL",
            quantity=100.0,
            average_cost=150.00,
            current_price=155.00,
            unrealized_pnl=500.00,
            position_type="LONG",
        )

        assert position_data.symbol == "AAPL"
        assert position_data.quantity == 100.0
        assert position_data.average_cost == 150.00
        assert position_data.current_price == 155.00
        assert position_data.unrealized_pnl == 500.00
        assert position_data.position_type == "LONG"

    def test_risk_event_data_creation(self):
        """Test creating risk event data."""
        risk_data = RiskEventData(
            symbol="AAPL",
            reason="Stop loss triggered",
            current_price=140.00,
            stop_loss_price=145.00,
        )

        assert risk_data.symbol == "AAPL"
        assert risk_data.reason == "Stop loss triggered"
        assert risk_data.current_price == 140.00
        assert risk_data.stop_loss_price == 145.00

    def test_portfolio_event_data_creation(self):
        """Test creating portfolio event data."""
        portfolio_data = PortfolioEventData(
            portfolio_id=1,
            current_capital=50000.00,
            total_value=75000.00,
            unrealized_pnl=5000.00,
            realized_pnl=2000.00,
            positions_count=3,
        )

        assert portfolio_data.portfolio_id == 1
        assert portfolio_data.current_capital == 50000.00
        assert portfolio_data.total_value == 75000.00
        assert portfolio_data.unrealized_pnl == 5000.00
        assert portfolio_data.realized_pnl == 2000.00
        assert portfolio_data.positions_count == 3

    def test_execution_event_with_order_data(self):
        """Test creating execution event with order data."""
        order_data = OrderEventData(
            symbol="AAPL",
            action="BUY",
            quantity=100.0,
            order_type="MARKET",
            status="FILLED",
        )

        event = ExecutionEvent(
            event_type=ExecutionEventType.ORDER_FILLED,
            session_id="sess_123",
            portfolio_id=1,
            order_data=order_data,
            message="Order filled successfully",
        )

        assert event.event_type == ExecutionEventType.ORDER_FILLED
        assert event.session_id == "sess_123"
        assert event.portfolio_id == 1
        assert event.order_data == order_data
        assert event.message == "Order filled successfully"
        assert isinstance(event.timestamp, datetime)

    def test_execution_event_with_position_data(self):
        """Test creating execution event with position data."""
        position_data = PositionEventData(
            symbol="AAPL",
            quantity=100.0,
            average_cost=150.00,
            current_price=155.00,
            unrealized_pnl=500.00,
        )

        event = ExecutionEvent(
            event_type=ExecutionEventType.POSITION_OPENED,
            session_id="sess_123",
            portfolio_id=1,
            position_data=position_data,
            message="Position opened",
        )

        assert event.event_type == ExecutionEventType.POSITION_OPENED
        assert event.position_data == position_data

    def test_execution_event_with_risk_data(self):
        """Test creating execution event with risk data."""
        risk_data = RiskEventData(
            symbol="AAPL",
            reason="Stop loss triggered",
            current_price=140.00,
        )

        event = ExecutionEvent(
            event_type=ExecutionEventType.STOP_LOSS_TRIGGERED,
            session_id="sess_123",
            portfolio_id=1,
            risk_data=risk_data,
            message="Stop loss triggered",
        )

        assert event.event_type == ExecutionEventType.STOP_LOSS_TRIGGERED
        assert event.risk_data == risk_data

    def test_execution_event_serialization(self):
        """Test execution event serialization to JSON."""
        order_data = OrderEventData(
            symbol="AAPL",
            action="BUY",
            quantity=100.0,
            order_type="MARKET",
            status="FILLED",
        )

        event = ExecutionEvent(
            event_type=ExecutionEventType.ORDER_FILLED,
            session_id="sess_123",
            portfolio_id=1,
            order_data=order_data,
            message="Order filled",
        )

        json_data = event.model_dump(mode='json')

        assert json_data["event_type"] == "order_filled"
        assert json_data["session_id"] == "sess_123"
        assert json_data["portfolio_id"] == 1
        assert json_data["order_data"]["symbol"] == "AAPL"
        assert json_data["message"] == "Order filled"
        assert "timestamp" in json_data


class TestEventPublishing:
    """Test event publishing through SessionEventManager."""

    def test_publish_event_to_manager(self):
        """Test publishing an event to the event manager."""
        event_manager = SessionEventManager()
        session_id = "sess_123"

        # Create a stream for the session
        import asyncio
        loop = asyncio.new_event_loop()
        
        async def setup():
            await event_manager.create_stream(session_id)
        
        loop.run_until_complete(setup())

        # Create an event
        event = ExecutionEvent(
            event_type=ExecutionEventType.ORDER_SUBMITTED,
            session_id=session_id,
            portfolio_id=1,
            order_data=OrderEventData(
                symbol="AAPL",
                action="BUY",
                quantity=100.0,
                order_type="MARKET",
                status="SUBMITTED",
            ),
            message="Order submitted",
        )

        # Publish event
        result = event_manager.publish(session_id, event.model_dump(mode='json'))

        assert result is True

    def test_publish_to_nonexistent_session(self):
        """Test publishing to a nonexistent session."""
        event_manager = SessionEventManager()

        event = ExecutionEvent(
            event_type=ExecutionEventType.ORDER_SUBMITTED,
            session_id="nonexistent",
            portfolio_id=1,
            order_data=OrderEventData(
                symbol="AAPL",
                action="BUY",
                quantity=100.0,
                order_type="MARKET",
                status="SUBMITTED",
            ),
        )

        result = event_manager.publish("nonexistent", event.model_dump(mode='json'))

        assert result is False

    def test_get_recent_events(self):
        """Test retrieving recent events from buffer."""
        event_manager = SessionEventManager(max_buffer_size=10)
        session_id = "sess_123"

        import asyncio
        loop = asyncio.new_event_loop()
        
        async def setup():
            await event_manager.create_stream(session_id)
        
        loop.run_until_complete(setup())

        # Publish multiple events
        for i in range(5):
            event = ExecutionEvent(
                event_type=ExecutionEventType.ORDER_SUBMITTED,
                session_id=session_id,
                portfolio_id=1,
                order_data=OrderEventData(
                    symbol=f"SYM{i}",
                    action="BUY",
                    quantity=100.0,
                    order_type="MARKET",
                    status="SUBMITTED",
                ),
                message=f"Order {i}",
            )
            event_manager.publish(session_id, event.model_dump(mode='json'))

        # Get recent events
        recent_events = event_manager.get_recent_events(session_id)

        assert len(recent_events) == 5
        assert all("timestamp" in e for e in recent_events)
        assert all("event" in e for e in recent_events)

    def test_event_buffer_max_size(self):
        """Test that event buffer respects max size."""
        max_size = 3
        event_manager = SessionEventManager(max_buffer_size=max_size)
        session_id = "sess_123"

        import asyncio
        loop = asyncio.new_event_loop()
        
        async def setup():
            await event_manager.create_stream(session_id)
        
        loop.run_until_complete(setup())

        # Publish more events than buffer size
        for i in range(10):
            event = ExecutionEvent(
                event_type=ExecutionEventType.ORDER_SUBMITTED,
                session_id=session_id,
                portfolio_id=1,
                order_data=OrderEventData(
                    symbol=f"SYM{i}",
                    action="BUY",
                    quantity=100.0,
                    order_type="MARKET",
                    status="SUBMITTED",
                ),
            )
            event_manager.publish(session_id, event.model_dump(mode='json'))

        # Buffer should only contain last max_size events
        recent_events = event_manager.get_recent_events(session_id)

        assert len(recent_events) == max_size
        # Verify we have the most recent events (SYM7, SYM8, SYM9)
        symbols = [e["event"]["order_data"]["symbol"] for e in recent_events]
        assert "SYM7" in symbols
        assert "SYM8" in symbols
        assert "SYM9" in symbols