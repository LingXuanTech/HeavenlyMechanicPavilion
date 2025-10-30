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

    # LLM Provider API Keys
    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    deepseek_api_key: Optional[str] = Field(default=None, alias="DEEPSEEK_API_KEY")
    grok_api_key: Optional[str] = Field(default=None, alias="GROK_API_KEY")
    anthropic_api_key: Optional[str] = Field(default=None, alias="ANTHROPIC_API_KEY")

    # Encryption key for sensitive data
    encryption_key: Optional[str] = Field(default=None, alias="ENCRYPTION_KEY")

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
    
    # Streaming configuration
    streaming_enabled: bool = Field(default=True, alias="STREAMING_ENABLED")
    auto_start_workers: bool = Field(default=False, alias="AUTO_START_WORKERS")

    # Monitoring configuration
    monitoring_enabled: bool = Field(default=True, alias="MONITORING_ENABLED")
    metrics_enabled: bool = Field(default=True, alias="METRICS_ENABLED")
    
    # Alerting configuration
    alerting_enabled: bool = Field(default=False, alias="ALERTING_ENABLED")
    alert_email_enabled: bool = Field(default=False, alias="ALERT_EMAIL_ENABLED")
    alert_email_to: Optional[str] = Field(default=None, alias="ALERT_EMAIL_TO")
    alert_email_from: Optional[str] = Field(default=None, alias="ALERT_EMAIL_FROM")
    smtp_host: Optional[str] = Field(default=None, alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_username: Optional[str] = Field(default=None, alias="SMTP_USERNAME")
    smtp_password: Optional[str] = Field(default=None, alias="SMTP_PASSWORD")
    smtp_use_tls: bool = Field(default=True, alias="SMTP_USE_TLS")
    
    alert_webhook_enabled: bool = Field(default=False, alias="ALERT_WEBHOOK_ENABLED")
    alert_webhook_url: Optional[str] = Field(default=None, alias="ALERT_WEBHOOK_URL")
    alert_webhook_headers: Optional[str] = Field(default=None, alias="ALERT_WEBHOOK_HEADERS")
    
    # Worker watchdog configuration
    watchdog_enabled: bool = Field(default=True, alias="WATCHDOG_ENABLED")
    watchdog_check_interval: int = Field(default=60, alias="WATCHDOG_CHECK_INTERVAL")
    watchdog_task_timeout: int = Field(default=300, alias="WATCHDOG_TASK_TIMEOUT")

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
