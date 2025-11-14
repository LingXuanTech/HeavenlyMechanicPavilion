"""Add session_events table for event persistence

Revision ID: add_session_events_001
Revises: 
Create Date: 2025-11-13 11:34:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_session_events_001'
down_revision = None  # Update this to the latest migration ID
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add session_events table."""
    op.create_table(
        'session_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('sequence_number', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('agent_name', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['session_id'], ['analysis_sessions.id'], ondelete='CASCADE'),
    )
    
    # Create indexes for efficient queries
    op.create_index('ix_session_events_session_id', 'session_events', ['session_id'])
    op.create_index('ix_session_events_event_type', 'session_events', ['event_type'])
    op.create_index('ix_session_events_sequence_number', 'session_events', ['sequence_number'])
    op.create_index('ix_session_events_timestamp', 'session_events', ['timestamp'])
    op.create_index('ix_session_events_agent_name', 'session_events', ['agent_name'])
    
    # Composite indexes for common query patterns
    op.create_index('idx_session_events_session_seq', 'session_events', ['session_id', 'sequence_number'])
    op.create_index('idx_session_events_session_time', 'session_events', ['session_id', 'timestamp'])


def downgrade() -> None:
    """Remove session_events table."""
    op.drop_index('idx_session_events_session_time', table_name='session_events')
    op.drop_index('idx_session_events_session_seq', table_name='session_events')
    op.drop_index('ix_session_events_agent_name', table_name='session_events')
    op.drop_index('ix_session_events_timestamp', table_name='session_events')
    op.drop_index('ix_session_events_sequence_number', table_name='session_events')
    op.drop_index('ix_session_events_event_type', table_name='session_events')
    op.drop_index('ix_session_events_session_id', table_name='session_events')
    op.drop_table('session_events')