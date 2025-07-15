"""merge permission and user changes

Revision ID: 654bd06b9a18
Revises: remove_is_category_001, rename_bio_to_remark
Create Date: 2025-07-15 11:50:20.150676

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '654bd06b9a18'
down_revision = ('remove_is_category_001', 'rename_bio_to_remark')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass