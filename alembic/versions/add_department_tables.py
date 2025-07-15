"""Add department tables

Revision ID: add_department_tables
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_department_tables'
down_revision = 'create_base_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建部门表
    op.create_table(
        'departments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False, comment='部门名称'),
        sa.Column('parent_id', sa.Integer(), nullable=True, comment='上级部门ID'),
        sa.Column('manager_id', sa.Integer(), nullable=True, comment='部门负责人ID'),
        sa.Column('manager_phone', sa.String(length=20), nullable=True, comment='负责人手机号'),
        sa.Column('manager_email', sa.String(length=100), nullable=True, comment='负责人邮箱'),
        sa.Column('description', sa.Text(), nullable=True, comment='部门描述'),
        sa.Column('sort_order', sa.Integer(), nullable=False, default=0, comment='排序'),
        sa.Column('status', sa.Integer(), nullable=False, default=1, comment='部门状态：1-正常，2-停用'),
        sa.Column('level', sa.Integer(), nullable=False, default=1, comment='部门层级'),
        sa.Column('path', sa.String(length=500), nullable=True, comment='部门路径'),
        sa.Column('remarks', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='更新时间'),
        sa.Column('created_by', sa.Integer(), nullable=True, comment='创建人ID'),
        sa.Column('updated_by', sa.Integer(), nullable=True, comment='更新人ID'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['parent_id'], ['departments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['manager_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        comment='部门表'
    )
    
    # 创建部门成员表
    op.create_table(
        'department_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('department_id', sa.Integer(), nullable=False, comment='部门ID'),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='用户ID'),
        sa.Column('position', sa.String(length=100), nullable=True, comment='职位'),
        sa.Column('is_manager', sa.Boolean(), nullable=False, default=False, comment='是否为负责人'),
        sa.Column('status', sa.Integer(), nullable=False, default=1, comment='成员状态：1-正常，2-离职'),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='加入时间'),
        sa.Column('left_at', sa.DateTime(timezone=True), nullable=True, comment='离职时间'),
        sa.Column('remarks', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        comment='部门成员表'
    )
    
    # 创建索引
    # 部门表索引
    op.create_index('idx_departments_parent_id', 'departments', ['parent_id'])
    op.create_index('idx_departments_manager_id', 'departments', ['manager_id'])
    op.create_index('idx_departments_status', 'departments', ['status'])
    op.create_index('idx_departments_level', 'departments', ['level'])
    op.create_index('idx_departments_sort_order', 'departments', ['sort_order'])
    op.create_index('idx_departments_name', 'departments', ['name'])
    op.create_index('idx_departments_path', 'departments', ['path'])
    op.create_index('idx_departments_created_at', 'departments', ['created_at'])
    
    # 部门成员表索引
    op.create_index('idx_department_members_dept_id', 'department_members', ['department_id'])
    op.create_index('idx_department_members_user_id', 'department_members', ['user_id'])
    op.create_index('idx_department_members_status', 'department_members', ['status'])
    op.create_index('idx_department_members_is_manager', 'department_members', ['is_manager'])
    op.create_index('idx_department_members_joined_at', 'department_members', ['joined_at'])
    
    # 复合索引
    op.create_index('idx_departments_parent_status', 'departments', ['parent_id', 'status'])
    op.create_index('idx_departments_level_sort', 'departments', ['level', 'sort_order'])
    op.create_index('idx_department_members_dept_status', 'department_members', ['department_id', 'status'])
    op.create_index('idx_department_members_user_status', 'department_members', ['user_id', 'status'])
    
    # 唯一约束
    op.create_index('idx_departments_name_parent_unique', 'departments', ['name', 'parent_id'], unique=True)
    op.create_index('idx_department_members_dept_user_unique', 'department_members', ['department_id', 'user_id'], unique=True)
    
    # SQLite不支持触发器函数，updated_at字段将在应用层更新
    
    # SQLite不支持ALTER约束操作，检查约束将在应用层实现


def downgrade() -> None:
    # 删除表（会自动删除相关的索引和约束）
    op.drop_table('department_members')
    op.drop_table('departments')