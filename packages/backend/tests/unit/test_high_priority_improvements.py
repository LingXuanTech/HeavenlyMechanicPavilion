"""Unit tests for high priority improvements."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.auto_trading_orchestrator import AutoTradingOrchestrator
from app.services.execution import ExecutionService
from app.services.risk_management import RiskManagementService, RiskConstraints
from app.services.events import SessionEventManager
from app.db.models import Position, Trade
from app.schemas.execution_events import ExecutionEvent, ExecutionEventType


class TestAutoTradingEventIntegration:
    """Test event publishing in AutoTradingOrchestrator."""

    @pytest.fixture
    def mock_event_manager(self):
        """Create mock event manager."""
        manager = MagicMock(spec=SessionEventManager)
        manager.publish = MagicMock(return_value=True)
        return manager

    @pytest.fixture
    def orchestrator(self, mock_event_manager):
        """Create orchestrator with event manager."""
        graph_service = MagicMock()
        trading_session_service = MagicMock()
        
        return AutoTradingOrchestrator(
            graph_service=graph_service,
            trading_session_service=trading_session_service,
            event_manager=mock_event_manager,
        )

    @pytest.mark.asyncio
    async def test_emit_event_with_session_id(self, orchestrator, mock_event_manager):
        """Test that events are published with session ID."""
        session_id = "sess_123"
        event = {
            "type": "agent_decision",
            "symbol": "AAPL",
            "session_id": session_id,
        }
        
        await orchestrator._emit_event(event)
        
        mock_event_manager.publish.assert_called_once_with(session_id, event)

    @pytest.mark.asyncio
    async def test_emit_event_without_session_id(self, orchestrator, mock_event_manager):
        """Test that events without session ID are not published."""
        event = {
            "type": "agent_decision",
            "symbol": "AAPL",
        }
        
        await orchestrator._emit_event(event)
        
        mock_event_manager.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_emit_event_handles_exception(self, orchestrator, mock_event_manager):
        """Test that event publishing errors are handled gracefully."""
        mock_event_manager.publish.side_effect = Exception("Publishing failed")
        
        event = {
            "type": "agent_decision",
            "symbol": "AAPL",
            "session_id": "sess_123",
        }
        
        # Should not raise exception
        await orchestrator._emit_event(event)


class TestOrderCancellation:
    """Test order cancellation functionality."""

    @pytest.fixture
    def execution_service(self):
        """Create execution service for testing."""
        broker = MagicMock()
        return ExecutionService(broker=broker)

    @pytest.mark.asyncio
    async def test_cancel_filled_order(self, execution_service):
        """Test that filled orders cannot be cancelled."""
        session = AsyncMock()
        
        # Create a filled trade
        trade = Trade(
            id=1,
            portfolio_id=1,
            symbol="AAPL",
            action="BUY",
            quantity=100,
            order_type="MARKET",
            status="FILLED",
        )
        
        with patch('app.services.execution.TradeRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get.return_value = trade
            mock_repo_class.return_value = mock_repo
            
            result = await execution_service.cancel_order(session, trade_id=1)
            
            assert result.status == "FILLED"
            # Trade should not be updated
            mock_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_pending_order(self, execution_service):
        """Test that pending orders can be cancelled."""
        session = AsyncMock()
        
        # Create a pending trade
        trade = Trade(
            id=1,
            portfolio_id=1,
            symbol="AAPL",
            action="BUY",
            quantity=100,
            order_type="LIMIT",
            status="PENDING",
        )
        
        with patch('app.services.execution.TradeRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get.return_value = trade
            mock_repo.update.return_value = trade
            mock_repo_class.return_value = mock_repo
            
            result = await execution_service.cancel_order(session, trade_id=1)
            
            assert result.status == "CANCELLED"
            mock_repo.update.assert_called_once()
            session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_order(self, execution_service):
        """Test cancelling non-existent order raises error."""
        from app.core.errors import ResourceNotFoundError
        
        session = AsyncMock()
        
        with patch('app.services.execution.TradeRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get.return_value = None
            mock_repo_class.return_value = mock_repo
            
            with pytest.raises(ResourceNotFoundError):
                await execution_service.cancel_order(session, trade_id=999)


class TestTrailingStopLoss:
    """Test trailing stop loss functionality."""

    @pytest.fixture
    def risk_service_with_trailing(self):
        """Create risk service with trailing stop enabled."""
        constraints = RiskConstraints(
            use_trailing_stop=True,
            trailing_stop_pct=0.05,  # 5% trailing stop
            default_stop_loss_pct=0.10,  # 10% fixed stop
        )
        return RiskManagementService(constraints=constraints)

    @pytest.fixture
    def risk_service_without_trailing(self):
        """Create risk service with fixed stop only."""
        constraints = RiskConstraints(
            use_trailing_stop=False,
            default_stop_loss_pct=0.10,
        )
        return RiskManagementService(constraints=constraints)

    def test_fixed_stop_loss_triggered(self, risk_service_without_trailing):
        """Test that fixed stop loss triggers correctly."""
        position = Position(
            symbol="AAPL",
            quantity=100,
            average_cost=100.0,
            current_price=89.0,
            position_type="LONG",
        )
        
        # Price dropped 11%, should trigger 10% stop
        result = risk_service_without_trailing.check_stop_loss(position, 89.0)
        assert result is True

    def test_fixed_stop_loss_not_triggered(self, risk_service_without_trailing):
        """Test that stop loss doesn't trigger when within limits."""
        position = Position(
            symbol="AAPL",
            quantity=100,
            average_cost=100.0,
            current_price=95.0,
            position_type="LONG",
        )
        
        # Price dropped 5%, should not trigger 10% stop
        result = risk_service_without_trailing.check_stop_loss(position, 95.0)
        assert result is False

    def test_trailing_stop_triggers_after_profit(self, risk_service_with_trailing):
        """Test that trailing stop triggers after price drops from peak."""
        position = Position(
            symbol="AAPL",
            quantity=100,
            average_cost=100.0,
            current_price=110.0,  # Was up 10%
            position_type="LONG",
        )
        
        # Price now at 104 (up 4%), dropped 6% from peak
        # Should trigger 5% trailing stop
        result = risk_service_with_trailing.check_stop_loss(position, 104.0)
        assert result is True

    def test_trailing_stop_for_short_position(self, risk_service_with_trailing):
        """Test trailing stop for short positions."""
        position = Position(
            symbol="AAPL",
            quantity=-100,
            average_cost=100.0,
            current_price=90.0,  # Was down 10% (profit for short)
            position_type="SHORT",
        )
        
        # Price now at 96 (down 4%), rose 6% from lowest
        # Should trigger trailing stop
        result = risk_service_with_trailing.check_stop_loss(position, 96.0)
        assert result is True

    def test_absolute_stop_triggers_with_trailing(self, risk_service_with_trailing):
        """Test that absolute stop still works with trailing enabled."""
        position = Position(
            symbol="AAPL",
            quantity=100,
            average_cost=100.0,
            current_price=89.0,
            position_type="LONG",
        )
        
        # Price dropped 11%, should trigger 10% absolute stop
        result = risk_service_with_trailing.check_stop_loss(position, 89.0)
        assert result is True


