"""Repositories for backtesting persistence models."""

from __future__ import annotations

from typing import Iterable, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import (
    BacktestArtifact,
    BacktestEquityCurvePoint,
    BacktestMetrics,
    BacktestRun,
)
from .base import BaseRepository


class BacktestRunRepository(BaseRepository[BacktestRun]):
    """Repository for :class:`BacktestRun`."""

    def __init__(self, session: AsyncSession):
        super().__init__(BacktestRun, session)

    async def get_by_run_id(self, run_id: str) -> Optional[BacktestRun]:
        statement = select(BacktestRun).where(BacktestRun.run_id == run_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_recent(self, *, skip: int = 0, limit: int = 100) -> List[BacktestRun]:
        statement = (
            select(BacktestRun).order_by(BacktestRun.created_at.desc()).offset(skip).limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def list_by_status(
        self,
        *,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[BacktestRun]:
        statement = (
            select(BacktestRun)
            .where(BacktestRun.status == status)
            .order_by(BacktestRun.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())


class BacktestMetricsRepository(BaseRepository[BacktestMetrics]):
    """Repository for :class:`BacktestMetrics`."""

    def __init__(self, session: AsyncSession):
        super().__init__(BacktestMetrics, session)

    async def get_by_run_id(self, run_id: int) -> Optional[BacktestMetrics]:
        statement = select(BacktestMetrics).where(BacktestMetrics.run_id == run_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def delete_for_run(self, run_id: int) -> None:
        await self.session.execute(delete(BacktestMetrics).where(BacktestMetrics.run_id == run_id))
        await self.session.commit()


class BacktestEquityCurveRepository(BaseRepository[BacktestEquityCurvePoint]):
    """Repository for equity curve points."""

    def __init__(self, session: AsyncSession):
        super().__init__(BacktestEquityCurvePoint, session)

    async def get_points(self, run_id: int) -> List[BacktestEquityCurvePoint]:
        statement = (
            select(BacktestEquityCurvePoint)
            .where(BacktestEquityCurvePoint.run_id == run_id)
            .order_by(BacktestEquityCurvePoint.timestamp.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def delete_for_run(self, run_id: int) -> None:
        await self.session.execute(
            delete(BacktestEquityCurvePoint).where(BacktestEquityCurvePoint.run_id == run_id)
        )
        await self.session.commit()

    async def create_many(self, points: Iterable[BacktestEquityCurvePoint]) -> None:
        self.session.add_all(list(points))
        await self.session.commit()


class BacktestArtifactRepository(BaseRepository[BacktestArtifact]):
    """Repository for stored artifacts such as logs and summaries."""

    def __init__(self, session: AsyncSession):
        super().__init__(BacktestArtifact, session)

    async def get_by_type(self, run_id: int, artifact_type: str) -> Optional[BacktestArtifact]:
        statement = select(BacktestArtifact).where(
            BacktestArtifact.run_id == run_id,
            BacktestArtifact.artifact_type == artifact_type,
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_for_run(self, run_id: int) -> List[BacktestArtifact]:
        statement = (
            select(BacktestArtifact)
            .where(BacktestArtifact.run_id == run_id)
            .order_by(BacktestArtifact.created_at.asc())
        )
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def delete_for_run(self, run_id: int) -> None:
        await self.session.execute(
            delete(BacktestArtifact).where(BacktestArtifact.run_id == run_id)
        )
        await self.session.commit()

    async def create_many(self, artifacts: Iterable[BacktestArtifact]) -> None:
        self.session.add_all(list(artifacts))
        await self.session.commit()
