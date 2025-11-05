"""Health related API routes."""

from fastapi import APIRouter, Depends

from ..dependencies import get_graph_service
from ..schemas.health import FeatureChecklist, FeatureCheckStatus, HealthStatus
from ..services.feature_checks import run_feature_checks, summarize_feature_checks
from ..services.graph import TradingGraphService

router = APIRouter()


@router.get("/health", response_model=HealthStatus)
async def get_health(service: TradingGraphService = Depends(get_graph_service)) -> HealthStatus:
    return HealthStatus(**service.health())


@router.get("/health/features", response_model=FeatureChecklist)
async def get_feature_health() -> FeatureChecklist:
    """Return a checklist describing the status of recently shipped features."""

    results = run_feature_checks()
    summary = summarize_feature_checks(results)

    return FeatureChecklist(
        status=summary.status,
        passed=summary.passed,
        failed=summary.failed,
        total=summary.total,
        checks=[
            FeatureCheckStatus(
                name=result.name,
                description=result.description,
                passed=result.passed,
                detail=result.detail,
            )
            for result in results
        ],
    )
