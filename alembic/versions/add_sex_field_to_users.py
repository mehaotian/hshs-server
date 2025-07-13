"""add sex field to users

Revision ID: add_sex_field_to_users
Revises: rbac_system_improvement
Create Date: 2024-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_sex_field_to_users'
down_revision = '47e546b57da5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """添加性别字段到用户表"""
    # 添加性别字段
    op.add_column('users', sa.Column('sex', sa.String(10), nullable=True, comment='性别：male-男，female-女，other-其他'))


def downgrade() -> None:
    """移除性别字段"""
    # 删除性别字段
    op.drop_column('users', 'sex')