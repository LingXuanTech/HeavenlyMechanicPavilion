"""Database session management with async support."""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel


class DatabaseManager:
    """Manages database connections and session lifecycle."""

    def __init__(self, database_url: str, echo: bool = False):
        """Initialize the database manager.

        Args:
            database_url: Database connection URL (e.g., postgresql+asyncpg://...)
            echo: Whether to echo SQL statements for debugging
        """
        self.database_url = database_url
        self.echo = echo
        self._engine: AsyncEngine | None = None
        self._session_factory: sessionmaker | None = None

    @property
    def engine(self) -> AsyncEngine:
        """Get or create the async database engine."""
        if self._engine is None:
            self._engine = create_async_engine(
                self.database_url,
                echo=self.echo,
                future=True,
            )
        return self._engine

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

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session.

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


# Global database manager instance
_db_manager: DatabaseManager | None = None


def init_db(database_url: str, echo: bool = False) -> DatabaseManager:
    """Initialize the global database manager.

    Args:
        database_url: Database connection URL
        echo: Whether to echo SQL statements

    Returns:
        DatabaseManager: The initialized database manager
    """
    global _db_manager
    _db_manager = DatabaseManager(database_url, echo)
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
