from pydantic_settings import BaseSettings
from typing import Optional, List
import os
import sys

def _parse_cors_origins() -> List[str]:
    """解析 CORS_ORIGINS 环境变量（逗号分隔）"""
    origins_str = os.getenv("CORS_ORIGINS", "")
    if origins_str:
        return [o.strip() for o in origins_str.split(",") if o.strip()]
    # 默认仅允许本地开发
    return ["http://localhost:3000", "http://127.0.0.1:3000"]


class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "Stock Agents Monitoring Dashboard"

    # Environment
    ENV: str = os.getenv("ENV", "development")  # development | production

    # Security
    API_KEY: str = os.getenv("API_KEY", "")  # 生产环境必须配置
    API_KEY_ENABLED: bool = os.getenv("API_KEY_ENABLED", "false").lower() == "true"
    CORS_ORIGINS: List[str] = _parse_cors_origins()

    # LLM Settings
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    ANTHROPIC_API_KEY: Optional[str] = os.getenv("ANTHROPIC_API_KEY")
    GOOGLE_API_KEY: Optional[str] = os.getenv("GOOGLE_API_KEY")

    # Data Provider Keys
    ALPHA_VANTAGE_API_KEY: Optional[str] = os.getenv("ALPHA_VANTAGE_API_KEY")
    FRED_API_KEY: Optional[str] = os.getenv("FRED_API_KEY")  # Federal Reserve Economic Data
    FINNHUB_API_KEY: Optional[str] = os.getenv("FINNHUB_API_KEY")  # Finnhub Stock API

    # Database - Dual Mode Support (sqlite / postgresql)
    DATABASE_MODE: str = os.getenv("DATABASE_MODE", "sqlite")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./db/trading.db")

    # PostgreSQL Settings (only used when DATABASE_MODE=postgresql)
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "trading")

    # ChromaDB
    CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", "./db/chroma")

    # Redis (可选，未配置时使用内存缓存)
    REDIS_URL: Optional[str] = os.getenv("REDIS_URL")

    # Prompt Config
    PROMPTS_YAML_PATH: str = os.getenv("PROMPTS_YAML_PATH", "./config/prompts.yaml")

    # Scheduler Settings
    DAILY_ANALYSIS_ENABLED: bool = os.getenv("DAILY_ANALYSIS_ENABLED", "false").lower() == "true"
    DAILY_ANALYSIS_HOUR: int = int(os.getenv("DAILY_ANALYSIS_HOUR", "9"))
    DAILY_ANALYSIS_MINUTE: int = int(os.getenv("DAILY_ANALYSIS_MINUTE", "30"))

    @property
    def database_url(self) -> str:
        """动态生成数据库连接 URL"""
        if self.DATABASE_MODE == "postgresql":
            return (
                f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        return self.DATABASE_URL

    class Config:
        case_sensitive = True
        env_file = ".env"

    def validate_production(self) -> None:
        """生产环境启动前验证"""
        if self.ENV != "production":
            return

        errors = []

        if self.API_KEY_ENABLED and not self.API_KEY:
            errors.append("API_KEY must be set when API_KEY_ENABLED=true in production")

        if not self.OPENAI_API_KEY and not self.GOOGLE_API_KEY:
            errors.append("At least one LLM API key (OPENAI_API_KEY or GOOGLE_API_KEY) must be set")

        if self.DATABASE_MODE == "postgresql" and not self.POSTGRES_PASSWORD:
            errors.append("POSTGRES_PASSWORD must be set when using PostgreSQL")

        if errors:
            for err in errors:
                print(f"[CONFIG ERROR] {err}", file=sys.stderr)
            sys.exit(1)


settings = Settings()
# 生产环境启动时自动验证
settings.validate_production()
