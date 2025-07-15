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
    # 注意：sex字段已经在create_base_tables.py中定义为Integer类型
    # 这里不需要再添加
    pass


def downgrade() -> None:
    """移除性别字段"""
    # 注意：sex字段在create_base_tables.py中定义，这里不删除
    pass