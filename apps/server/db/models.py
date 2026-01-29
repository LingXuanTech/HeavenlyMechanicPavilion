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


# ============ Prompt 配置模型 ============

class AgentCategory(str, Enum):
    """Agent 分类"""
    ANALYST = "analyst"           # 分析师：market, news, fundamentals, social, sentiment, policy
    RESEARCHER = "researcher"     # 研究员：bull, bear
    MANAGER = "manager"           # 管理层：research_manager, risk_manager
    RISK = "risk"                 # 风险辩论：aggressive, conservative, neutral
    TRADER = "trader"             # 交易员
    SYNTHESIZER = "synthesizer"   # 合成器


class AgentPrompt(SQLModel, table=True):
    """Agent Prompt 配置"""
    __tablename__ = "agent_prompts"
    __table_args__ = (
        Index("ix_prompt_agent_active", "agent_key", "is_active"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    agent_key: str = Field(index=True)                    # "market_analyst", "bull_researcher" 等
    category: AgentCategory = Field(default=AgentCategory.ANALYST)
    display_name: str = Field(default="")                 # 显示名称，如 "市场分析师"
    description: str = Field(default="")                  # Agent 职责描述

    # Prompt 内容
    system_prompt: str = Field(default="")                # 系统提示词
    user_prompt_template: str = Field(default="")         # 用户消息模板，支持 {variable} 占位符

    # 可用变量说明（JSON 数组）
    available_variables: str = Field(default="[]")        # ["ticker", "date", "data", "market"]

    # 配置元数据
    version: int = Field(default=1)                       # 版本号
    is_active: bool = Field(default=True)                 # 是否激活（同一 agent_key 可有多版本，仅一个激活）
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class PromptVersion(SQLModel, table=True):
    """Prompt 版本历史（用于回滚）"""
    __tablename__ = "prompt_versions"

    id: Optional[int] = Field(default=None, primary_key=True)
    prompt_id: int = Field(foreign_key="agent_prompts.id", index=True)
    version: int
    system_prompt: str
    user_prompt_template: str
    change_note: str = Field(default="")                  # 变更说明
    created_at: datetime = Field(default_factory=datetime.now)
    created_by: str = Field(default="system")             # 修改人（用于审计）


# ============ 用户认证模型 ============

class User(SQLModel, table=True):
    """用户表"""
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: Optional[str] = Field(default=None)  # OAuth 用户可无密码
    display_name: Optional[str] = Field(default=None)
    avatar_url: Optional[str] = Field(default=None)
    email_verified: bool = Field(default=False)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class OAuthAccount(SQLModel, table=True):
    """OAuth 第三方账号关联"""
    __tablename__ = "oauth_accounts"
    __table_args__ = (
        Index("ix_oauth_provider_user", "provider", "provider_user_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    provider: str  # google, github, wechat
    provider_user_id: str
    access_token: Optional[str] = Field(default=None)
    refresh_token: Optional[str] = Field(default=None)
    expires_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)


class WebAuthnCredential(SQLModel, table=True):
    """WebAuthn / Passkey 凭证"""
    __tablename__ = "webauthn_credentials"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    credential_id: str = Field(unique=True, index=True)
    public_key: str  # Base64 编码
    sign_count: int = Field(default=0)
    device_name: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.now)
    last_used_at: Optional[datetime] = Field(default=None)


class RefreshToken(SQLModel, table=True):
    """刷新令牌表"""
    __tablename__ = "refresh_tokens"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    token: str = Field(unique=True, index=True)
    expires_at: datetime
    revoked: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.now)


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
