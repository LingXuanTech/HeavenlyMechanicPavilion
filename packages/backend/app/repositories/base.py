"""Base repository pattern for database operations."""

from __future__ import annotations

from typing import Any, Generic, List, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel

ModelType = TypeVar("ModelType", bound=SQLModel)


class BaseRepository(Generic[ModelType]):
    """Base repository providing common CRUD operations."""

    def __init__(self, model: Type[ModelType], session: AsyncSession):
        """Initialize the repository.

        Args:
            model: The SQLModel class for this repository
            session: The async database session
        """
        self.model = model
        self.session = session

    async def get(self, id: int) -> Optional[ModelType]:
        """Get a record by ID.

        Args:
            id: The record ID

        Returns:
            The record if found, None otherwise
        """
        return await self.session.get(self.model, id)

    async def get_multi(self, *, skip: int = 0, limit: int = 100) -> List[ModelType]:
        """Get multiple records with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of records
        """
        statement = select(self.model).offset(skip).limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def create(self, obj_in: ModelType) -> ModelType:
        """Create a new record.

        Args:
            obj_in: The object to create

        Returns:
            The created object with ID
        """
        self.session.add(obj_in)
        await self.session.commit()
        await self.session.refresh(obj_in)
        return obj_in

    async def update(self, *, db_obj: ModelType, obj_in: dict[str, Any]) -> ModelType:
        """Update an existing record.

        Args:
            db_obj: The existing database object
            obj_in: Dictionary of fields to update

        Returns:
            The updated object
        """
        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, *, id: int) -> bool:
        """Delete a record by ID.

        Args:
            id: The record ID

        Returns:
            True if deleted, False if not found
        """
        obj = await self.get(id)
        if obj:
            await self.session.delete(obj)
            await self.session.commit()
            return True
        return False