class TestEventPublishingInCancellation:
    """Test event publishing during order cancellation."""

    @pytest.fixture
    def execution_service_with_events(self):
        """Create execution service with event manager."""
        broker = MagicMock()
        event_manager = MagicMock(spec=SessionEventManager)
        
        service = ExecutionService(broker=broker, event_manager=event_manager)
        return service

    @pytest.mark.asyncio
    async def test_cancellation_publishes_event(self, execution_service_with_events):
        """Test that order cancellation publishes an event."""
        session = AsyncMock()
        session_id = 123
        
        trade = Trade(
            id=1,
            portfolio_id=1,
            symbol="AAPL",
            action="BUY",
            quantity=100,
            order_type="LIMIT",
            status="PENDING",
        )
        
        with patch('app.services.execution.TradeRepository') as mock_repo_class:
            mock_repo = AsyncMock()
            mock_repo.get.return_value = trade
            mock_repo.update.return_value = trade
            mock_repo_class.return_value = mock_repo
            
            await execution_service_with_events.cancel_order(
                session, 
                trade_id=1, 
                session_id=session_id
            )
            
            # Verify event was published
            execution_service_with_events.event_manager.publish.assert_called()
            call_args = execution_service_with_events.event_manager.publish.call_args
            
            # Check that event contains cancellation info
            assert call_args[0][0] == str(session_id)
            event_data = call_args[0][1]
            assert event_data["event_type"] == "order_cancelled"
            assert event_data["order_data"]["symbol"] == "AAPL"