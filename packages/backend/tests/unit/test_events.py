"""Unit tests for SessionEventManager and event buffering."""

import asyncio
from datetime import datetime

import pytest

from app.services.events import SessionEventManager


@pytest.mark.asyncio
async def test_create_stream_initializes_buffer():
    """Test that create_stream initializes both queue and event buffer."""
    manager = SessionEventManager()
    session_id = "test-session-1"
    
    queue = await manager.create_stream(session_id)
    
    assert queue is not None
    assert isinstance(queue, asyncio.Queue)
    recent_events = manager.get_recent_events(session_id)
    assert recent_events == []


@pytest.mark.asyncio
async def test_publish_stores_event_in_buffer():
    """Test that publish adds events to the buffer with timestamps."""
    manager = SessionEventManager()
    session_id = "test-session-1"
    
    await manager.create_stream(session_id)
    
    event1 = {"type": "status", "message": "started"}
    event2 = {"type": "result", "data": "test"}
    
    result1 = manager.publish(session_id, event1)
    result2 = manager.publish(session_id, event2)
    
    assert result1 is True
    assert result2 is True
    
    recent_events = manager.get_recent_events(session_id)
    assert len(recent_events) == 2
    assert recent_events[0]["event"] == event1
    assert recent_events[1]["event"] == event2


@pytest.mark.asyncio
async def test_publish_includes_timestamps():
    """Test that published events include ISO format timestamps."""
    manager = SessionEventManager()
    session_id = "test-session-1"
    
    await manager.create_stream(session_id)
    
    before = datetime.now()
    manager.publish(session_id, {"type": "test"})
    after = datetime.now()
    
    recent_events = manager.get_recent_events(session_id)
    assert len(recent_events) == 1
    
    timestamp_str = recent_events[0]["timestamp"]
    timestamp = datetime.fromisoformat(timestamp_str)
    
    assert before <= timestamp <= after


@pytest.mark.asyncio
async def test_buffer_respects_max_size():
    """Test that buffer truncates old events when exceeding max size."""
    max_size = 5
    manager = SessionEventManager(max_buffer_size=max_size)
    session_id = "test-session-1"
    
    await manager.create_stream(session_id)
    
    for i in range(max_size + 10):
        manager.publish(session_id, {"type": "event", "index": i})
    
    recent_events = manager.get_recent_events(session_id)
    assert len(recent_events) == max_size
    
    indices = [event["event"]["index"] for event in recent_events]
    assert indices == list(range(10, 15))


@pytest.mark.asyncio
async def test_get_recent_events_returns_empty_for_unknown_session():
    """Test that get_recent_events returns empty list for unknown sessions."""
    manager = SessionEventManager()
    
    recent_events = manager.get_recent_events("unknown-session")
    assert recent_events == []


@pytest.mark.asyncio
async def test_get_recent_events_after_close():
    """Test that get_recent_events returns buffer after stream is closed."""
    manager = SessionEventManager()
    session_id = "test-session-1"
    
    await manager.create_stream(session_id)
    
    event1 = {"type": "status", "message": "started"}
    event2 = {"type": "result", "data": "final"}
    
    manager.publish(session_id, event1)
    manager.publish(session_id, event2)
    
    manager.close(session_id)
    
    recent_events = manager.get_recent_events(session_id)
    assert len(recent_events) == 2
    assert recent_events[0]["event"] == event1
    assert recent_events[1]["event"] == event2


@pytest.mark.asyncio
async def test_publish_returns_false_for_unknown_session():
    """Test that publish returns False if session doesn't exist."""
    manager = SessionEventManager()
    
    result = manager.publish("unknown-session", {"type": "test"})
    assert result is False


@pytest.mark.asyncio
async def test_multiple_sessions_independent_buffers():
    """Test that different sessions have independent event buffers."""
    manager = SessionEventManager()
    session1 = "session-1"
    session2 = "session-2"
    
    await manager.create_stream(session1)
    await manager.create_stream(session2)
    
    manager.publish(session1, {"type": "event", "session": 1})
    manager.publish(session2, {"type": "event", "session": 2})
    manager.publish(session1, {"type": "event", "session": 1, "seq": 2})
    
    events1 = manager.get_recent_events(session1)
    events2 = manager.get_recent_events(session2)
    
    assert len(events1) == 2
    assert len(events2) == 1
    assert events1[0]["event"]["session"] == 1
    assert events1[1]["event"]["seq"] == 2
    assert events2[0]["event"]["session"] == 2


