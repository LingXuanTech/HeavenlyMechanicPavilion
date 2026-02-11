"""为 analysisresult 增加 user_id 审计字段

Revision ID: 003
Revises: 002
Create Date: 2026-02-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级迁移 - 为 analysisresult 添加 user_id 审计字段"""
    with op.batch_alter_table('analysisresult') as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.create_index('ix_analysisresult_user_id', ['user_id'], unique=False)


def downgrade() -> None:
    """降级迁移 - 删除 analysisresult.user_id"""
    with op.batch_alter_table('analysisresult') as batch_op:
        batch_op.drop_index('ix_analysisresult_user_id')
        batch_op.drop_column('user_id')
