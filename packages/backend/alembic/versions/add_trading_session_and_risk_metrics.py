"""add trading session and risk metrics

Revision ID: add_trading_session_risk
Revises: plugin_agent_fields
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'add_trading_session_risk'
down_revision: Union[str, None] = 'plugin_agent_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create trading_sessions table
    op.create_table(
        'trading_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('session_type', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.String(length=1000), nullable=True),
        sa.Column('max_position_size', sa.Float(), nullable=True),
        sa.Column('max_portfolio_exposure', sa.Float(), nullable=True),
        sa.Column('stop_loss_percentage', sa.Float(), nullable=True),
        sa.Column('take_profit_percentage', sa.Float(), nullable=True),
        sa.Column('starting_capital', sa.Float(), nullable=False),
        sa.Column('current_capital', sa.Float(), nullable=False),
        sa.Column('total_pnl', sa.Float(), nullable=False),
        sa.Column('total_trades', sa.Integer(), nullable=False),
        sa.Column('winning_trades', sa.Integer(), nullable=False),
        sa.Column('losing_trades', sa.Integer(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('stopped_at', sa.DateTime(), nullable=True),
        sa.Column('metadata_json', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_trading_sessions_portfolio_id'), 'trading_sessions', ['portfolio_id'], unique=False)
    op.create_index(op.f('ix_trading_sessions_session_type'), 'trading_sessions', ['session_type'], unique=False)
    op.create_index(op.f('ix_trading_sessions_started_at'), 'trading_sessions', ['started_at'], unique=False)
    op.create_index(op.f('ix_trading_sessions_status'), 'trading_sessions', ['status'], unique=False)

    # Create risk_metrics table
    op.create_table(
        'risk_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=True),
        sa.Column('var_1day_95', sa.Float(), nullable=True),
        sa.Column('var_1day_99', sa.Float(), nullable=True),
        sa.Column('var_5day_95', sa.Float(), nullable=True),
        sa.Column('var_5day_99', sa.Float(), nullable=True),
        sa.Column('portfolio_value', sa.Float(), nullable=False),
        sa.Column('portfolio_volatility', sa.Float(), nullable=True),
        sa.Column('sharpe_ratio', sa.Float(), nullable=True),
        sa.Column('max_drawdown', sa.Float(), nullable=True),
        sa.Column('largest_position_weight', sa.Float(), nullable=True),
        sa.Column('top5_concentration', sa.Float(), nullable=True),
        sa.Column('number_of_positions', sa.Integer(), nullable=False),
        sa.Column('total_exposure', sa.Float(), nullable=False),
        sa.Column('long_exposure', sa.Float(), nullable=False),
        sa.Column('short_exposure', sa.Float(), nullable=False),
        sa.Column('net_exposure', sa.Float(), nullable=False),
        sa.Column('market_beta', sa.Float(), nullable=True),
        sa.Column('correlation_to_spy', sa.Float(), nullable=True),
        sa.Column('measured_at', sa.DateTime(), nullable=False),
        sa.Column('metadata_json', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ),
        sa.ForeignKeyConstraint(['session_id'], ['trading_sessions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_risk_metrics_measured_at'), 'risk_metrics', ['measured_at'], unique=False)
    op.create_index(op.f('ix_risk_metrics_portfolio_id'), 'risk_metrics', ['portfolio_id'], unique=False)
    op.create_index(op.f('ix_risk_metrics_session_id'), 'risk_metrics', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_risk_metrics_session_id'), table_name='risk_metrics')
    op.drop_index(op.f('ix_risk_metrics_portfolio_id'), table_name='risk_metrics')
    op.drop_index(op.f('ix_risk_metrics_measured_at'), table_name='risk_metrics')
    op.drop_table('risk_metrics')
    op.drop_index(op.f('ix_trading_sessions_status'), table_name='trading_sessions')
    op.drop_index(op.f('ix_trading_sessions_started_at'), table_name='trading_sessions')
    op.drop_index(op.f('ix_trading_sessions_session_type'), table_name='trading_sessions')
    op.drop_index(op.f('ix_trading_sessions_portfolio_id'), table_name='trading_sessions')
    op.drop_table('trading_sessions')
