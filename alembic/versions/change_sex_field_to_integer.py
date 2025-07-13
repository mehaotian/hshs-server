"""change sex field to integer

Revision ID: change_sex_field_to_integer
Revises: add_sex_field_to_users
Create Date: 2025-07-13 11:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'change_sex_field_to_integer'
down_revision = 'add_sex_field_to_users'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 首先添加新的整数类型字段
    op.add_column('users', sa.Column('sex_new', sa.Integer(), nullable=True, comment='性别：1-男，2-女，0-其他/未知'))
    
    # 迁移数据：将字符串值转换为整数值
    op.execute("""
        UPDATE users 
        SET sex_new = CASE 
            WHEN sex = 'male' THEN 1
            WHEN sex = 'female' THEN 2
            WHEN sex = 'other' THEN 0
            ELSE NULL
        END
    """)
    
    # 删除旧的字符串字段
    op.drop_column('users', 'sex')
    
    # 重命名新字段为原字段名
    op.alter_column('users', 'sex_new', new_column_name='sex')


def downgrade() -> None:
    # 添加旧的字符串类型字段
    op.add_column('users', sa.Column('sex_old', sa.String(10), nullable=True, comment='性别：male-男，female-女，other-其他'))
    
    # 迁移数据：将整数值转换为字符串值
    op.execute("""
        UPDATE users 
        SET sex_old = CASE 
            WHEN sex = 1 THEN 'male'
            WHEN sex = 2 THEN 'female'
            WHEN sex = 0 THEN 'other'
            ELSE NULL
        END
    """)
    
    # 删除新的整数字段
    op.drop_column('users', 'sex')
    
    # 重命名旧字段为原字段名
    op.alter_column('users', 'sex_old', new_column_name='sex')