"""FastAPI application bootstrap for the TradingAgents backend."""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI

from .api import get_api_router
from .cache import init_redis
from .db import init_db
from .dependencies import get_settings
from .middleware import MetricsMiddleware

logger = logging.getLogger(__name__)

settings = get_settings()

app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description=(
        "REST + streaming interface wrapping the TradingAgents LangGraph-based "
        "workflow with persistence and caching support."
    ),
)

# Add metrics middleware if enabled
if settings.metrics_enabled:
    app.add_middleware(MetricsMiddleware)


@app.on_event("startup")
async def startup_event() -> None:
    """Initialize application resources on startup."""
    logger.info("Starting TradingAgents backend...")

    # Initialize database
    try:
        db_manager = init_db(
            database_url=settings.database_url,
            echo=settings.database_echo,
        )
        logger.info(f"Database initialized: {settings.database_url}")

        # Create tables if they don't exist (for development)
        # In production, use Alembic migrations instead
        if settings.debug:
            await db_manager.create_tables()
            logger.info("Database tables created (debug mode)")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    # Initialize vendor plugin registry
    try:
        from tradingagents.plugins import initialize_registry

        registry = initialize_registry()
        logger.info(
            f"Vendor plugin registry initialized with {len(registry.list_plugins())} plugins"
        )
    except Exception as e:
        logger.error(f"Failed to initialize vendor plugin registry: {e}")
        # Don't raise - continue without plugins

    # Initialize Redis if enabled
    if settings.redis_enabled:
        try:
            redis_manager = init_redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                password=settings.redis_password,
            )

            # Test Redis connection
            if await redis_manager.ping():
                logger.info(f"Redis initialized: {settings.redis_host}:{settings.redis_port}")

                # Initialize streaming infrastructure
                try:
                    from .services.streaming_config import StreamingConfigService
                    from .workers import init_worker_manager

                    config_service = StreamingConfigService(redis_manager)
                    worker_manager = init_worker_manager(redis_manager, config_service)
                    await worker_manager.initialize()

                    # Auto-start workers if configured
                    if settings.streaming_enabled and (
                        settings.auto_start_workers or settings.debug
                    ):
                        worker_manager.start_all()
                        logger.info("Background workers started")

                        # Start watchdog if enabled
                        if settings.watchdog_enabled:
                            from .workers.watchdog import start_watchdog

                            start_watchdog()
                            logger.info("Worker watchdog started")
                    else:
                        logger.info(
                            "Background workers initialized (use /streaming/config/workers/start-all to start)"
                        )

                except Exception as e:
                    logger.error(f"Failed to initialize streaming infrastructure: {e}")
            else:
                logger.warning("Redis ping failed, caching may not work correctly")
        except Exception as e:
            logger.warning(f"Failed to initialize Redis: {e}. Continuing without caching.")
    else:
        logger.info("Redis caching is disabled")

    logger.info("TradingAgents backend started successfully")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Cleanup application resources on shutdown."""
    logger.info("Shutting down TradingAgents backend...")

    # Stop watchdog
    if settings.watchdog_enabled:
        try:
            from .workers.watchdog import stop_watchdog

            await stop_watchdog()
            logger.info("Worker watchdog stopped")
        except Exception as e:
            logger.error(f"Error stopping watchdog: {e}")

    # Stop background workers
    if settings.redis_enabled:
        try:
            from .workers import get_worker_manager

            worker_manager = get_worker_manager()
            if worker_manager:
                await worker_manager.stop_all()
                logger.info("Background workers stopped")
        except Exception as e:
            logger.error(f"Error stopping workers: {e}")

    # Close database connections
    try:
        from .db import get_db_manager

        db_manager = get_db_manager()
        await db_manager.close()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")

    # Close Redis connections
    if settings.redis_enabled:
        try:
            from .cache import get_redis_manager

            redis_manager = get_redis_manager()
            if redis_manager:
                await redis_manager.close()
                logger.info("Redis connections closed")
        except Exception as e:
            logger.error(f"Error closing Redis: {e}")

    logger.info("TradingAgents backend shutdown complete")


app.include_router(get_api_router())


@app.get("/", tags=["health"])
async def root() -> dict[str, Any]:
    """Lightweight root endpoint primarily used for smoke tests."""

    return {
        "status": "ok",
        "message": "TradingAgents backend is running",
        "llm_provider": settings.llm_provider or "default",
        "database": "connected",
        "redis": "enabled" if settings.redis_enabled else "disabled",
    }


def create_app() -> FastAPI:  # pragma: no cover - convenience helper
    return app


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("RELOAD", "false").lower() == "true",
    )
