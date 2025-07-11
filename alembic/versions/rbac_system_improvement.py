"""RBAC权限系统改进

Revision ID: rbac_improvement_001
Revises: add_position_type_to_department_members
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'rbac_improvement_001'
down_revision = 'add_position_type'
branch_labels = None
depends_on = None


def upgrade():
    """升级数据库结构"""
    
    # 1. 为permissions表添加新字段（先设为可空）
    op.add_column('permissions', sa.Column('is_wildcard', sa.Integer(), nullable=True, comment='是否通配符权限：1-是，0-否'))
    op.add_column('permissions', sa.Column('is_active', sa.Integer(), nullable=True, comment='是否激活：1-是，0-否'))
    
    # 更新现有数据的默认值
    connection = op.get_bind()
    connection.execute(sa.text("UPDATE permissions SET is_wildcard = 0 WHERE is_wildcard IS NULL"))
    connection.execute(sa.text("UPDATE permissions SET is_active = 1 WHERE is_active IS NULL"))
    
    # 设置字段为NOT NULL
    op.alter_column('permissions', 'is_wildcard', nullable=False)
    op.alter_column('permissions', 'is_active', nullable=False)
    
    # 2. 为roles表添加新字段（先设为可空）
    op.add_column('roles', sa.Column('is_active', sa.Integer(), nullable=True, comment='是否激活：1-是，0-否'))
    
    # 更新现有数据的默认值
    connection.execute(sa.text("UPDATE roles SET is_active = 1 WHERE is_active IS NULL"))
    
    # 设置字段为NOT NULL
    op.alter_column('roles', 'is_active', nullable=False)
    
    # 3. 创建role_permissions关联表
    op.create_table('role_permissions',
        sa.Column('id', sa.Integer(), nullable=False, comment='关联ID'),
        sa.Column('role_id', sa.Integer(), nullable=False, comment='角色ID'),
        sa.Column('permission_id', sa.Integer(), nullable=False, comment='权限ID'),
        sa.Column('granted_by', sa.Integer(), nullable=True, comment='授权者ID'),
        sa.Column('granted_at', sa.DateTime(), nullable=False, default=sa.func.now(), comment='授权时间'),
        sa.Column('expires_at', sa.DateTime(), nullable=True, comment='过期时间'),
        sa.Column('created_at', sa.DateTime(), nullable=False, default=sa.func.now(), comment='创建时间'),
        sa.ForeignKeyConstraint(['permission_id'], ['permissions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['granted_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role_id', 'permission_id', name='uk_role_permission'),
        comment='角色权限关联表'
    )
    
    # 4. 创建索引
    op.create_index('idx_role_permissions_role_id', 'role_permissions', ['role_id'])
    op.create_index('idx_role_permissions_permission_id', 'role_permissions', ['permission_id'])
    op.create_index('idx_permissions_is_active', 'permissions', ['is_active'])
    op.create_index('idx_roles_is_active', 'roles', ['is_active'])
    
    # 5. 迁移现有数据：将roles表中的permissions JSON数据迁移到role_permissions表
    # 注意：这里需要根据实际的JSON结构进行调整
    
    # 获取所有角色和权限数据
    roles_result = connection.execute(sa.text("SELECT id, name, permissions FROM roles WHERE permissions IS NOT NULL"))
    permissions_result = connection.execute(sa.text("SELECT id, name FROM permissions"))
    
    # 创建权限名称到ID的映射
    permission_name_to_id = {}
    for perm in permissions_result:
        permission_name_to_id[perm.name] = perm.id
    
    # 迁移角色权限数据
    import json
    for role in roles_result:
        if role.permissions:
            try:
                # 解析JSON权限数据
                if isinstance(role.permissions, str):
                    permissions_data = json.loads(role.permissions)
                else:
                    permissions_data = role.permissions
                
                # 提取权限列表
                if isinstance(permissions_data, list):
                    permission_names = permissions_data
                elif isinstance(permissions_data, dict) and 'permissions' in permissions_data:
                    permission_names = permissions_data['permissions']
                else:
                    continue
                
                # 为每个权限创建关联记录
                for perm_name in permission_names:
                    if perm_name in permission_name_to_id:
                        connection.execute(sa.text(
                            "INSERT INTO role_permissions (role_id, permission_id, granted_at, created_at) "
                            "VALUES (:role_id, :permission_id, NOW(), NOW())"
                        ), {
                            'role_id': role.id,
                            'permission_id': permission_name_to_id[perm_name]
                        })
            except (json.JSONDecodeError, KeyError, TypeError):
                # 如果JSON解析失败，跳过该角色
                continue
    
    # 6. 删除roles表的permissions字段
    op.drop_column('roles', 'permissions')
    
    # 7. 更新通配符权限
    connection.execute(sa.text(
        "UPDATE permissions SET is_wildcard = 1 WHERE name LIKE '%*%'"
    ))


def downgrade():
    """降级数据库结构"""
    
    # 1. 重新添加roles表的permissions字段
    op.add_column('roles', sa.Column('permissions', mysql.JSON(), nullable=True, comment='权限配置JSON'))
    
    # 2. 迁移role_permissions数据回roles表的permissions字段
    connection = op.get_bind()
    
    # 获取所有角色及其权限
    result = connection.execute(sa.text(
        "SELECT r.id, r.name, GROUP_CONCAT(p.name) as permission_names "
        "FROM roles r "
        "LEFT JOIN role_permissions rp ON r.id = rp.role_id "
        "LEFT JOIN permissions p ON rp.permission_id = p.id "
        "GROUP BY r.id, r.name"
    ))
    
    # 更新roles表的permissions字段
    import json
    for role in result:
        if role.permission_names:
            permission_list = role.permission_names.split(',')
            permissions_json = json.dumps({'permissions': permission_list})
            connection.execute(sa.text(
                "UPDATE roles SET permissions = :permissions WHERE id = :role_id"
            ), {
                'permissions': permissions_json,
                'role_id': role.id
            })
    
    # 3. 删除索引
    op.drop_index('idx_roles_is_active', 'roles')
    op.drop_index('idx_permissions_is_active', 'permissions')
    op.drop_index('idx_role_permissions_permission_id', 'role_permissions')
    op.drop_index('idx_role_permissions_role_id', 'role_permissions')
    
    # 4. 删除role_permissions表
    op.drop_table('role_permissions')
    
    # 5. 删除新添加的字段
    op.drop_column('roles', 'is_active')
    op.drop_column('permissions', 'is_active')
    op.drop_column('permissions', 'is_wildcard')