"""remove permission is_category field

Revision ID: remove_is_category_001
Revises: permission_classification_001
Create Date: 2025-01-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'remove_is_category_001'
down_revision = 'permission_classification_001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """升级数据库结构 - 移除权限分类概念"""
    
    # 移除 is_category 字段
    op.drop_column('permissions', 'is_category')
    
    print("已移除权限表的 is_category 字段，权限系统已转换为层级结构")


def downgrade() -> None:
    """降级数据库结构 - 恢复权限分类概念"""
    
    # 重新添加 is_category 字段
    op.add_column('permissions', sa.Column('is_category', sa.Integer(), default=0, comment='是否为分类：1-是，0-否'))
    
    print("已恢复权限表的 is_category 字段")