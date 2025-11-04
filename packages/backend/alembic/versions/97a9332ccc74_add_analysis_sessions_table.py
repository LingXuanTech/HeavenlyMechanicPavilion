"""add_analysis_sessions_table

Revision ID: 97a9332ccc74
Revises: 5951c803aff7
Create Date: 2025-11-04 03:51:22.107978

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '97a9332ccc74'
down_revision: Union[str, None] = '5951c803aff7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create analysis_sessions table."""
    op.create_table(
        'analysis_sessions',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('ticker', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('trade_date', sa.String(length=10), nullable=False),
        sa.Column('selected_analysts_json', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('summary_json', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_analysis_sessions_ticker'), 'analysis_sessions', ['ticker'], unique=False)
    op.create_index(op.f('ix_analysis_sessions_status'), 'analysis_sessions', ['status'], unique=False)
    op.create_index(op.f('ix_analysis_sessions_created_at'), 'analysis_sessions', ['created_at'], unique=False)
    op.create_index(op.f('ix_analysis_sessions_updated_at'), 'analysis_sessions', ['updated_at'], unique=False)


def downgrade() -> None:
    """Drop analysis_sessions table."""
    op.drop_index(op.f('ix_analysis_sessions_updated_at'), table_name='analysis_sessions')
    op.drop_index(op.f('ix_analysis_sessions_created_at'), table_name='analysis_sessions')
    op.drop_index(op.f('ix_analysis_sessions_status'), table_name='analysis_sessions')
    op.drop_index(op.f('ix_analysis_sessions_ticker'), table_name='analysis_sessions')
    op.drop_table('analysis_sessions')
