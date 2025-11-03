"""Database session management with async support."""

from __future__ import annotations

import logging
import time
from typing import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and session lifecycle."""

    def __init__(
        self,
        database_url: str,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
        pool_timeout: float = 30.0,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
        echo_pool: bool = False,
        enable_query_logging: bool = False,
        slow_query_threshold: float = 1.0,
        enable_read_replica: bool = False,
        read_replica_url: str | None = None,
    ):
        """Initialize the database manager.

        Args:
            database_url: Database connection URL (e.g., postgresql+asyncpg://...)
            echo: Whether to echo SQL statements for debugging
            pool_size: Number of connections to maintain in the pool
            max_overflow: Maximum number of connections that can be created beyond pool_size
            pool_timeout: Seconds to wait before giving up on getting a connection from the pool
            pool_recycle: Seconds after which a connection is automatically recycled
            pool_pre_ping: Enable connection health checks before use
            echo_pool: Whether to echo pool connection/checkout activity
            enable_query_logging: Enable query performance logging
            slow_query_threshold: Threshold in seconds for logging slow queries
            enable_read_replica: Enable read replica support
            read_replica_url: Read replica database connection URL
        """
        self.database_url = database_url
        self.echo = echo
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_timeout = pool_timeout
        self.pool_recycle = pool_recycle
        self.pool_pre_ping = pool_pre_ping
        self.echo_pool = echo_pool
        self.enable_query_logging = enable_query_logging
        self.slow_query_threshold = slow_query_threshold
        self.enable_read_replica = enable_read_replica
        self.read_replica_url = read_replica_url
        self._engine: AsyncEngine | None = None
        self._read_engine: AsyncEngine | None = None
        self._session_factory: sessionmaker | None = None
        self._read_session_factory: sessionmaker | None = None

    @property
    def engine(self) -> AsyncEngine:
        """Get or create the async database engine with connection pooling."""
        if self._engine is None:
            # SQLite doesn't support connection pooling the same way
            if "sqlite" in self.database_url:
                self._engine = create_async_engine(
                    self.database_url,
                    echo=self.echo,
                    future=True,
                )
            else:
                # PostgreSQL and other databases with proper connection pooling
                self._engine = create_async_engine(
                    self.database_url,
                    echo=self.echo,
                    future=True,
                    pool_size=self.pool_size,
                    max_overflow=self.max_overflow,
                    pool_timeout=self.pool_timeout,
                    pool_recycle=self.pool_recycle,
                    pool_pre_ping=self.pool_pre_ping,
                    echo_pool=self.echo_pool,
                )
            
            # Setup query performance monitoring if enabled
            if self.enable_query_logging:
                self._setup_query_logging()
        
        return self._engine
    
    def _setup_query_logging(self) -> None:
        """Setup query performance monitoring event listeners."""
        if self._engine is None:
            return
        
        # Get the sync engine for event registration
        sync_engine = self._engine.sync_engine
        
        @event.listens_for(sync_engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Record query start time."""
            conn.info.setdefault("query_start_time", []).append(time.time())
        
        @event.listens_for(sync_engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Log query execution time."""
            total_time = time.time() - conn.info["query_start_time"].pop()
            
            # Log slow queries
            if total_time >= self.slow_query_threshold:
                logger.warning(
                    f"Slow query detected (took {total_time:.2f}s): {statement[:200]}",
                    extra={
                        "query_time": total_time,
                        "query": statement,
                        "parameters": parameters,
                    },
                )
            elif self.echo:
                logger.debug(
                    f"Query executed in {total_time:.4f}s",
                    extra={"query_time": total_time, "query": statement},
                )

    @property
    def session_factory(self) -> sessionmaker:
        """Get or create the session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return self._session_factory
    
    @property
    def read_engine(self) -> AsyncEngine:
        """Get or create the read replica async database engine.
        
        If read replica is not enabled or configured, falls back to primary engine.
        """
        if not self.enable_read_replica or not self.read_replica_url:
            return self.engine
        
        if self._read_engine is None:
            # Create read replica engine with same configuration
            if "sqlite" in self.read_replica_url:
                self._read_engine = create_async_engine(
                    self.read_replica_url,
                    echo=self.echo,
                    future=True,
                )
            else:
                self._read_engine = create_async_engine(
                    self.read_replica_url,
                    echo=self.echo,
                    future=True,
                    pool_size=self.pool_size,
                    max_overflow=self.max_overflow,
                    pool_timeout=self.pool_timeout,
                    pool_recycle=self.pool_recycle,
                    pool_pre_ping=self.pool_pre_ping,
                    echo_pool=self.echo_pool,
                )
            
            # Setup query logging for read engine if enabled
            if self.enable_query_logging:
                self._setup_query_logging_for_engine(self._read_engine)
        
        return self._read_engine
    
    @property
    def read_session_factory(self) -> sessionmaker:
        """Get or create the read replica session factory."""
        if self._read_session_factory is None:
            self._read_session_factory = sessionmaker(
                self.read_engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
        return self._read_session_factory
    
    def _setup_query_logging_for_engine(self, engine: AsyncEngine) -> None:
        """Setup query performance monitoring for a specific engine.
        
        Args:
            engine: The engine to setup logging for
        """
        sync_engine = engine.sync_engine
        
        @event.listens_for(sync_engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Record query start time."""
            conn.info.setdefault("query_start_time", []).append(time.time())
        
        @event.listens_for(sync_engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            """Log query execution time."""
            total_time = time.time() - conn.info["query_start_time"].pop()
            
            # Log slow queries
            if total_time >= self.slow_query_threshold:
                logger.warning(
                    f"Slow query detected (took {total_time:.2f}s): {statement[:200]}",
                    extra={
                        "query_time": total_time,
                        "query": statement,
                        "parameters": parameters,
                    },
                )
            elif self.echo:
                logger.debug(
                    f"Query executed in {total_time:.4f}s",
                    extra={"query_time": total_time, "query": statement},
                )

    async def create_tables(self) -> None:
        """Create all tables in the database."""
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

    async def drop_tables(self) -> None:
        """Drop all tables in the database."""
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.drop_all)

    async def close(self) -> None:
        """Close the database engine and all connections."""
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None
        
        if self._read_engine is not None:
            await self._read_engine.dispose()
            self._read_engine = None
            self._read_session_factory = None

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session for write operations.

        Yields:
            AsyncSession: A database session
        """
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def get_read_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session for read operations (uses read replica if configured).

        Yields:
            AsyncSession: A database session connected to read replica or primary
        """
        async with self.read_session_factory() as session:
            try:
                yield session
                # Read sessions typically don't need commits, but we'll keep it for consistency
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


# Global database manager instance
_db_manager: DatabaseManager | None = None


def init_db(
    database_url: str,
    echo: bool = False,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_timeout: float = 30.0,
    pool_recycle: int = 3600,
    pool_pre_ping: bool = True,
    echo_pool: bool = False,
    enable_query_logging: bool = False,
    slow_query_threshold: float = 1.0,
    enable_read_replica: bool = False,
    read_replica_url: str | None = None,
) -> DatabaseManager:
    """Initialize the global database manager.

    Args:
        database_url: Database connection URL
        echo: Whether to echo SQL statements
        pool_size: Number of connections to maintain in the pool
        max_overflow: Maximum number of connections that can be created beyond pool_size
        pool_timeout: Seconds to wait before giving up on getting a connection from the pool
        pool_recycle: Seconds after which a connection is automatically recycled
        pool_pre_ping: Enable connection health checks before use
        echo_pool: Whether to echo pool connection/checkout activity
        enable_query_logging: Enable query performance logging
        slow_query_threshold: Threshold in seconds for logging slow queries
        enable_read_replica: Enable read replica support
        read_replica_url: Read replica database connection URL

    Returns:
        DatabaseManager: The initialized database manager
    """
    global _db_manager
    _db_manager = DatabaseManager(
        database_url=database_url,
        echo=echo,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_timeout=pool_timeout,
        pool_recycle=pool_recycle,
        pool_pre_ping=pool_pre_ping,
        echo_pool=echo_pool,
        enable_query_logging=enable_query_logging,
        slow_query_threshold=slow_query_threshold,
        enable_read_replica=enable_read_replica,
        read_replica_url=read_replica_url,
    )
    return _db_manager


def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance.

    Returns:
        DatabaseManager: The database manager

    Raises:
        RuntimeError: If the database manager has not been initialized
    """
    if _db_manager is None:
        raise RuntimeError("Database manager not initialized. Call init_db() first.")
    return _db_manager


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get a database session in FastAPI.

    Yields:
        AsyncSession: A database session
    """
    db_manager = get_db_manager()
    async for session in db_manager.get_session():
        yield session
