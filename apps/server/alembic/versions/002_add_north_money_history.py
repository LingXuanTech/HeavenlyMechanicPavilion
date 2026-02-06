"""添加北向资金历史数据表

Revision ID: 002
Revises: 001
Create Date: 2026-02-06

此迁移脚本创建北向资金历史数据表，用于：
- 持久化存储每日北向资金流向数据
- 存储市场指数数据用于相关性计算
- 支持历史数据查询和分析
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级迁移 - 创建北向资金历史数据表"""
    
    # north_money_history 表
    op.create_table(
        'north_money_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('north_inflow', sa.Float(), nullable=False),
        sa.Column('sh_inflow', sa.Float(), nullable=False),
        sa.Column('sz_inflow', sa.Float(), nullable=False),
        sa.Column('cumulative_inflow', sa.Float(), nullable=False),
        sa.Column('market_index', sa.Float(), nullable=True),
        sa.Column('hs300_index', sa.Float(), nullable=True),
        sa.Column('cyb_index', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建索引
    op.create_index(op.f('ix_north_money_history_date'), 'north_money_history', ['date'], unique=True)
    op.create_index('ix_north_money_date', 'north_money_history', ['date'], unique=False)


def downgrade() -> None:
    """降级迁移 - 删除北向资金历史数据表"""
    
    # 删除索引
    op.drop_index('ix_north_money_date', table_name='north_money_history')
    op.drop_index(op.f('ix_north_money_history_date'), table_name='north_money_history')
    
    # 删除表
    op.drop_table('north_money_history')
