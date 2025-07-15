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
    # is_wildcard字段在rbac_system_improvement.py中已经被移除
    # 这里不需要再删除
    pass


def downgrade() -> None:
    # 由于upgrade中没有删除字段，downgrade中也不需要添加
    pass