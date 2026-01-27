from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # API Settings
    API_V1_STR: str = "/api"
    PROJECT_NAME: str = "Stock Agents Monitoring Dashboard"

    # Security
    API_KEY: str = os.getenv("API_KEY", "dev-key-12345")
    API_KEY_ENABLED: bool = os.getenv("API_KEY_ENABLED", "false").lower() == "true"
    CORS_ORIGINS: list[str] = ["*"]

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

settings = Settings()
