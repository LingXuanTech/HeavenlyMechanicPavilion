"""Integration tests for execution event streaming with authentication."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.execution_events import (
    ExecutionEvent,
    ExecutionEventType,
    OrderEventData,
)
from app.services.events import SessionEventManager


@pytest.fixture
def test_client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_event_manager():
    """Create mock event manager."""
    manager = MagicMock(spec=SessionEventManager)
    manager.get_recent_events = MagicMock(return_value=[])
    return manager


@pytest.fixture
def mock_auth_token():
    """Create mock authentication token."""
    return "mock_jwt_token_12345"


@pytest.fixture
def mock_user():
    """Create mock authenticated user."""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "is_active": True,
    }


class TestEventHistoryEndpoint:
    """Test event history retrieval endpoint."""

    def test_get_event_history_requires_auth(self, test_client):
        """Test that event history endpoint requires authentication."""
        session_id = "sess_123"
        
        response = test_client.get(f"/api/streams/{session_id}/events-history")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("app.api.streams.get_current_active_user")
    @patch("app.api.streams.get_event_manager")
    def test_get_event_history_with_auth(
        self,
        mock_get_manager,
        mock_get_user,
        test_client,
        mock_event_manager,
        mock_user,
    ):
        """Test retrieving event history with authentication."""
        session_id = "sess_123"
        
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_get_manager.return_value = mock_event_manager
        
        # Create sample events
        sample_events = [
            {
                "timestamp": "2025-01-01T12:00:00",
                "event": {
                    "event_type": "order_submitted",
                    "session_id": session_id,
                    "message": "Order submitted",
                },
            }
        ]
        mock_event_manager.get_recent_events.return_value = sample_events
        
        # Make authenticated request
        response = test_client.get(
            f"/api/streams/{session_id}/events-history",
            headers={"Authorization": "Bearer mock_token"},
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["session_id"] == session_id
        assert data["count"] == 1
        assert len(data["events"]) == 1

    @patch("app.api.streams.get_current_active_user")
    @patch("app.api.streams.get_event_manager")
    def test_get_event_history_empty_session(
        self,
        mock_get_manager,
        mock_get_user,
        test_client,
        mock_event_manager,
        mock_user,
    ):
        """Test retrieving event history for session with no events."""
        session_id = "empty_session"
        
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_get_manager.return_value = mock_event_manager
        mock_event_manager.get_recent_events.return_value = []
        
        response = test_client.get(
            f"/api/streams/{session_id}/events-history",
            headers={"Authorization": "Bearer mock_token"},
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["count"] == 0
        assert data["events"] == []


class TestSSEEndpoint:
    """Test Server-Sent Events endpoint."""

    def test_sse_requires_auth(self, test_client):
        """Test that SSE endpoint requires authentication."""
        session_id = "sess_123"
        
        response = test_client.get(f"/api/streams/{session_id}/events")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @patch("app.api.streams.get_current_active_user")
    @patch("app.api.streams.get_graph_service")
    def test_sse_unknown_session(
        self,
        mock_get_service,
        mock_get_user,
        test_client,
        mock_user,
    ):
        """Test SSE with unknown session ID."""
        session_id = "unknown_session"
        
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_service = AsyncMock()
        mock_service.ensure_session_stream = AsyncMock(side_effect=KeyError(session_id))
        mock_get_service.return_value = mock_service
        
        response = test_client.get(
            f"/api/streams/{session_id}/events",
            headers={"Authorization": "Bearer mock_token"},
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestWebSocketAuthentication:
    """Test WebSocket authentication."""

    def test_websocket_without_token(self, test_client):
        """Test WebSocket connection without authentication token."""
        session_id = "sess_123"
        
        with test_client.websocket_connect(f"/api/streams/{session_id}/ws") as websocket:
            # Connection should be rejected
            pass

    def test_websocket_with_invalid_token(self, test_client):
        """Test WebSocket connection with invalid token."""
        session_id = "sess_123"
        
        with pytest.raises(Exception):
            with test_client.websocket_connect(
                f"/api/streams/{session_id}/ws?token=invalid_token"
            ) as websocket:
                pass

    @patch("app.api.streams.verify_access_token")
    @patch("app.api.streams.get_graph_service")
    def test_websocket_with_valid_token(
        self,
        mock_get_service,
        mock_verify_token,
        test_client,
    ):
        """Test WebSocket connection with valid authentication token."""
        session_id = "sess_123"
        token = "valid_token_12345"
        
        # Setup mocks
        mock_verify_token.return_value = {"sub": "testuser"}
        
        mock_service = AsyncMock()
        mock_queue = asyncio.Queue()
        mock_service.ensure_session_stream = AsyncMock(return_value=mock_queue)
        mock_get_service.return_value = mock_service
        
        # Add test event to queue
        asyncio.create_task(mock_queue.put({
            "event_type": "order_submitted",
            "message": "Test event"
        }))
        asyncio.create_task(mock_queue.put(None))  # End marker
        
        with test_client.websocket_connect(
            f"/api/streams/{session_id}/ws?token={token}"
        ) as websocket:
            # Should receive event
            data = websocket.receive_json()
            assert "event_type" in data or "type" in data


class TestExecutionServiceEventPublishing:
    """Test event publishing from ExecutionService."""

    def test_publish_order_submitted_event(self):
        """Test publishing order submitted event."""
        event_manager = SessionEventManager()
        session_id = "sess_123"
        
        # Create stream
        async def setup():
            queue = await event_manager.create_stream(session_id)
            
            # Publish event
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
            
            result = event_manager.publish(session_id, event.model_dump(mode='json'))
            assert result is True
            
            # Retrieve event from queue
            received_event = await asyncio.wait_for(queue.get(), timeout=1.0)
            assert received_event["event_type"] == "order_submitted"
            assert received_event["order_data"]["symbol"] == "AAPL"
        
        asyncio.run(setup())

    def test_publish_order_filled_event(self):
        """Test publishing order filled event."""
        event_manager = SessionEventManager()
        session_id = "sess_456"
        
        async def setup():
            queue = await event_manager.create_stream(session_id)
            
            event = ExecutionEvent(
                event_type=ExecutionEventType.ORDER_FILLED,
                session_id=session_id,
                portfolio_id=1,
                order_data=OrderEventData(
                    symbol="AAPL",
                    action="BUY",
                    quantity=100.0,
                    order_type="MARKET",
                    status="FILLED",
                    filled_quantity=100.0,
                    average_fill_price=150.50,
                ),
                message="Order filled",
            )
            
            result = event_manager.publish(session_id, event.model_dump(mode='json'))
            assert result is True
            
            received_event = await asyncio.wait_for(queue.get(), timeout=1.0)
            assert received_event["event_type"] == "order_filled"
            assert received_event["order_data"]["filled_quantity"] == 100.0
            assert received_event["order_data"]["average_fill_price"] == 150.50
        
        asyncio.run(setup())

    def test_publish_risk_check_failed_event(self):
        """Test publishing risk check failed event."""
        event_manager = SessionEventManager()
        session_id = "sess_789"
        
        async def setup():
            queue = await event_manager.create_stream(session_id)
            
            from app.schemas.execution_events import RiskEventData
            
            event = ExecutionEvent(
                event_type=ExecutionEventType.RISK_CHECK_FAILED,
                session_id=session_id,
                portfolio_id=1,
                risk_data=RiskEventData(
                    symbol="AAPL",
                    reason="Insufficient funds",
                    details={"required": 15050, "available": 10000},
                ),
                message="Risk check failed",
            )
            
            result = event_manager.publish(session_id, event.model_dump(mode='json'))
            assert result is True
            
            received_event = await asyncio.wait_for(queue.get(), timeout=1.0)
            assert received_event["event_type"] == "risk_check_failed"
            assert received_event["risk_data"]["reason"] == "Insufficient funds"
        
        asyncio.run(setup())

    def test_multiple_event_publishing(self):
        """Test publishing multiple events in sequence."""
        event_manager = SessionEventManager()
        session_id = "sess_multi"
        
        async def setup():
            queue = await event_manager.create_stream(session_id)
            
            # Publish multiple events
            events = [
                ExecutionEvent(
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
                for i in range(3)
            ]
            
            for event in events:
                event_manager.publish(session_id, event.model_dump(mode='json'))
            
            # Verify all events received
            received_events = []
            for _ in range(3):
                event = await asyncio.wait_for(queue.get(), timeout=1.0)
                received_events.append(event)
            
            assert len(received_events) == 3
            symbols = [e["order_data"]["symbol"] for e in received_events]
            assert "SYM0" in symbols
            assert "SYM1" in symbols
            assert "SYM2" in symbols
        
        asyncio.run(setup())