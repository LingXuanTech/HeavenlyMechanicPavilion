"""Enhanced settings for database, Redis, and application configuration."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with database, Redis, and environment configuration."""

    # ===== TradingAgents 核心配置 =====
    llm_provider: str = Field(default="openai", alias="TRADINGAGENTS_LLM_PROVIDER")
    deep_think_llm: str = Field(default="o4-mini", alias="TRADINGAGENTS_DEEP_THINK_LLM")
    quick_think_llm: str = Field(default="gpt-4o-mini", alias="TRADINGAGENTS_QUICK_THINK_LLM")
    results_dir: str = Field(default="./results", alias="TRADINGAGENTS_RESULTS_DIR")

    # TradingAgents 路径配置
    project_dir: str = Field(default=".", alias="TRADINGAGENTS_PROJECT_DIR")
    data_dir: str = Field(default="./data", alias="TRADINGAGENTS_DATA_DIR")
    data_cache_dir: str = Field(default="./data_cache", alias="TRADINGAGENTS_DATA_CACHE_DIR")

    # LLM Backend URL
    backend_url: str = Field(default="https://api.openai.com/v1", alias="TRADINGAGENTS_BACKEND_URL")

    # 辩论和讨论设置
    max_debate_rounds: int = Field(default=1, alias="TRADINGAGENTS_MAX_DEBATE_ROUNDS")
    max_risk_discuss_rounds: int = Field(default=1, alias="TRADINGAGENTS_MAX_RISK_DISCUSS_ROUNDS")
    max_recur_limit: int = Field(default=100, alias="TRADINGAGENTS_MAX_RECUR_LIMIT")

    # 数据供应商配置
    vendor_core_stock_apis: str = Field(default="yfinance", alias="VENDOR_CORE_STOCK_APIS")
    vendor_technical_indicators: str = Field(
        default="yfinance", alias="VENDOR_TECHNICAL_INDICATORS"
    )
    vendor_fundamental_data: str = Field(default="alpha_vantage", alias="VENDOR_FUNDAMENTAL_DATA")
    vendor_news_data: str = Field(default="alpha_vantage", alias="VENDOR_NEWS_DATA")

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
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    api_title: str = Field(default="TradingAgents Backend", alias="API_TITLE")
    api_version: str = Field(default="0.1.0", alias="API_VERSION")

    # Error tracking / observability
    error_tracking_enabled: bool = Field(default=False, alias="ERROR_TRACKING_ENABLED")
    sentry_dsn: Optional[str] = Field(default=None, alias="SENTRY_DSN")
    sentry_traces_sample_rate: float = Field(default=0.0, alias="SENTRY_TRACES_SAMPLE_RATE")
    sentry_profiles_sample_rate: float = Field(default=0.0, alias="SENTRY_PROFILES_SAMPLE_RATE")

    # Resilience defaults
    retry_default_attempts: int = Field(default=3, alias="RETRY_DEFAULT_ATTEMPTS")
    retry_default_backoff_seconds: float = Field(default=0.5, alias="RETRY_DEFAULT_BACKOFF_SECONDS")
    retry_max_backoff_seconds: float = Field(default=30.0, alias="RETRY_MAX_BACKOFF_SECONDS")
    circuit_breaker_failure_threshold: int = Field(default=5, alias="CIRCUIT_BREAKER_FAILURE_THRESHOLD")
    circuit_breaker_recovery_seconds: int = Field(default=60, alias="CIRCUIT_BREAKER_RECOVERY_SECONDS")
    circuit_breaker_half_open_successes: int = Field(
        default=1, alias="CIRCUIT_BREAKER_HALF_OPEN_SUCCESSES"
    )

    # Authentication configuration
    jwt_secret_key: str = Field(
        default="change-this-secret-key-in-production-use-openssl-rand-hex-32",
        alias="JWT_SECRET_KEY",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_access_token_expire_minutes: int = Field(
        default=30, alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    jwt_refresh_token_expire_days: int = Field(default=7, alias="JWT_REFRESH_TOKEN_EXPIRE_DAYS")

    # Rate limiting configuration
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(default=1000, alias="RATE_LIMIT_PER_HOUR")

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

    @property
    def data_vendors(self) -> Dict[str, str]:
        """获取数据供应商配置字典.

        Returns:
            数据供应商配置
        """
        return {
            "core_stock_apis": self.vendor_core_stock_apis,
            "technical_indicators": self.vendor_technical_indicators,
            "fundamental_data": self.vendor_fundamental_data,
            "news_data": self.vendor_news_data,
        }

    @property
    def tradingagents_config(self) -> Dict[str, Any]:
        """获取 TradingAgents 完整配置字典 (兼容旧的 default_config.py 格式).

        Returns:
            完整的 TradingAgents 配置
        """
        return {
            "project_dir": self.project_dir,
            "results_dir": self.results_dir,
            "data_dir": self.data_dir,
            "data_cache_dir": self.data_cache_dir,
            "llm_provider": self.llm_provider,
            "deep_think_llm": self.deep_think_llm,
            "quick_think_llm": self.quick_think_llm,
            "backend_url": self.backend_url,
            "max_debate_rounds": self.max_debate_rounds,
            "max_risk_discuss_rounds": self.max_risk_discuss_rounds,
            "max_recur_limit": self.max_recur_limit,
            "data_vendors": self.data_vendors,
            "tool_vendors": {},  # 可以后续扩展为工具级别的配置
        }


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance (singleton)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
