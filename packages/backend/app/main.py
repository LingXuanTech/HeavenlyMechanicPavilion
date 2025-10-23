"""FastAPI application bootstrap for the TradingAgents backend."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI

from .api import get_api_router
from .dependencies import get_settings

settings = get_settings()

app = FastAPI(
    title="TradingAgents Backend",
    version="0.1.0",
    description=(
        "REST + streaming interface wrapping the TradingAgents LangGraph-based "
        "workflow."
    ),
)

app.include_router(get_api_router())


@app.get("/", tags=["health"])
async def root() -> dict[str, Any]:
    """Lightweight root endpoint primarily used for smoke tests."""

    return {
        "status": "ok",
        "message": "TradingAgents backend is running",
        "llm_provider": settings.llm_provider or "default",
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
