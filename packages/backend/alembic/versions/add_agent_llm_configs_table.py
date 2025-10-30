"""add agent_llm_configs table

Revision ID: add_agent_llm_configs
Revises: add_trading_session_risk
Create Date: 2025-01-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'add_agent_llm_configs'
down_revision: Union[str, None] = 'add_trading_session_risk'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create agent_llm_configs table."""
    op.create_table(
        'agent_llm_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('provider', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('model_name', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=False),
        sa.Column('temperature', sa.Float(), nullable=False, server_default='0.7'),
        sa.Column('max_tokens', sa.Integer(), nullable=True),
        sa.Column('top_p', sa.Float(), nullable=True),
        sa.Column('api_key_encrypted', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
        sa.Column('fallback_provider', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=True),
        sa.Column('fallback_model', sqlmodel.sql.sqltypes.AutoString(length=100), nullable=True),
        sa.Column('cost_per_1k_input_tokens', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('cost_per_1k_output_tokens', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('metadata_json', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(['agent_id'], ['agent_configs.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_agent_llm_configs_agent_id'), 'agent_llm_configs', ['agent_id'], unique=False)
    op.create_index(op.f('ix_agent_llm_configs_enabled'), 'agent_llm_configs', ['enabled'], unique=False)
    op.create_index(op.f('ix_agent_llm_configs_provider'), 'agent_llm_configs', ['provider'], unique=False)


def downgrade() -> None:
    """Drop agent_llm_configs table."""
    op.drop_index(op.f('ix_agent_llm_configs_provider'), table_name='agent_llm_configs')
    op.drop_index(op.f('ix_agent_llm_configs_enabled'), table_name='agent_llm_configs')
    op.drop_index(op.f('ix_agent_llm_configs_agent_id'), table_name='agent_llm_configs')
    op.drop_table('agent_llm_configs')
