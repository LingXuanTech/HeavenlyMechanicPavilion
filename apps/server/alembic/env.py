"""
Alembic 环境配置文件

此文件配置 Alembic 迁移环境，包括：
- 数据库连接 URL（从 config.settings 动态获取）
- SQLModel metadata（用于自动生成迁移）
- 支持 SQLite 和 PostgreSQL 双模式
"""
import sys
from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# 将 apps/server 添加到 Python 路径，以便导入项目模块
# 这确保无论从哪个目录运行 alembic 命令都能正确导入
server_path = Path(__file__).resolve().parent.parent
if str(server_path) not in sys.path:
    sys.path.insert(0, str(server_path))

# 导入项目配置和模型
from config.settings import settings
# 导入所有模型以确保 SQLModel.metadata 包含所有表定义
# 这是自动生成迁移脚本的关键
from db.models import (
    # 基础业务模型
    Watchlist,
    AnalysisResult,
    ChatHistory,
    # AI 配置模型
    AIProvider,
    AIModelConfig,
    # Prompt 配置模型
    AgentPrompt,
    PromptVersion,
    # 用户认证模型
    User,
    OAuthAccount,
    WebAuthnCredential,
    RefreshToken,
    # 预测追踪模型
    PredictionOutcome,
    AgentPerformance,
    ModelPerformance,
    RacingAnalysisResult,
    BacktestResultRecord,
)
from sqlmodel import SQLModel

# Alembic Config 对象，提供对 .ini 文件配置值的访问
config = context.config

# 解析 Python 日志配置
# 这会设置日志记录器
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 设置 target_metadata 为 SQLModel 的 metadata
# 这使得 Alembic 能够自动检测模型变更并生成迁移脚本
target_metadata = SQLModel.metadata

# 其他配置值可以从 config 获取
# 例如: my_important_option = config.get_main_option("my_important_option")


def get_url() -> str:
    """
    获取数据库连接 URL
    
    优先使用 settings.database_url（支持 SQLite 和 PostgreSQL 双模式）
    """
    return settings.database_url


def run_migrations_offline() -> None:
    """
    在"离线"模式下运行迁移
    
    这种模式下，只需要配置 URL，不需要实际的数据库连接。
    通过调用 context.execute() 来生成 SQL 语句，而不是直接执行。
    
    适用场景：
    - 生成 SQL 脚本供 DBA 审核
    - 在无法直接连接数据库的环境中准备迁移
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # 比较类型变更（如 VARCHAR 长度变化）
        compare_type=True,
        # 比较服务器默认值
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    在"在线"模式下运行迁移
    
    这种模式下，需要创建实际的数据库连接，并在事务中执行迁移。
    
    针对不同数据库的特殊处理：
    - SQLite: 使用 NullPool（因为 SQLite 不支持多连接）
    - PostgreSQL: 使用默认连接池
    """
    # 获取数据库 URL
    url = get_url()
    
    # 根据数据库类型选择连接池
    if url.startswith("sqlite"):
        # SQLite 使用 NullPool，避免连接共享问题
        poolclass = pool.NullPool
    else:
        # PostgreSQL 等使用默认连接池
        poolclass = None
    
    # 创建配置字典
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url
    
    # 创建引擎
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=poolclass,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # 比较类型变更
            compare_type=True,
            # 比较服务器默认值
            compare_server_default=True,
            # 渲染 item 为批处理模式（SQLite 需要）
            render_as_batch=url.startswith("sqlite"),
        )

        with context.begin_transaction():
            context.run_migrations()


# 根据运行模式选择执行方式
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
