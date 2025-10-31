"""Backtesting API endpoints."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories import BacktestRunRepository
from ..schemas.backtest import (
    BacktestArtifactResponse,
    BacktestComparisonEntry,
    BacktestComparisonResponse,
    BacktestComparisonSummary,
    BacktestDecisionLogEntry,
    BacktestEquityPointResponse,
    BacktestExportResponse,
    BacktestMetricsResponse,
    BacktestRunDetailResponse,
    BacktestRunResponse,
    BacktestTradeLogEntry,
    StartBacktestRequest,
)
from ..services import BacktestService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backtests", tags=["backtests"])


def _split_symbols(symbols: str) -> List[str]:
    return [sym.strip() for sym in symbols.split(",") if sym.strip()]


def _run_to_response(run) -> BacktestRunResponse:
    return BacktestRunResponse(
        id=run.id,
        run_id=run.run_id,
        name=run.name,
        description=run.description,
        symbols=_split_symbols(run.symbols) if run.symbols else [],
        start_date=run.start_date,
        end_date=run.end_date,
        initial_capital=run.initial_capital,
        position_size=run.position_size,
        risk_free_rate=run.risk_free_rate,
        status=run.status,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
        duration_seconds=run.duration_seconds,
        result_summary=run.result_summary,
        error_message=run.error_message,
    )


def _metrics_to_response(metrics) -> Optional[BacktestMetricsResponse]:
    if metrics is None:
        return None
    return BacktestMetricsResponse(
        total_return=metrics.total_return,
        annualized_return=metrics.annualized_return,
        sharpe_ratio=metrics.sharpe_ratio,
        sortino_ratio=metrics.sortino_ratio,
        volatility=metrics.volatility,
        max_drawdown=metrics.max_drawdown,
        max_drawdown_duration=metrics.max_drawdown_duration,
        win_rate=metrics.win_rate,
        best_trade_return=metrics.best_trade_return,
        worst_trade_return=metrics.worst_trade_return,
        trades_executed=metrics.trades_executed,
        holding_period_days=metrics.holding_period_days,
        metadata_json=metrics.metadata_json,
    )


def _equity_point_to_response(point) -> BacktestEquityPointResponse:
    return BacktestEquityPointResponse(
        timestamp=point.timestamp,
        price=point.price,
        equity=point.equity,
        cash=point.cash,
        position=point.position,
        daily_return=point.daily_return,
    )


def _artifact_to_response(artifact) -> BacktestArtifactResponse:
    return BacktestArtifactResponse(
        artifact_type=artifact.artifact_type,
        content=artifact.content,
        uri=artifact.uri,
        description=artifact.description,
        created_at=artifact.created_at,
    )


def _parse_datetime(value) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
    logger.warning("Unable to parse timestamp '%s', defaulting to current time", value)
    return datetime.utcnow()


def _decision_from_dict(payload: dict) -> BacktestDecisionLogEntry:
    timestamp = _parse_datetime(payload.get("timestamp"))
    return BacktestDecisionLogEntry(
        timestamp=timestamp,
        processed_signal=payload.get("processed_signal", "") or "",
        raw_decision=payload.get("raw_decision"),
        equity=float(payload.get("equity", 0.0)),
        price=float(payload.get("price", 0.0)),
        position=float(payload.get("position", 0.0)),
    )


def _trade_from_dict(payload: dict) -> BacktestTradeLogEntry:
    timestamp = _parse_datetime(payload.get("timestamp"))
    return BacktestTradeLogEntry(
        timestamp=timestamp,
        action=payload.get("action", "") or "",
        quantity=float(payload.get("quantity", 0.0)),
        price=float(payload.get("price", 0.0)),
        cash=float(payload.get("cash", 0.0)),
        equity=float(payload.get("equity", 0.0)),
        position=float(payload.get("position", 0.0)),
    )


@router.post(
    "",
    response_model=BacktestRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_backtest(
    request: StartBacktestRequest,
    db: AsyncSession = Depends(get_db_session),
    service: BacktestService = Depends(get_backtest_service),
) -> BacktestRunResponse:
    repo = BacktestRunRepository(db)
    try:
        run = await service.start_backtest(session=repo, request=request)
        return _run_to_response(run)
    except ValueError as exc:
        logger.warning("Backtest validation failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:  # pragma: no cover - defensive guard
        logger.exception("Failed to start backtest: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start backtest",
        )


@router.get("", response_model=List[BacktestRunResponse])
async def list_backtests(
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db_session),
    service: BacktestService = Depends(get_backtest_service),
) -> List[BacktestRunResponse]:
    repo = BacktestRunRepository(db)
    runs = await service.list_runs(
        session=repo,
        status=status_filter,
        skip=skip,
        limit=limit,
    )
    return [_run_to_response(run) for run in runs]


@router.get("/{run_id}", response_model=BacktestRunDetailResponse)
async def get_backtest(
    run_id: str,
    db: AsyncSession = Depends(get_db_session),
    service: BacktestService = Depends(get_backtest_service),
) -> BacktestRunDetailResponse:
    repo = BacktestRunRepository(db)
    details = await service.get_run_details(session=repo, run_id=run_id)
    if not details:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backtest run not found")

    metrics_response = _metrics_to_response(details.get("metrics"))
    equity_curve_response = [
        _equity_point_to_response(point) for point in details.get("equity_curve", [])
    ]
    artifacts_response = [
        _artifact_to_response(artifact) for artifact in details.get("artifacts", [])
    ]

    return BacktestRunDetailResponse(
        run=_run_to_response(details["run"]),
        metrics=metrics_response,
        equity_curve=equity_curve_response,
        artifacts=artifacts_response,
    )


@router.get("/compare", response_model=BacktestComparisonResponse)
async def compare_backtests(
    run_ids: List[str] = Query(..., alias="id"),
    db: AsyncSession = Depends(get_db_session),
    service: BacktestService = Depends(get_backtest_service),
) -> BacktestComparisonResponse:
    if not run_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="At least one run id is required"
        )

    repo = BacktestRunRepository(db)
    comparisons = await service.compare_runs(session=repo, run_ids=run_ids)
    if not comparisons:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No matching backtest runs found"
        )

    entries: List[BacktestComparisonEntry] = []
    for item in comparisons:
        entries.append(
            BacktestComparisonEntry(
                run=_run_to_response(item["run"]),
                metrics=_metrics_to_response(item.get("metrics")),
            )
        )

    summary = BacktestComparisonSummary(
        top_total_return_run=_select_best(entries, key="total_return", reverse=True),
        top_sharpe_run=_select_best(entries, key="sharpe_ratio", reverse=True),
        lowest_drawdown_run=_select_best(entries, key="max_drawdown", reverse=False),
    )

    return BacktestComparisonResponse(runs=entries, summary=summary)


@router.get("/{run_id}/export", response_model=BacktestExportResponse)
async def export_backtest(
    run_id: str,
    db: AsyncSession = Depends(get_session),
) -> BacktestExportResponse:
    service = BacktestService()
    repo = BacktestRunRepository(db)
    payload = await service.export_run(session=repo, run_id=run_id)
    if not payload:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backtest run not found")

    decision_entries = [_decision_from_dict(entry) for entry in payload.get("decisions", [])]
    trade_entries = [_trade_from_dict(entry) for entry in payload.get("trades", [])]

    artifacts_response = [
        _artifact_to_response(artifact) for artifact in payload.get("artifacts", [])
    ]

    return BacktestExportResponse(
        run=_run_to_response(payload["run"]),
        metrics=_metrics_to_response(payload.get("metrics")),
        equity_curve=[_equity_point_to_response(p) for p in payload.get("equity_curve", [])],
        trades=trade_entries,
        decision_log=decision_entries,
        artifacts=artifacts_response,
    )


def _select_best(
    entries: List[BacktestComparisonEntry],
    *,
    key: str,
    reverse: bool,
) -> Optional[str]:
    best_value = None
    best_run_id = None
    for entry in entries:
        metrics = entry.metrics
        if metrics is None:
            continue
        value = getattr(metrics, key)
        if value is None:
            continue
        if best_value is None:
            best_value = value
            best_run_id = entry.run.run_id
            continue
        if (reverse and value > best_value) or (not reverse and value < best_value):
            best_value = value
            best_run_id = entry.run.run_id
    return best_run_id
