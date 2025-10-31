"""Add agent plugin fields to agent_config

Revision ID: plugin_agent_fields
Revises: ac7a9a8391bc
Create Date: 2024-01-15 00:00:00.000000

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = 'plugin_agent_fields'
down_revision = 'ac7a9a8391bc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Add new columns to agent_configs table
    op.add_column('agent_configs', sa.Column('role', sa.String(length=50), nullable=False, server_default='analyst'))
    op.add_column('agent_configs', sa.Column('llm_type', sa.String(length=20), nullable=False, server_default='quick'))
    op.add_column('agent_configs', sa.Column('prompt_template', sa.Text(), nullable=True))
    op.add_column('agent_configs', sa.Column('capabilities_json', sa.Text(), nullable=True))
    op.add_column('agent_configs', sa.Column('required_tools_json', sa.Text(), nullable=True))
    op.add_column('agent_configs', sa.Column('requires_memory', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('agent_configs', sa.Column('memory_name', sa.String(length=100), nullable=True))
    op.add_column('agent_configs', sa.Column('is_reserved', sa.Boolean(), nullable=False, server_default='true'))
    op.add_column('agent_configs', sa.Column('slot_name', sa.String(length=50), nullable=True))
    op.add_column('agent_configs', sa.Column('version', sa.String(length=20), nullable=False, server_default='1.0.0'))
    
    # Create indexes
    op.create_index(op.f('ix_agent_configs_role'), 'agent_configs', ['role'], unique=False)
    op.create_index(op.f('ix_agent_configs_slot_name'), 'agent_configs', ['slot_name'], unique=False)


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop indexes
    op.drop_index(op.f('ix_agent_configs_slot_name'), table_name='agent_configs')
    op.drop_index(op.f('ix_agent_configs_role'), table_name='agent_configs')
    
    # Drop columns
    op.drop_column('agent_configs', 'version')
    op.drop_column('agent_configs', 'slot_name')
    op.drop_column('agent_configs', 'is_reserved')
    op.drop_column('agent_configs', 'memory_name')
    op.drop_column('agent_configs', 'requires_memory')
    op.drop_column('agent_configs', 'required_tools_json')
    op.drop_column('agent_configs', 'capabilities_json')
    op.drop_column('agent_configs', 'prompt_template')
    op.drop_column('agent_configs', 'llm_type')
    op.drop_column('agent_configs', 'role')
