"""rename bio to remark

Revision ID: rename_bio_to_remark
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'rename_bio_to_remark'
down_revision = 'change_sex_field_to_integer'
branch_labels = None
depends_on = None


def upgrade():
    """重命名 bio 字段为 remark"""
    # 注意：create_base_tables.py中已经定义了remark字段，不需要重命名
    pass


def downgrade():
    """回滚：重命名 remark 字段为 bio"""
    # 注意：create_base_tables.py中已经定义了remark字段，不需要重命名
    pass