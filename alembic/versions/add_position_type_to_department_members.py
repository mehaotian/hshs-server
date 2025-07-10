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
    # 创建职位类型枚举
    position_type_enum = postgresql.ENUM(
        'MEMBER', 'DEPUTY_MANAGER', 'MANAGER',
        name='positiontype',
        create_type=False
    )
    position_type_enum.create(op.get_bind(), checkfirst=True)
    
    # 添加position_type字段
    op.add_column('department_members', 
                  sa.Column('position_type', 
                           postgresql.ENUM('MEMBER', 'DEPUTY_MANAGER', 'MANAGER', name='positiontype'),
                           nullable=False,
                           server_default='MEMBER',
                           comment='职位类型：MEMBER-普通成员，DEPUTY_MANAGER-副部长，MANAGER-部长'))
    
    # 根据现有is_manager字段初始化position_type值
    op.execute("""
        UPDATE department_members 
        SET position_type = CASE 
            WHEN is_manager = true THEN 'MANAGER'::positiontype
            ELSE 'MEMBER'::positiontype
        END
    """)
    
    # 添加唯一约束：每个部门只能有一个部长
    op.create_index('idx_department_unique_manager', 'department_members', 
                    ['department_id'], 
                    unique=True,
                    postgresql_where=sa.text("position_type = 'MANAGER' AND status = 1"))
    
    # 添加索引优化查询性能
    op.create_index('idx_department_members_position_type', 'department_members', ['position_type'])
    op.create_index('idx_department_members_dept_position', 'department_members', ['department_id', 'position_type'])


def downgrade():
    # 删除索引
    op.drop_index('idx_department_members_dept_position')
    op.drop_index('idx_department_members_position_type')
    op.drop_index('idx_department_unique_manager')
    
    # 删除字段
    op.drop_column('department_members', 'position_type')
    
    # 删除枚举类型
    position_type_enum = postgresql.ENUM('MEMBER', 'DEPUTY_MANAGER', 'MANAGER', name='positiontype')
    position_type_enum.drop(op.get_bind(), checkfirst=True)