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
    architecture_mode: str = Field(default="monolith")  # monolith / subgraph


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


# ============ 预测追踪模型 ============

class PredictionOutcome(SQLModel, table=True):
    """预测结果追踪（用于反思闭环）"""
    __tablename__ = "prediction_outcomes"
    __table_args__ = (
        Index("ix_prediction_symbol_date", "symbol", "prediction_date"),
        Index("ix_prediction_agent", "agent_key"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    # 预测信息
    analysis_id: int = Field(foreign_key="analysisresult.id", index=True)
    symbol: str = Field(index=True)
    prediction_date: str = Field(index=True)           # 预测日期
    signal: str                                        # 预测信号：Strong Buy/Buy/Hold/Sell/Strong Sell
    confidence: int                                    # 预测置信度 0-100
    target_price: Optional[float] = Field(default=None)
    stop_loss: Optional[float] = Field(default=None)
    entry_price: Optional[float] = Field(default=None)

    # Agent 信息
    agent_key: str = Field(default="overall")          # 哪个 Agent 的预测

    # 实际结果
    outcome_date: Optional[str] = Field(default=None)  # 结果日期
    actual_price: Optional[float] = Field(default=None)
    actual_return: Optional[float] = Field(default=None)  # 百分比收益
    outcome: Optional[str] = Field(default=None)       # Win/Loss/Partial/Pending

    # 分析
    is_correct: Optional[bool] = Field(default=None)   # 方向是否正确
    return_vs_benchmark: Optional[float] = Field(default=None)  # 相对基准收益
    notes: Optional[str] = Field(default=None)         # 备注

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now)
    evaluated_at: Optional[datetime] = Field(default=None)


class AgentPerformance(SQLModel, table=True):
    """Agent 表现统计（定期聚合）"""
    __tablename__ = "agent_performance"
    __table_args__ = (
        Index("ix_agent_perf_key_period", "agent_key", "period_start"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    agent_key: str = Field(index=True)                 # Agent 标识
    period_start: str = Field(index=True)              # 统计周期开始日期
    period_end: str                                    # 统计周期结束日期

    # 统计指标
    total_predictions: int = Field(default=0)          # 总预测数
    correct_predictions: int = Field(default=0)        # 正确预测数
    win_rate: float = Field(default=0.0)               # 胜率
    avg_return: float = Field(default=0.0)             # 平均收益
    avg_confidence: float = Field(default=0.0)         # 平均置信度

    # 细分统计
    strong_buy_accuracy: Optional[float] = Field(default=None)
    buy_accuracy: Optional[float] = Field(default=None)
    hold_accuracy: Optional[float] = Field(default=None)
    sell_accuracy: Optional[float] = Field(default=None)
    strong_sell_accuracy: Optional[float] = Field(default=None)

    # 偏差分析
    overconfidence_bias: Optional[float] = Field(default=None)  # 过度自信偏差
    direction_bias: Optional[str] = Field(default=None)         # 方向偏差：bullish/bearish/neutral

    # 时间戳
    calculated_at: datetime = Field(default_factory=datetime.now)


class ModelPerformance(SQLModel, table=True):
    """模型表现追踪（多模型赛马）"""
    __tablename__ = "model_performance"
    __table_args__ = (
        Index("ix_model_perf_key_period", "model_key", "period_start"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    model_key: str = Field(index=True)                 # 模型配置键（deep_think, quick_think 等）
    model_name: str = Field(default="")                # 实际模型名（gpt-4o, claude-3-sonnet 等）
    provider: str = Field(default="")                  # 提供商（openai, anthropic, google）
    period_start: str = Field(index=True)              # 统计周期开始日期
    period_end: str                                    # 统计周期结束日期

    # 统计指标
    total_predictions: int = Field(default=0)          # 总预测数
    correct_predictions: int = Field(default=0)        # 正确预测数
    win_rate: float = Field(default=0.0)               # 胜率
    avg_return: float = Field(default=0.0)             # 平均收益
    avg_confidence: float = Field(default=0.0)         # 平均置信度
    avg_response_time: float = Field(default=0.0)      # 平均响应时间（秒）

    # 共识一致率
    consensus_agreement_rate: float = Field(default=0.0)  # 与最终共识的一致率

    # 细分统计
    strong_buy_accuracy: Optional[float] = Field(default=None)
    buy_accuracy: Optional[float] = Field(default=None)
    sell_accuracy: Optional[float] = Field(default=None)

    # 偏差分析
    overconfidence_bias: Optional[float] = Field(default=None)
    direction_bias: Optional[str] = Field(default=None)

    # 时间戳
    calculated_at: datetime = Field(default_factory=datetime.now)


class RacingAnalysisResult(SQLModel, table=True):
    """赛马分析结果记录"""
    __tablename__ = "racing_analysis_results"
    __table_args__ = (
        Index("ix_racing_symbol_created", "symbol", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    symbol: str = Field(index=True)
    market: str = Field(default="US")
    analysis_date: str = Field(index=True)

    # 共识结果
    consensus_signal: str                              # 最终共识信号
    consensus_confidence: int                          # 共识置信度
    consensus_method: str                              # 使用的共识方法
    agreement_rate: float                              # 一致率

    # 各模型结果（JSON 存储）
    model_results_json: str = Field(default="{}")      # JSON: {model_key: {signal, confidence, ...}}
    dissenting_models: str = Field(default="[]")       # JSON: ["model_key1", "model_key2"]

    # 元数据
    total_models: int = Field(default=0)
    successful_models: int = Field(default=0)
    total_elapsed_seconds: float = Field(default=0.0)

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now)


class BacktestResultRecord(SQLModel, table=True):
    """回测结果记录"""
    __tablename__ = "backtest_results"
    __table_args__ = (
        Index("ix_backtest_symbol_created", "symbol", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    symbol: str = Field(index=True)
    market: str = Field(default="US")
    start_date: str
    end_date: str

    # 资金指标
    initial_capital: float = Field(default=100000)
    final_capital: float = Field(default=100000)
    total_return_pct: float = Field(default=0)
    annualized_return_pct: float = Field(default=0)
    max_drawdown_pct: float = Field(default=0)
    sharpe_ratio: Optional[float] = Field(default=None)

    # 交易统计
    total_trades: int = Field(default=0)
    winning_trades: int = Field(default=0)
    losing_trades: int = Field(default=0)
    win_rate: float = Field(default=0)
    avg_win_pct: float = Field(default=0)
    avg_loss_pct: float = Field(default=0)
    profit_factor: Optional[float] = Field(default=None)

    # 基准对比
    benchmark_return_pct: Optional[float] = Field(default=None)
    alpha: Optional[float] = Field(default=None)

    # 交易明细（JSON 存储）
    trades_json: str = Field(default="[]")

    # 配置参数
    holding_days: int = Field(default=5)
    stop_loss_pct: float = Field(default=-5.0)
    take_profit_pct: float = Field(default=10.0)

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now)


# ============ 北向资金历史数据模型 ============

class NorthMoneyHistoryRecord(SQLModel, table=True):
    """北向资金历史数据记录（持久化存储）"""
    __tablename__ = "north_money_history"
    __table_args__ = (
        Index("ix_north_money_date", "date"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)

    # 日期（唯一索引，每日一条记录）
    date: str = Field(index=True, unique=True)             # 日期 YYYY-MM-DD 格式

    # 北向资金流向数据
    north_inflow: float = Field(default=0.0)               # 北向资金净流入（亿元）
    sh_inflow: float = Field(default=0.0)                  # 沪股通净流入（亿元）
    sz_inflow: float = Field(default=0.0)                  # 深股通净流入（亿元）
    cumulative_inflow: float = Field(default=0.0)          # 累计净流入（亿元）

    # 市场指数数据（用于相关性计算）
    market_index: Optional[float] = Field(default=None)    # 当日上证指数收盘价
    hs300_index: Optional[float] = Field(default=None)     # 当日沪深300收盘价
    cyb_index: Optional[float] = Field(default=None)       # 当日创业板指收盘价

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ============ 北向资金板块流向历史 ============

class NorthMoneySectorRecord(SQLModel, table=True):
    """北向资金板块级流向历史记录"""
    __tablename__ = "north_money_sector_history"
    __table_args__ = (
        Index("ix_north_sector_date_name", "date", "sector_name"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    date: str = Field(index=True)                              # 日期 YYYY-MM-DD
    sector_name: str = Field(index=True)                       # 板块名称
    net_inflow: float = Field(default=0.0)                     # 板块净流入（亿元）
    buy_amount: float = Field(default=0.0)                     # 买入金额（亿元）
    sell_amount: float = Field(default=0.0)                    # 卖出金额（亿元）
    top_stocks_json: str = Field(default="[]")                 # 板块内 TOP 股票 JSON

    created_at: datetime = Field(default_factory=datetime.now)


# ============ Vision 分析记录 ============

class VisionAnalysisRecord(SQLModel, table=True):
    """Vision 图表分析持久化记录"""
    __tablename__ = "vision_analysis_records"
    __table_args__ = (
        Index("ix_vision_symbol_created", "symbol", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: Optional[str] = Field(default=None, index=True)    # 关联股票代码
    content_type: str = Field(default="image")                 # image | audio
    file_name: Optional[str] = Field(default=None)             # 原始文件名
    file_size: Optional[int] = Field(default=None)             # 文件大小（字节）
    description: Optional[str] = Field(default=None)           # 用户补充说明
    analysis_json: str = Field(default="{}")                   # 分析结果 JSON
    chart_type: Optional[str] = Field(default=None)            # 图表类型
    confidence: Optional[float] = Field(default=None)          # 置信度
    batch_id: Optional[str] = Field(default=None, index=True)  # 批量分析 ID

    created_at: datetime = Field(default_factory=datetime.now)


# ============ 推送通知模型 ============

class NotificationConfig(SQLModel, table=True):
    """用户推送通知配置"""
    __tablename__ = "notification_configs"
    __table_args__ = (
        Index("ix_notif_config_user_channel", "user_id", "channel", unique=True),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)                           # 关联用户 ID
    channel: str = Field(default="telegram")                   # telegram | wechat | email
    channel_user_id: Optional[str] = Field(default=None)       # 渠道内用户标识（如 chat_id）
    is_enabled: bool = Field(default=True)                     # 是否启用
    signal_threshold: str = Field(default="STRONG_BUY")        # STRONG_BUY | BUY | ALL
    quiet_hours_start: Optional[int] = Field(default=None)     # 静默开始时（0-23）
    quiet_hours_end: Optional[int] = Field(default=None)       # 静默结束时（0-23）

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class NotificationLog(SQLModel, table=True):
    """推送通知日志"""
    __tablename__ = "notification_logs"
    __table_args__ = (
        Index("ix_notif_log_user_sent", "user_id", "sent_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    channel: str = Field(default="telegram")
    title: str = Field(default="")
    body: str = Field(default="")
    signal: Optional[str] = Field(default=None)                # 信号类型
    symbol: Optional[str] = Field(default=None)                # 关联股票
    sent_at: datetime = Field(default_factory=datetime.now)
    delivered: bool = Field(default=False)
    error: Optional[str] = Field(default=None)


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
        # PostgreSQL 配置：增大连接池以支持更高并发
        import os
        cpu_count = os.cpu_count() or 4
        pool_size = max(10, cpu_count * 2)  # 至少 10，推荐 2 倍 CPU 核数
        return create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=pool_size,
            max_overflow=pool_size // 2,
            pool_recycle=3600,  # 1 小时回收连接，避免连接泄漏
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
