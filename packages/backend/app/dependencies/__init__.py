"""Application dependency wiring for FastAPI."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Dict

from pydantic import BaseSettings, Field

from ..services.events import SessionEventManager
from ..services.graph import TradingGraphService


class BackendSettings(BaseSettings):
    """Environment-driven configuration for the FastAPI backend."""

    llm_provider: str | None = Field(default=None, alias="TRADINGAGENTS_LLM_PROVIDER")
    deep_think_llm: str | None = Field(default=None, alias="TRADINGAGENTS_DEEP_THINK_LLM")
    quick_think_llm: str | None = Field(default=None, alias="TRADINGAGENTS_QUICK_THINK_LLM")
    results_dir: str | None = Field(default=None, alias="TRADINGAGENTS_RESULTS_DIR")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def config_overrides(self) -> Dict[str, Any]:
        overrides: Dict[str, Any] = {}
        if self.llm_provider:
            overrides["llm_provider"] = self.llm_provider
        if self.deep_think_llm:
            overrides["deep_think_llm"] = self.deep_think_llm
        if self.quick_think_llm:
            overrides["quick_think_llm"] = self.quick_think_llm
        if self.results_dir:
            overrides["results_dir"] = self.results_dir
        return overrides


_settings = BackendSettings()
_event_manager = SessionEventManager()


def get_settings() -> BackendSettings:
    return _settings


def get_event_manager() -> SessionEventManager:
    return _event_manager


@lru_cache
def get_graph_service() -> TradingGraphService:
    return TradingGraphService(
        event_manager=_event_manager,
        config_overrides=_settings.config_overrides(),
    )
