"""添加职位类型字段到部门成员表

Revision ID: add_position_type
Revises: add_department_tables
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_position_type'
down_revision = 'add_department_tables'
branch_labels = None
depends_on = None


def upgrade():
    # SQLite兼容：使用VARCHAR代替ENUM
    # 添加position_type字段
    op.add_column('department_members', 
                  sa.Column('position_type', 
                           sa.String(20),
                           nullable=False,
                           server_default='MEMBER',
                           comment='职位类型：MEMBER-普通成员，DEPUTY_MANAGER-副部长，MANAGER-部长'))
    
    # 根据现有is_manager字段初始化position_type值
    op.execute("""
        UPDATE department_members 
        SET position_type = CASE 
            WHEN is_manager = 1 THEN 'MANAGER'
            ELSE 'MEMBER'
        END
    """)
    
    # 添加索引优化查询性能
    op.create_index('idx_department_members_position_type', 'department_members', ['position_type'])
    op.create_index('idx_department_members_dept_position', 'department_members', ['department_id', 'position_type'])


def downgrade():
    # 删除索引
    op.drop_index('idx_department_members_dept_position')
    op.drop_index('idx_department_members_position_type')
    
    # 删除字段
    op.drop_column('department_members', 'position_type')