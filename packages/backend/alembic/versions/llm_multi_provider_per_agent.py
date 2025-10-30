"""Add tables for agent-specific LLM configuration and usage tracking.

Revision ID: llm_multi_provider
Revises: add_trading_session_risk
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "llm_multi_provider"
down_revision: Union[str, None] = "add_trading_session_risk"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply schema changes for LLM configuration."""
    op.create_table(
        "agent_llm_configs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=False),
        sa.Column("provider", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("model", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0.7"),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column("top_p", sa.Float(), nullable=True),
        sa.Column("api_key_encrypted", sqlmodel.sql.sqltypes.AutoString(length=1024), nullable=True),
        sa.Column("fallback_provider", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column("fallback_model", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column("cost_per_1k_tokens", sa.Float(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_configs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", name="uq_agent_llm_configs_agent_id"),
    )
    op.create_index(
        op.f("ix_agent_llm_configs_agent_id"),
        "agent_llm_configs",
        ["agent_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_agent_llm_configs_provider"),
        "agent_llm_configs",
        ["provider"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_llm_configs_enabled"),
        "agent_llm_configs",
        ["enabled"],
        unique=False,
    )

    op.create_table(
        "agent_llm_usage",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("agent_id", sa.Integer(), nullable=True),
        sa.Column("llm_config_id", sa.Integer(), nullable=True),
        sa.Column("agent_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("provider", sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column("model", sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("cost", sa.Float(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("error_type", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("error_message", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["agent_id"], ["agent_configs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["llm_config_id"], ["agent_llm_configs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_llm_usage_agent_id"),
        "agent_llm_usage",
        ["agent_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_llm_usage_llm_config_id"),
        "agent_llm_usage",
        ["llm_config_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_llm_usage_agent_name"),
        "agent_llm_usage",
        ["agent_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_llm_usage_provider"),
        "agent_llm_usage",
        ["provider"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_llm_usage_success"),
        "agent_llm_usage",
        ["success"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_llm_usage_created_at"),
        "agent_llm_usage",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Revert schema changes."""
    op.drop_index(op.f("ix_agent_llm_usage_created_at"), table_name="agent_llm_usage")
    op.drop_index(op.f("ix_agent_llm_usage_success"), table_name="agent_llm_usage")
    op.drop_index(op.f("ix_agent_llm_usage_provider"), table_name="agent_llm_usage")
    op.drop_index(op.f("ix_agent_llm_usage_agent_name"), table_name="agent_llm_usage")
    op.drop_index(op.f("ix_agent_llm_usage_llm_config_id"), table_name="agent_llm_usage")
    op.drop_index(op.f("ix_agent_llm_usage_agent_id"), table_name="agent_llm_usage")
    op.drop_table("agent_llm_usage")

    op.drop_index(op.f("ix_agent_llm_configs_enabled"), table_name="agent_llm_configs")
    op.drop_index(op.f("ix_agent_llm_configs_provider"), table_name="agent_llm_configs")
    op.drop_index(op.f("ix_agent_llm_configs_agent_id"), table_name="agent_llm_configs")
    op.drop_table("agent_llm_configs")
