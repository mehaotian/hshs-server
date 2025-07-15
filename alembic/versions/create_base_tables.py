"""Create base tables

Revision ID: create_base_tables
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'create_base_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建用户表
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False, comment='用户ID'),
        sa.Column('username', sa.String(length=50), nullable=False, comment='用户名'),
        sa.Column('email', sa.String(length=100), nullable=True, comment='邮箱地址'),
        sa.Column('password_hash', sa.String(length=255), nullable=False, comment='密码哈希值'),
        sa.Column('real_name', sa.String(length=100), nullable=True, comment='真实姓名'),
        sa.Column('avatar_url', sa.String(length=500), nullable=True, comment='头像URL'),
        sa.Column('phone', sa.String(length=20), nullable=True, comment='手机号码'),
        sa.Column('wechat', sa.String(length=100), nullable=True, comment='微信号'),
        sa.Column('sex', sa.Integer(), nullable=True, comment='性别：1-男，2-女，0-其他/未知'),
        sa.Column('remark', sa.Text(), nullable=True, comment='备注'),
        sa.Column('status', sa.Integer(), nullable=True, comment='用户状态：1-启用，0-禁用'),
        sa.Column('last_login_at', sa.DateTime(), nullable=True, comment='最后登录时间'),
        sa.Column('login_count', sa.Integer(), nullable=True, comment='登录次数'),
        sa.Column('settings', sa.JSON(), nullable=True, comment='用户个人设置'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        comment='用户基础信息表'
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # 创建角色表
    op.create_table('roles',
        sa.Column('id', sa.Integer(), nullable=False, comment='角色ID'),
        sa.Column('name', sa.String(length=50), nullable=False, comment='角色名称'),
        sa.Column('display_name', sa.String(length=100), nullable=True, comment='角色显示名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='角色描述'),
        sa.Column('is_system', sa.Integer(), nullable=True, comment='是否系统角色：1-是，0-否'),
        sa.Column('is_active', sa.Integer(), nullable=True, comment='是否激活：1-是，0-否'),
        sa.Column('sort_order', sa.Integer(), nullable=True, comment='排序顺序'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True, comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        comment='角色定义表'
    )
    op.create_index(op.f('ix_roles_id'), 'roles', ['id'], unique=False)

    # 创建权限表
    op.create_table('permissions',
        sa.Column('id', sa.Integer(), nullable=False, comment='权限ID'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='权限名称'),
        sa.Column('display_name', sa.String(length=100), nullable=True, comment='权限显示名称'),
        sa.Column('description', sa.Text(), nullable=True, comment='权限描述'),
        sa.Column('module', sa.String(length=50), nullable=True, comment='所属模块'),
        sa.Column('action', sa.String(length=50), nullable=True, comment='操作类型'),
        sa.Column('resource', sa.String(length=50), nullable=True, comment='资源类型'),
        sa.Column('is_system', sa.Integer(), nullable=True, comment='是否系统权限'),
        sa.Column('is_active', sa.Integer(), nullable=True, comment='是否激活：1-是，0-否'),
        sa.Column('sort_order', sa.Integer(), nullable=True, comment='排序顺序'),
        sa.Column('parent_id', sa.Integer(), nullable=True, comment='父权限ID'),
        sa.Column('level', sa.Integer(), nullable=True, comment='权限层级：0-根级，1-一级，2-二级等'),
        sa.Column('path', sa.String(length=500), nullable=True, comment='权限路径，用于快速查询子权限'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True, comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True, comment='更新时间'),
        sa.ForeignKeyConstraint(['parent_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
        comment='权限定义表'
    )
    op.create_index(op.f('ix_permissions_id'), 'permissions', ['id'], unique=False)

    # 创建用户角色关联表
    op.create_table('user_roles',
        sa.Column('id', sa.Integer(), nullable=False, comment='关联ID'),
        sa.Column('user_id', sa.Integer(), nullable=False, comment='用户ID'),
        sa.Column('role_id', sa.Integer(), nullable=False, comment='角色ID'),
        sa.Column('assigned_by', sa.Integer(), nullable=True, comment='分配者ID'),
        sa.Column('assigned_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True, comment='分配时间'),
        sa.Column('expires_at', sa.DateTime(), nullable=True, comment='过期时间'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True, comment='创建时间'),
        sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'role_id', name='uk_user_role'),
        comment='用户角色关联表'
    )
    op.create_index(op.f('ix_user_roles_id'), 'user_roles', ['id'], unique=False)

    # 创建角色权限关联表
    op.create_table('role_permissions',
        sa.Column('id', sa.Integer(), nullable=False, comment='关联ID'),
        sa.Column('role_id', sa.Integer(), nullable=False, comment='角色ID'),
        sa.Column('permission_id', sa.Integer(), nullable=False, comment='权限ID'),
        sa.Column('granted_by', sa.Integer(), nullable=True, comment='授权者ID'),
        sa.Column('granted_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True, comment='授权时间'),
        sa.Column('expires_at', sa.DateTime(), nullable=True, comment='过期时间'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True, comment='创建时间'),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role_id', 'permission_id', name='uk_role_permission'),
        comment='角色权限关联表'
    )
    op.create_index(op.f('ix_role_permissions_id'), 'role_permissions', ['id'], unique=False)


def downgrade() -> None:
    # 删除表（按依赖关系逆序）
    op.drop_table('role_permissions')
    op.drop_table('user_roles')
    op.drop_table('permissions')
    op.drop_table('roles')
    op.drop_table('users')