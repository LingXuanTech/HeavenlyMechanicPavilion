"""add_database_optimization_indexes

Revision ID: 5951c803aff7
Revises: c1e38cfe113f
Create Date: 2025-11-03 06:45:52.628500

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '5951c803aff7'
down_revision: Union[str, None] = 'c1e38cfe113f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add database optimization indexes for improved query performance."""
    
    # Use batch mode for SQLite compatibility when adding foreign keys
    with op.batch_alter_table('trades', schema=None) as batch_op:
        batch_op.add_column(sa.Column('session_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key('fk_trades_session_id', 'trading_sessions', ['session_id'], ['id'])
        batch_op.create_index(batch_op.f('ix_trades_session_id'), ['session_id'], unique=False)
    
    # Add composite index on positions(portfolio_id, symbol) for faster lookups
    # This is crucial for queries like "get position for symbol X in portfolio Y"
    op.create_index('ix_positions_portfolio_symbol', 'positions', ['portfolio_id', 'symbol'], unique=False)
    
    # Add user_id to portfolios for multi-user support (if not already exists)
    # First check if user table exists, if not, we'll skip this for now
    # This will be useful when multi-user support is added
    # Commenting out for now as user table may not exist yet
    # op.add_column('portfolios', sa.Column('user_id', sa.Integer(), nullable=True))
    # op.create_foreign_key('fk_portfolios_user_id', 'portfolios', 'users', ['user_id'], ['id'])
    # op.create_index(op.f('ix_portfolios_user_id'), 'portfolios', ['user_id'], unique=False)
    
    # Add composite index on trades(portfolio_id, status) for filtering trades by portfolio and status
    op.create_index('ix_trades_portfolio_status', 'trades', ['portfolio_id', 'status'], unique=False)
    
    # Add composite index on trades(portfolio_id, created_at) for time-based queries
    op.create_index('ix_trades_portfolio_created', 'trades', ['portfolio_id', 'created_at'], unique=False)


def downgrade() -> None:
    """Remove database optimization indexes."""
    
    # Remove composite indexes
    op.drop_index('ix_trades_portfolio_created', table_name='trades')
    op.drop_index('ix_trades_portfolio_status', table_name='trades')
    op.drop_index('ix_positions_portfolio_symbol', table_name='positions')
    
    # Use batch mode for SQLite compatibility when removing foreign keys
    with op.batch_alter_table('trades', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_trades_session_id'))
        batch_op.drop_constraint('fk_trades_session_id', type_='foreignkey')
        batch_op.drop_column('session_id')
    
    # Commented out user_id removal (corresponding to upgrade)
    # op.drop_index(op.f('ix_portfolios_user_id'), table_name='portfolios')
    # op.drop_constraint('fk_portfolios_user_id', 'portfolios', type_='foreignkey')
    # op.drop_column('portfolios', 'user_id')
