"""Unit tests for analysis session service."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models.analysis_session import AnalysisSession
from app.services.analysis_session import AnalysisSessionService
from app.services.events import SessionEventManager


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_event_manager():
    """Mock event manager."""
    event_manager = MagicMock(spec=SessionEventManager)
    event_manager.get_recent_events.return_value = []
    return event_manager


@pytest.fixture
def analysis_service(mock_db_session, mock_event_manager):
    """Create analysis session service with mocks."""
    return AnalysisSessionService(mock_db_session, mock_event_manager)


@pytest.mark.asyncio
async def test_create_session(analysis_service, mock_db_session):
    """Test creating a new analysis session."""
    with patch.object(analysis_service.repository, 'create', new=AsyncMock()) as mock_create:
        mock_create.return_value = AnalysisSession(
            id="test-id",
            ticker="AAPL",
            trade_date="2024-01-15",
            status="running",
        )
        
        result = await analysis_service.create_session(
            session_id="test-id",
            ticker="AAPL",
            trade_date="2024-01-15",
            selected_analysts=["market", "news"],
        )
        
        assert result.id == "test-id"
        assert result.ticker == "AAPL"
        assert result.status == "running"
        
        # Verify repository.create was called
        mock_create.assert_called_once()
        call_args = mock_create.call_args[0][0]
        assert call_args.id == "test-id"
        assert call_args.ticker == "AAPL"
        assert call_args.selected_analysts_json == json.dumps(["market", "news"])


@pytest.mark.asyncio
async def test_create_session_without_analysts(analysis_service):
    """Test creating a session without selected analysts."""
    with patch.object(analysis_service.repository, 'create', new=AsyncMock()) as mock_create:
        mock_create.return_value = AnalysisSession(
            id="test-id",
            ticker="AAPL",
            trade_date="2024-01-15",
            status="running",
        )
        
        await analysis_service.create_session(
            session_id="test-id",
            ticker="AAPL",
            trade_date="2024-01-15",
        )
        
        call_args = mock_create.call_args[0][0]
        assert call_args.selected_analysts_json is None


@pytest.mark.asyncio
async def test_update_status(analysis_service):
    """Test updating session status."""
    existing_session = AnalysisSession(
        id="test-id",
        ticker="AAPL",
        trade_date="2024-01-15",
        status="running",
        created_at=datetime.utcnow(),
    )
    
    with patch.object(analysis_service.repository, 'get_by_id', new=AsyncMock()) as mock_get, \
         patch.object(analysis_service.repository, 'update', new=AsyncMock()) as mock_update:
        
        mock_get.return_value = existing_session
        mock_update.return_value = existing_session
        
        result = await analysis_service.update_status("test-id", "completed")
        
        assert result is not None
        mock_get.assert_called_once_with("test-id")
        mock_update.assert_called_once()
        
        # Verify update data
        update_call_args = mock_update.call_args[1]
        assert update_call_args["obj_in"]["status"] == "completed"
        assert "updated_at" in update_call_args["obj_in"]


@pytest.mark.asyncio
async def test_update_status_with_summary(analysis_service):
    """Test updating status with summary data."""
    existing_session = AnalysisSession(
        id="test-id",
        ticker="AAPL",
        trade_date="2024-01-15",
        status="running",
        created_at=datetime.utcnow(),
    )
    
    with patch.object(analysis_service.repository, 'get_by_id', new=AsyncMock()) as mock_get, \
         patch.object(analysis_service.repository, 'update', new=AsyncMock()) as mock_update:
        
        mock_get.return_value = existing_session
        mock_update.return_value = existing_session
        
        summary = {"decision": "buy", "confidence": 0.85}
        await analysis_service.update_status("test-id", "completed", summary)
        
        update_call_args = mock_update.call_args[1]
        assert update_call_args["obj_in"]["summary_json"] == json.dumps(summary)


@pytest.mark.asyncio
async def test_update_status_not_found(analysis_service):
    """Test updating status for non-existent session."""
    with patch.object(analysis_service.repository, 'get_by_id', new=AsyncMock()) as mock_get:
        mock_get.return_value = None
        
        result = await analysis_service.update_status("nonexistent", "completed")
        
        assert result is None


@pytest.mark.asyncio
async def test_get_session(analysis_service):
    """Test getting a session by ID."""
    expected_session = AnalysisSession(
        id="test-id",
        ticker="AAPL",
        trade_date="2024-01-15",
        status="running",
        created_at=datetime.utcnow(),
    )
    
    with patch.object(analysis_service.repository, 'get_by_id', new=AsyncMock()) as mock_get:
        mock_get.return_value = expected_session
        
        result = await analysis_service.get_session("test-id")
        
        assert result == expected_session
        mock_get.assert_called_once_with("test-id")


@pytest.mark.asyncio
async def test_list_sessions(analysis_service):
    """Test listing sessions."""
    expected_sessions = [
        AnalysisSession(
            id="session-1",
            ticker="AAPL",
            trade_date="2024-01-15",
            status="completed",
            created_at=datetime.utcnow(),
        ),
        AnalysisSession(
            id="session-2",
            ticker="MSFT",
            trade_date="2024-01-16",
            status="running",
            created_at=datetime.utcnow(),
        ),
    ]
    
    with patch.object(analysis_service.repository, 'get_recent', new=AsyncMock()) as mock_get:
        mock_get.return_value = expected_sessions
        
        result = await analysis_service.list_sessions(skip=0, limit=10)
        
        assert result == expected_sessions
        mock_get.assert_called_once_with(skip=0, limit=10, status=None)


@pytest.mark.asyncio
async def test_list_sessions_with_status_filter(analysis_service):
    """Test listing sessions with status filter."""
    with patch.object(analysis_service.repository, 'get_recent', new=AsyncMock()) as mock_get:
        mock_get.return_value = []
        
        await analysis_service.list_sessions(status="completed")
        
        mock_get.assert_called_once_with(skip=0, limit=50, status="completed")


@pytest.mark.asyncio
async def test_list_sessions_with_ticker_filter(analysis_service):
    """Test listing sessions with ticker filter."""
    with patch.object(analysis_service.repository, 'get_by_ticker', new=AsyncMock()) as mock_get:
        mock_get.return_value = []
        
        await analysis_service.list_sessions(ticker="AAPL")
        
        mock_get.assert_called_once_with("AAPL", skip=0, limit=50)


def test_get_session_events(analysis_service, mock_event_manager):
    """Test getting session events from event manager."""
    expected_events = [
        {"timestamp": "2024-01-15T10:00:00", "event": {"type": "status"}},
        {"timestamp": "2024-01-15T10:01:00", "event": {"type": "result"}},
    ]
    mock_event_manager.get_recent_events.return_value = expected_events
    
    result = analysis_service.get_session_events("test-session")
    
    assert result == expected_events
    mock_event_manager.get_recent_events.assert_called_once_with("test-session")
