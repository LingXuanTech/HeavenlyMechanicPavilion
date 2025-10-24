"""Configuration endpoints for streaming infrastructure."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from ..cache import RedisManager, get_redis_manager
from ..dependencies import get_settings
from ..schemas.streaming import (
    DataType,
    InstrumentConfig,
    RefreshCadence,
    StreamingConfig,
    TelemetryRecord,
    WorkerStatus,
)
from ..services.streaming_config import StreamingConfigService
from ..workers import get_worker_manager

router = APIRouter()


def get_config_service(
    redis: Optional[RedisManager] = Depends(get_redis_manager),
    settings = Depends(get_settings),
) -> StreamingConfigService:
    """Get streaming config service dependency.
    
    Args:
        redis: Redis manager
        settings: Application settings
        
    Returns:
        StreamingConfigService instance
    """
    if not settings.redis_enabled or not redis:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis is required for streaming configuration",
        )
    return StreamingConfigService(redis)


# Configuration endpoints
@router.get("/config", response_model=StreamingConfig)
async def get_config(
    service: StreamingConfigService = Depends(get_config_service),
):
    """Get complete streaming configuration."""
    return await service.get_config()


@router.put("/config", response_model=StreamingConfig)
async def update_config(
    config: StreamingConfig,
    service: StreamingConfigService = Depends(get_config_service),
):
    """Update complete streaming configuration."""
    return await service.update_config(config)


# Instrument endpoints
@router.get("/instruments", response_model=List[InstrumentConfig])
async def list_instruments(
    service: StreamingConfigService = Depends(get_config_service),
):
    """List all configured instruments."""
    return await service.list_instruments()


@router.post("/instruments", response_model=InstrumentConfig, status_code=status.HTTP_201_CREATED)
async def add_instrument(
    instrument: InstrumentConfig,
    service: StreamingConfigService = Depends(get_config_service),
):
    """Add or update an instrument configuration."""
    return await service.add_instrument(instrument)


@router.get("/instruments/{symbol}", response_model=InstrumentConfig)
async def get_instrument(
    symbol: str,
    service: StreamingConfigService = Depends(get_config_service),
):
    """Get configuration for a specific instrument."""
    instrument = await service.get_instrument(symbol.upper())
    if not instrument:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instrument {symbol} not found",
        )
    return instrument


@router.delete("/instruments/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_instrument(
    symbol: str,
    service: StreamingConfigService = Depends(get_config_service),
):
    """Remove an instrument configuration."""
    removed = await service.remove_instrument(symbol.upper())
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Instrument {symbol} not found",
        )


# Cadence endpoints
@router.get("/cadences/{data_type}", response_model=RefreshCadence)
async def get_cadence(
    data_type: DataType,
    service: StreamingConfigService = Depends(get_config_service),
):
    """Get refresh cadence for a data type."""
    cadence = await service.get_cadence(data_type)
    if not cadence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cadence for {data_type} not found",
        )
    return cadence


@router.put("/cadences/{data_type}", response_model=RefreshCadence)
async def update_cadence(
    data_type: DataType,
    cadence: RefreshCadence,
    service: StreamingConfigService = Depends(get_config_service),
):
    """Update refresh cadence for a data type."""
    if cadence.data_type != data_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data type in path must match data type in body",
        )
    return await service.update_cadence(cadence)


# Worker management endpoints
@router.get("/workers", response_model=List[WorkerStatus])
async def list_workers():
    """List all workers and their status."""
    manager = get_worker_manager()
    if not manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Worker manager not initialized",
        )
    return manager.get_all_statuses()


@router.get("/workers/{worker_id}", response_model=WorkerStatus)
async def get_worker_status(worker_id: str):
    """Get status of a specific worker."""
    manager = get_worker_manager()
    if not manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Worker manager not initialized",
        )
    
    status_info = manager.get_worker_status(worker_id)
    if not status_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker {worker_id} not found",
        )
    return status_info


@router.post("/workers/{worker_id}/start", status_code=status.HTTP_204_NO_CONTENT)
async def start_worker(worker_id: str):
    """Start a specific worker."""
    manager = get_worker_manager()
    if not manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Worker manager not initialized",
        )
    
    if not manager.start_worker(worker_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker {worker_id} not found",
        )


@router.post("/workers/{worker_id}/stop", status_code=status.HTTP_204_NO_CONTENT)
async def stop_worker(worker_id: str):
    """Stop a specific worker."""
    manager = get_worker_manager()
    if not manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Worker manager not initialized",
        )
    
    if not await manager.stop_worker(worker_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Worker {worker_id} not found",
        )


@router.post("/workers/start-all", status_code=status.HTTP_204_NO_CONTENT)
async def start_all_workers():
    """Start all workers."""
    manager = get_worker_manager()
    if not manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Worker manager not initialized",
        )
    manager.start_all()


@router.post("/workers/stop-all", status_code=status.HTTP_204_NO_CONTENT)
async def stop_all_workers():
    """Stop all workers."""
    manager = get_worker_manager()
    if not manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Worker manager not initialized",
        )
    await manager.stop_all()


# Telemetry endpoints
@router.get("/telemetry/{data_type}", response_model=List[TelemetryRecord])
async def get_telemetry(
    data_type: DataType,
    limit: int = 100,
    redis: Optional[RedisManager] = Depends(get_redis_manager),
    settings = Depends(get_settings),
):
    """Get telemetry records for a data type.
    
    Args:
        data_type: Data type to get telemetry for
        limit: Maximum number of records to return
        redis: Redis manager
        settings: Application settings
        
    Returns:
        List of telemetry records
    """
    if not settings.redis_enabled or not redis:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis is required for telemetry",
        )
    
    telemetry_key = f"telemetry:{data_type.value}"
    records = await redis.client.lrange(telemetry_key, 0, limit - 1)
    
    import json
    telemetry_records = []
    for record in records:
        try:
            data = json.loads(record)
            telemetry_records.append(TelemetryRecord(**data))
        except Exception:
            continue
    
    return telemetry_records
