"""VendorConfig repository for database operations."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import VendorConfig
from .base import BaseRepository


class VendorConfigRepository(BaseRepository[VendorConfig]):
    """Repository for VendorConfig operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(VendorConfig, session)

    async def get_by_name(self, name: str) -> Optional[VendorConfig]:
        """Get a vendor config by name.

        Args:
            name: The config name

        Returns:
            The vendor config if found, None otherwise
        """
        statement = select(VendorConfig).where(VendorConfig.name == name)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_type(self, vendor_type: str) -> List[VendorConfig]:
        """Get vendor configs by type.

        Args:
            vendor_type: The vendor type

        Returns:
            List of vendor configs
        """
        statement = select(VendorConfig).where(
            VendorConfig.vendor_type == vendor_type,
            VendorConfig.is_active == True,
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get_active(self) -> List[VendorConfig]:
        """Get all active vendor configs.

        Returns:
            List of active vendor configs
        """
        statement = select(VendorConfig).where(VendorConfig.is_active == True)
        result = await self.session.execute(statement)
        return list(result.scalars().all())
