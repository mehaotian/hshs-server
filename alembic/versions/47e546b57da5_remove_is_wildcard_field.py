"""remove_is_wildcard_field

Revision ID: 47e546b57da5
Revises: rbac_improvement_001
Create Date: 2025-07-11 22:08:10.113259

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '47e546b57da5'
down_revision = 'rbac_improvement_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 移除 permissions 表的 is_wildcard 字段
    op.drop_column('permissions', 'is_wildcard')


def downgrade() -> None:
    # 恢复 permissions 表的 is_wildcard 字段
    op.add_column('permissions', sa.Column('is_wildcard', sa.Integer(), nullable=False, server_default='0', comment='是否通配符权限：1-是，0-否'))