@pytest.mark.asyncio
async def test_event_ordering_preserved():
    """Test that events are returned in the order they were published."""
    manager = SessionEventManager()
    session_id = "test-session-1"
    
    await manager.create_stream(session_id)
    
    events_to_publish = [
        {"type": "event", "seq": i}
        for i in range(10)
    ]
    
    for event in events_to_publish:
        manager.publish(session_id, event)
    
    recent_events = manager.get_recent_events(session_id)
    
    for idx, stored in enumerate(recent_events):
        assert stored["event"]["seq"] == idx


@pytest.mark.asyncio
async def test_custom_buffer_size():
    """Test creating manager with custom buffer size."""
    custom_size = 10
    manager = SessionEventManager(max_buffer_size=custom_size)
    session_id = "test-session-1"
    
    await manager.create_stream(session_id)
    
    for i in range(custom_size + 5):
        manager.publish(session_id, {"index": i})
    
    recent_events = manager.get_recent_events(session_id)
    assert len(recent_events) == custom_size


@pytest.mark.asyncio
async def test_buffer_with_various_event_types():
    """Test that buffer handles various event payload types."""
    manager = SessionEventManager()
    session_id = "test-session-1"
    
    await manager.create_stream(session_id)
    
    events = [
        {"type": "string", "msg": "hello"},
        {"type": "dict", "data": {"nested": "value"}},
        {"type": "list", "items": [1, 2, 3]},
        {"type": "mixed", "value": None},
    ]
    
    for event in events:
        manager.publish(session_id, event)
    
    recent_events = manager.get_recent_events(session_id)
    assert len(recent_events) == 4
    
    for idx, stored in enumerate(recent_events):
        assert stored["event"] == events[idx]


@pytest.mark.asyncio
async def test_thread_safety_concurrent_publishes():
    """Test thread-safety with concurrent event publishes."""
    manager = SessionEventManager()
    session_id = "test-session-1"
    
    await manager.create_stream(session_id)
    
    async def publish_events(start_idx, count):
        for i in range(start_idx, start_idx + count):
            manager.publish(session_id, {"type": "event", "index": i})
    
    await asyncio.gather(
        publish_events(0, 5),
        publish_events(5, 5),
        publish_events(10, 5),
    )
    
    recent_events = manager.get_recent_events(session_id)
    assert len(recent_events) == 15
    
    indices = [event["event"]["index"] for event in recent_events]
    assert len(set(indices)) == 15


@pytest.mark.asyncio
async def test_close_does_not_remove_buffer():
    """Test that close removes stream but preserves buffer."""
    manager = SessionEventManager()
    session_id = "test-session-1"
    
    await manager.create_stream(session_id)
    manager.publish(session_id, {"type": "event1"})
    manager.publish(session_id, {"type": "event2"})
    
    manager.close(session_id)
    
    recent_events = manager.get_recent_events(session_id)
    assert len(recent_events) == 2


@pytest.mark.asyncio
async def test_get_stream_raises_for_closed_session():
    """Test that get_stream raises KeyError after close."""
    manager = SessionEventManager()
    session_id = "test-session-1"
    
    queue = await manager.create_stream(session_id)
    assert queue is not None
    
    manager.close(session_id)
    
    with pytest.raises(KeyError):
        await manager.get_stream(session_id)


@pytest.mark.asyncio
async def test_default_buffer_size_is_100():
    """Test that default buffer size is 100."""
    manager = SessionEventManager()
    session_id = "test-session-1"
    
    await manager.create_stream(session_id)
    
    for i in range(150):
        manager.publish(session_id, {"index": i})
    
    recent_events = manager.get_recent_events(session_id)
    assert len(recent_events) == 100
    
    indices = [event["event"]["index"] for event in recent_events]
    assert indices[0] == 50
    assert indices[-1] == 149
