from datetime import datetime
from typing import Optional, List
from enum import Enum
from sqlmodel import SQLModel, Field, create_engine, Session, select
from sqlalchemy import Index
from sqlalchemy.pool import StaticPool
from config.settings import settings
import structlog

logger = structlog.get_logger()


class Watchlist(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True, unique=True)
    name: str
    market: str
    added_at: datetime = Field(default_factory=datetime.now)


class AnalysisResult(SQLModel, table=True):
    __table_args__ = (
        # 复合索引：优化 "获取指定股票的最新分析" 查询
        Index("ix_analysis_symbol_created", "symbol", "created_at"),
        # 复合索引：优化 "按状态筛选指定股票分析" 查询
        Index("ix_analysis_symbol_status", "symbol", "status"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    date: str = Field(index=True)
    signal: str
    confidence: int
    full_report_json: str  # Store as JSON string
    anchor_script: str
    created_at: datetime = Field(default_factory=datetime.now)
    # 新增字段用于任务追踪
    task_id: Optional[str] = Field(default=None, index=True)
    status: str = Field(default="completed")  # pending/running/completed/failed
    error_message: Optional[str] = Field(default=None)
    # 诊断信息
    elapsed_seconds: Optional[float] = Field(default=None)
    token_usage: Optional[str] = Field(default=None)  # JSON string


class ChatHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    thread_id: str = Field(index=True)
    role: str
    content: str
    created_at: datetime = Field(default_factory=datetime.now)


# ============ AI 配置模型 ============

class AIProviderType(str, Enum):
    """AI 提供商类型"""
    OPENAI = "openai"                       # 官方 OpenAI
    OPENAI_COMPATIBLE = "openai_compatible" # NewAPI/OneAPI/OpenRouter 等兼容接口
    GOOGLE = "google"                       # Google Gemini
    ANTHROPIC = "anthropic"                 # Anthropic Claude
    DEEPSEEK = "deepseek"                   # DeepSeek (OpenAI 兼容)


class AIProvider(SQLModel, table=True):
    """AI 模型提供商配置"""
    __tablename__ = "ai_providers"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)  # 显示名称，如 "OpenAI Official"
    provider_type: AIProviderType = Field(default=AIProviderType.OPENAI)
    base_url: Optional[str] = Field(default=None)  # API 端点，OpenAI 兼容时必填
    api_key: str = Field(default="")               # 加密存储
    models: str = Field(default="[]")              # JSON: ["gpt-4o", "gpt-4o-mini"]
    is_enabled: bool = Field(default=True)
    priority: int = Field(default=0)               # 优先级，数字越小优先级越高
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class AIModelConfig(SQLModel, table=True):
    """AI 模型使用配置（哪个场景用哪个模型）"""
    __tablename__ = "ai_model_configs"

    id: Optional[int] = Field(default=None, primary_key=True)
    config_key: str = Field(index=True, unique=True)  # "deep_think", "quick_think", "synthesis"
    provider_id: Optional[int] = Field(default=None, foreign_key="ai_providers.id")
    model_name: str = Field(default="")               # 具体模型名
    is_active: bool = Field(default=True)
    updated_at: datetime = Field(default_factory=datetime.now)


def get_engine():
    """根据配置创建数据库引擎"""
    db_url = settings.database_url
    logger.info("Creating database engine", mode=settings.DATABASE_MODE, url=db_url.split("@")[-1] if "@" in db_url else db_url)

    if settings.DATABASE_MODE == "sqlite":
        # SQLite 配置：单线程检查关闭，使用 StaticPool
        return create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        # PostgreSQL 配置：启用连接池预检
        return create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )


engine = get_engine()


def init_db():
    """初始化数据库表"""
    logger.info("Initializing database tables")
    SQLModel.metadata.create_all(engine)


def get_session():
    """获取数据库会话（用于 FastAPI 依赖注入）"""
    with Session(engine) as session:
        yield session
