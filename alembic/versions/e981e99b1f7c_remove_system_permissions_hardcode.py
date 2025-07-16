"""remove_system_permissions_hardcode

Revision ID: e981e99b1f7c
Revises: 654bd06b9a18
Create Date: 2025-07-16 10:15:20.947190

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'e981e99b1f7c'
down_revision = '654bd06b9a18'
branch_labels = None
depends_on = None

# 系统权限数据定义
SYSTEM_PERMISSIONS_DATA = [
    # 用户管理
    {'name': 'user:create', 'display_name': '创建用户', 'module': 'user', 'action': 'create'},
    {'name': 'user:read', 'display_name': '查看用户', 'module': 'user', 'action': 'read'},
    {'name': 'user:update', 'display_name': '更新用户', 'module': 'user', 'action': 'update'},
    {'name': 'user:delete', 'display_name': '删除用户', 'module': 'user', 'action': 'delete'},
    {'name': 'user:assign_role', 'display_name': '分配角色', 'module': 'user', 'action': 'assign_role'},
    
    # 角色管理
    {'name': 'role:create', 'display_name': '创建角色', 'module': 'role', 'action': 'create'},
    {'name': 'role:read', 'display_name': '查看角色', 'module': 'role', 'action': 'read'},
    {'name': 'role:update', 'display_name': '更新角色', 'module': 'role', 'action': 'update'},
    {'name': 'role:delete', 'display_name': '删除角色', 'module': 'role', 'action': 'delete'},
    {'name': 'role:assign_permission', 'display_name': '分配权限', 'module': 'role', 'action': 'assign_permission'},
    
    # 剧本管理
    {'name': 'script:create', 'display_name': '创建剧本', 'module': 'script', 'action': 'create'},
    {'name': 'script:read', 'display_name': '查看剧本', 'module': 'script', 'action': 'read'},
    {'name': 'script:update', 'display_name': '更新剧本', 'module': 'script', 'action': 'update'},
    {'name': 'script:delete', 'display_name': '删除剧本', 'module': 'script', 'action': 'delete'},
    {'name': 'script:assign', 'display_name': '分配剧本', 'module': 'script', 'action': 'assign'},
    
    # 音频管理
    {'name': 'audio:upload', 'display_name': '上传音频', 'module': 'audio', 'action': 'upload'},
    {'name': 'audio:download', 'display_name': '下载音频', 'module': 'audio', 'action': 'download'},
    {'name': 'audio:delete', 'display_name': '删除音频', 'module': 'audio', 'action': 'delete'},
    {'name': 'audio:review', 'display_name': '审听音频', 'module': 'audio', 'action': 'review'},
    
    # 审听管理
    {'name': 'review:create', 'display_name': '创建审听', 'module': 'review', 'action': 'create'},
    {'name': 'review:read', 'display_name': '查看审听', 'module': 'review', 'action': 'read'},
    {'name': 'review:update', 'display_name': '更新审听', 'module': 'review', 'action': 'update'},
    {'name': 'review:approve', 'display_name': '审批通过', 'module': 'review', 'action': 'approve'},
    {'name': 'review:reject', 'display_name': '审批拒绝', 'module': 'review', 'action': 'reject'},
    
    # 系统管理
    {'name': 'system:config', 'display_name': '系统配置', 'module': 'system', 'action': 'config'},
    {'name': 'system:log', 'display_name': '查看日志', 'module': 'system', 'action': 'log'},
    {'name': 'system:monitor', 'display_name': '系统监控', 'module': 'system', 'action': 'monitor'},
]


def upgrade() -> None:
    """插入系统权限数据到数据库"""
    connection = op.get_bind()
    
    # 为每个权限数据添加默认字段
    for i, perm_data in enumerate(SYSTEM_PERMISSIONS_DATA):
        # 检查权限是否已存在
        result = connection.execute(
            text("SELECT id FROM permissions WHERE name = :name"),
            {'name': perm_data['name']}
        ).fetchone()
        
        if not result:
            # 插入新权限
             connection.execute(
                 text("""
                     INSERT INTO permissions (name, display_name, description, module, action, resource, is_system, is_active, sort_order, level, created_at, updated_at)
                     VALUES (:name, :display_name, :description, :module, :action, :resource, :is_system, :is_active, :sort_order, :level, NOW(), NOW())
                 """),
                 {
                     'name': perm_data['name'],
                     'display_name': perm_data['display_name'],
                     'description': perm_data['display_name'],
                     'module': perm_data['module'],
                     'action': perm_data['action'],
                     'resource': perm_data['module'],
                     'is_system': 1,
                     'is_active': 1,
                     'sort_order': i,
                     'level': 0
                 }
             )


def downgrade() -> None:
    """删除系统权限数据"""
    connection = op.get_bind()
    
    # 删除所有系统权限
    for perm_data in SYSTEM_PERMISSIONS_DATA:
        connection.execute(
            text("DELETE FROM permissions WHERE name = :name AND is_system = 1"),
            {'name': perm_data['name']}
        )