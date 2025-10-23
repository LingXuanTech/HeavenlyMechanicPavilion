"""Enhanced settings for database, Redis, and application configuration."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with database, Redis, and environment configuration."""

    # TradingAgents configuration
    llm_provider: Optional[str] = Field(default=None, alias="TRADINGAGENTS_LLM_PROVIDER")
    deep_think_llm: Optional[str] = Field(default=None, alias="TRADINGAGENTS_DEEP_THINK_LLM")
    quick_think_llm: Optional[str] = Field(default=None, alias="TRADINGAGENTS_QUICK_THINK_LLM")
    results_dir: Optional[str] = Field(default=None, alias="TRADINGAGENTS_RESULTS_DIR")

    # Database configuration
    database_url: str = Field(
        default="sqlite+aiosqlite:///./tradingagents.db",
        alias="DATABASE_URL",
    )
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")

    # Redis configuration
    redis_enabled: bool = Field(default=False, alias="REDIS_ENABLED")
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")

    # Application configuration
    debug: bool = Field(default=False, alias="DEBUG")
    api_title: str = Field(default="TradingAgents Backend", alias="API_TITLE")
    api_version: str = Field(default="0.1.0", alias="API_VERSION")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate and normalize database URL."""
        # Convert sync SQLite URLs to async
        if v.startswith("sqlite:///") and "aiosqlite" not in v:
            v = v.replace("sqlite:///", "sqlite+aiosqlite:///")
        # Convert sync PostgreSQL URLs to async
        if v.startswith("postgresql://") and "asyncpg" not in v:
            v = v.replace("postgresql://", "postgresql+asyncpg://")
        return v

    def config_overrides(self) -> Dict[str, Any]:
        """Get configuration overrides for TradingAgents graph.
        
        Returns:
            Dictionary of configuration overrides
        """
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

    @property
    def is_sqlite(self) -> bool:
        """Check if the database is SQLite."""
        return "sqlite" in self.database_url.lower()

    @property
    def is_postgresql(self) -> bool:
        """Check if the database is PostgreSQL."""
        return "postgresql" in self.database_url.lower()
