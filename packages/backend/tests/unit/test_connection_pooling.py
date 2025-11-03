"""Tests for database connection pooling configuration."""

import pytest

from app.db.session import DatabaseManager


def test_database_manager_default_pool_settings():
    """Test that DatabaseManager has correct default pool settings."""
    db_manager = DatabaseManager(
        database_url="postgresql+asyncpg://user:pass@localhost/test"
    )
    
    assert db_manager.pool_size == 5
    assert db_manager.max_overflow == 10
    assert db_manager.pool_timeout == 30.0
    assert db_manager.pool_recycle == 3600
    assert db_manager.pool_pre_ping is True
    assert db_manager.echo_pool is False


def test_database_manager_custom_pool_settings():
    """Test that DatabaseManager accepts custom pool settings."""
    db_manager = DatabaseManager(
        database_url="postgresql+asyncpg://user:pass@localhost/test",
        pool_size=20,
        max_overflow=40,
        pool_timeout=60.0,
        pool_recycle=1800,
        pool_pre_ping=False,
        echo_pool=True,
    )
    
    assert db_manager.pool_size == 20
    assert db_manager.max_overflow == 40
    assert db_manager.pool_timeout == 60.0
    assert db_manager.pool_recycle == 1800
    assert db_manager.pool_pre_ping is False
    assert db_manager.echo_pool is True


def test_database_manager_sqlite_no_pooling():
    """Test that SQLite doesn't use connection pooling."""
    db_manager = DatabaseManager(
        database_url="sqlite+aiosqlite:///./test.db",
        pool_size=10,
        max_overflow=20,
    )
    
    # SQLite engine is created without pool settings
    engine = db_manager.engine
    assert engine is not None
    # For SQLite, pool settings don't apply, but should not cause errors


def test_database_manager_query_logging_settings():
    """Test query logging configuration."""
    db_manager = DatabaseManager(
        database_url="postgresql+asyncpg://user:pass@localhost/test",
        enable_query_logging=True,
        slow_query_threshold=0.5,
    )
    
    assert db_manager.enable_query_logging is True
    assert db_manager.slow_query_threshold == 0.5


def test_database_manager_read_replica_settings():
    """Test read replica configuration."""
    db_manager = DatabaseManager(
        database_url="postgresql+asyncpg://user:pass@localhost/test",
        enable_read_replica=True,
        read_replica_url="postgresql+asyncpg://user:pass@replica/test",
    )
    
    assert db_manager.enable_read_replica is True
    assert db_manager.read_replica_url == "postgresql+asyncpg://user:pass@replica/test"


def test_database_manager_read_replica_disabled():
    """Test that read replica falls back to primary when disabled."""
    db_manager = DatabaseManager(
        database_url="postgresql+asyncpg://user:pass@localhost/test",
        enable_read_replica=False,
    )
    
    # Read engine should return primary engine when disabled
    assert db_manager.read_engine == db_manager.engine


def test_database_manager_read_replica_no_url():
    """Test that read replica falls back to primary when URL not provided."""
    db_manager = DatabaseManager(
        database_url="postgresql+asyncpg://user:pass@localhost/test",
        enable_read_replica=True,
        read_replica_url=None,
    )
    
    # Read engine should return primary engine when URL is None
    assert db_manager.read_engine == db_manager.engine


@pytest.mark.asyncio
async def test_session_factory_creation():
    """Test that session factory is created correctly."""
    db_manager = DatabaseManager(
        database_url="sqlite+aiosqlite:///:memory:"
    )
    
    session_factory = db_manager.session_factory
    assert session_factory is not None
    
    # Test creating a session
    async with session_factory() as session:
        assert session is not None


@pytest.mark.asyncio
async def test_read_session_factory_creation():
    """Test that read session factory is created correctly."""
    db_manager = DatabaseManager(
        database_url="sqlite+aiosqlite:///:memory:",
        enable_read_replica=False,  # Should fall back to primary
    )
    
    read_session_factory = db_manager.read_session_factory
    assert read_session_factory is not None
    
    # Should use same engine as primary when replica disabled
    assert db_manager.read_engine == db_manager.engine


@pytest.mark.asyncio
async def test_engine_cleanup():
    """Test that engines are properly disposed on close."""
    db_manager = DatabaseManager(
        database_url="sqlite+aiosqlite:///:memory:",
        enable_read_replica=True,
        read_replica_url="sqlite+aiosqlite:///:memory:",
    )
    
    # Access engines to create them
    _ = db_manager.engine
    _ = db_manager.read_engine
    
    assert db_manager._engine is not None
    assert db_manager._read_engine is not None
    
    # Close and verify cleanup
    await db_manager.close()
    
    assert db_manager._engine is None
    assert db_manager._session_factory is None
    assert db_manager._read_engine is None
    assert db_manager._read_session_factory is None


def test_pool_settings_validation():
    """Test that pool settings are stored correctly."""
    db_manager = DatabaseManager(
        database_url="postgresql+asyncpg://user:pass@localhost/test",
        pool_size=15,
        max_overflow=30,
        pool_timeout=45.0,
        pool_recycle=900,
    )
    
    # Verify all settings are stored
    assert db_manager.pool_size == 15
    assert db_manager.max_overflow == 30
    assert db_manager.pool_timeout == 45.0
    assert db_manager.pool_recycle == 900
    
    # Engine should be created with these settings (we don't test internal engine state,
    # just that manager stores the values correctly)
    assert db_manager.pool_size + db_manager.max_overflow == 45  # Total possible connections
