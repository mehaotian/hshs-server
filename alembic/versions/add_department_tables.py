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
down_revision = None  # 请根据实际情况修改为上一个迁移的revision
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
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='更新时间'),
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
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='加入时间'),
        sa.Column('left_at', sa.DateTime(timezone=True), nullable=True, comment='离职时间'),
        sa.Column('remarks', sa.Text(), nullable=True, comment='备注'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='更新时间'),
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
    
    # 创建更新时间触发器函数（如果不存在）
    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ language 'plpgsql';
    """)
    
    # 为部门表创建更新时间触发器
    op.execute("""
        CREATE TRIGGER update_departments_updated_at
            BEFORE UPDATE ON departments
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # 为部门成员表创建更新时间触发器
    op.execute("""
        CREATE TRIGGER update_department_members_updated_at
            BEFORE UPDATE ON department_members
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)
    
    # 添加检查约束
    op.create_check_constraint(
        'ck_departments_status',
        'departments',
        'status IN (1, 2)'
    )
    
    op.create_check_constraint(
        'ck_departments_level',
        'departments',
        'level >= 1 AND level <= 10'
    )
    
    op.create_check_constraint(
        'ck_departments_sort_order',
        'departments',
        'sort_order >= 0'
    )
    
    op.create_check_constraint(
        'ck_department_members_status',
        'department_members',
        'status IN (1, 2)'
    )
    
    # 防止部门自引用
    op.create_check_constraint(
        'ck_departments_no_self_reference',
        'departments',
        'id != parent_id'
    )


def downgrade() -> None:
    # 删除触发器
    op.execute('DROP TRIGGER IF EXISTS update_department_members_updated_at ON department_members;')
    op.execute('DROP TRIGGER IF EXISTS update_departments_updated_at ON departments;')
    
    # 删除表（会自动删除相关的索引和约束）
    op.drop_table('department_members')
    op.drop_table('departments')
    
    # 注意：这里不删除触发器函数，因为其他表可能也在使用
    # 如果确定没有其他表使用，可以取消注释下面的语句
    # op.execute('DROP FUNCTION IF EXISTS update_updated_at_column();')