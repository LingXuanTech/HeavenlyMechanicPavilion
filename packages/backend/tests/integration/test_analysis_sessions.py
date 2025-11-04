"""Integration tests for analysis session persistence."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.analysis_session import AnalysisSessionService
from app.services.events import SessionEventManager


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_analysis_session(
    async_client: AsyncClient,
    test_db: AsyncSession,
):
    """Test creating a persisted analysis session via POST /sessions."""
    response = await async_client.post(
        "/sessions",
        json={
            "ticker": "AAPL",
            "trade_date": "2024-01-15",
            "selected_analysts": ["market", "news"],
        },
    )
    
    assert response.status_code == 202
    data = response.json()
    assert "session_id" in data
    assert "stream_endpoint" in data
    
    session_id = data["session_id"]
    
    # Verify session was persisted in database
    result = await test_db.execute(
        "SELECT * FROM analysis_sessions WHERE id = :session_id",
        {"session_id": session_id}
    )
    row = result.fetchone()
    assert row is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_sessions_empty(async_client: AsyncClient):
    """Test listing sessions when none exist."""
    response = await async_client.get("/sessions")
    
    assert response.status_code == 200
    data = response.json()
    assert data["sessions"] == []
    assert data["total"] == 0
    assert data["skip"] == 0
    assert data["limit"] == 50


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_sessions_with_data(
    async_client: AsyncClient,
    test_db: AsyncSession,
):
    """Test listing sessions with existing data."""
    event_manager = SessionEventManager()
    service = AnalysisSessionService(test_db, event_manager)
    
    # Create a few sessions
    await service.create_session(
        session_id="session-1",
        ticker="AAPL",
        trade_date="2024-01-15",
        selected_analysts=["market"],
    )
    await service.create_session(
        session_id="session-2",
        ticker="MSFT",
        trade_date="2024-01-16",
        selected_analysts=["news"],
    )
    await test_db.commit()
    
    response = await async_client.get("/sessions")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["sessions"]) == 2
    assert data["total"] == 2
    
    # Verify field structure matches shared DTO
    session = data["sessions"][0]
    assert "id" in session
    assert "ticker" in session
    assert "asOfDate" in session
    assert "status" in session
    assert "createdAt" in session


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_sessions_with_pagination(
    async_client: AsyncClient,
    test_db: AsyncSession,
):
    """Test pagination of sessions list."""
    event_manager = SessionEventManager()
    service = AnalysisSessionService(test_db, event_manager)
    
    # Create multiple sessions
    for i in range(5):
        await service.create_session(
            session_id=f"session-{i}",
            ticker="AAPL",
            trade_date="2024-01-15",
        )
    await test_db.commit()
    
    # Test with limit
    response = await async_client.get("/sessions?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["sessions"]) == 2
    assert data["limit"] == 2
    
    # Test with skip
    response = await async_client.get("/sessions?skip=2&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["sessions"]) == 2
    assert data["skip"] == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_sessions_filter_by_status(
    async_client: AsyncClient,
    test_db: AsyncSession,
):
    """Test filtering sessions by status."""
    event_manager = SessionEventManager()
    service = AnalysisSessionService(test_db, event_manager)
    
    # Create sessions with different statuses
    await service.create_session(
        session_id="session-running",
        ticker="AAPL",
        trade_date="2024-01-15",
    )
    await service.create_session(
        session_id="session-completed",
        ticker="MSFT",
        trade_date="2024-01-16",
    )
    await service.update_status("session-completed", "completed")
    await test_db.commit()
    
    # Filter by running status
    response = await async_client.get("/sessions?status=running")
    assert response.status_code == 200
    data = response.json()
    assert len(data["sessions"]) == 1
    assert data["sessions"][0]["status"] == "running"
    
    # Filter by completed status
    response = await async_client.get("/sessions?status=completed")
    assert response.status_code == 200
    data = response.json()
    assert len(data["sessions"]) == 1
    assert data["sessions"][0]["status"] == "completed"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_sessions_filter_by_ticker(
    async_client: AsyncClient,
    test_db: AsyncSession,
):
    """Test filtering sessions by ticker."""
    event_manager = SessionEventManager()
    service = AnalysisSessionService(test_db, event_manager)
    
    await service.create_session(
        session_id="session-aapl",
        ticker="AAPL",
        trade_date="2024-01-15",
    )
    await service.create_session(
        session_id="session-msft",
        ticker="MSFT",
        trade_date="2024-01-16",
    )
    await test_db.commit()
    
    response = await async_client.get("/sessions?ticker=AAPL")
    assert response.status_code == 200
    data = response.json()
    assert len(data["sessions"]) == 1
    assert data["sessions"][0]["ticker"] == "AAPL"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_session_by_id(
    async_client: AsyncClient,
    test_db: AsyncSession,
):
    """Test retrieving a single session by ID."""
    event_manager = SessionEventManager()
    service = AnalysisSessionService(test_db, event_manager)
    
    session_id = "test-session-123"
    await service.create_session(
        session_id=session_id,
        ticker="AAPL",
        trade_date="2024-01-15",
        selected_analysts=["market", "news"],
    )
    await test_db.commit()
    
    response = await async_client.get(f"/sessions/{session_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert "session" in data
    assert "events" in data
    assert data["session"]["id"] == session_id
    assert data["session"]["ticker"] == "AAPL"
    assert data["session"]["asOfDate"] == "2024-01-15"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_session_not_found(async_client: AsyncClient):
    """Test retrieving a non-existent session returns 404."""
    response = await async_client.get("/sessions/nonexistent-id")
    
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_session_with_events(
    async_client: AsyncClient,
    test_db: AsyncSession,
):
    """Test retrieving a session includes buffered events."""
    event_manager = SessionEventManager()
    service = AnalysisSessionService(test_db, event_manager)
    
    session_id = "test-session-with-events"
    await event_manager.create_stream(session_id)
    
    await service.create_session(
        session_id=session_id,
        ticker="AAPL",
        trade_date="2024-01-15",
    )
    await test_db.commit()
    
    # Publish some events
    event_manager.publish(session_id, {"type": "status", "message": "started"})
    event_manager.publish(session_id, {"type": "result", "data": "test"})
    
    response = await async_client.get(f"/sessions/{session_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) == 2
    assert data["events"][0]["event"]["type"] == "status"
    assert data["events"][1]["event"]["type"] == "result"
