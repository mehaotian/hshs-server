"""add_permission_classification_fields

Revision ID: permission_classification_001
Revises: 47e546b57da5
Create Date: 2025-01-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = 'permission_classification_001'
down_revision = '47e546b57da5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """添加权限分类相关字段"""
    # 注意：parent_id、level、path字段已在create_base_tables.py中定义
    # 只添加is_category字段
    op.add_column('permissions', sa.Column('is_category', sa.Integer(), nullable=False, server_default='0', comment='是否为分类：1-是，0-否'))
    
    # 外键约束已在create_base_tables.py中创建，这里不需要重复创建
    
    # 创建索引以优化查询性能
    # 注意：parent_id、level、path的索引已在create_base_tables.py中创建
    # 只创建is_category和sort_order的索引
    
    # 检查并创建 is_category 索引（PostgreSQL特定查询）
    connection = op.get_bind()
    
    result = connection.execute(text("""
        SELECT COUNT(*) FROM pg_indexes 
        WHERE indexname = 'idx_permissions_is_category'
    """))
    if result.scalar() == 0:
        op.create_index('idx_permissions_is_category', 'permissions', ['is_category'])
    
    # 检查并创建 sort_order 索引
    result = connection.execute(text("""
        SELECT COUNT(*) FROM pg_indexes 
        WHERE indexname = 'idx_permissions_sort_order'
    """))
    if result.scalar() == 0:
        op.create_index('idx_permissions_sort_order', 'permissions', ['sort_order'])
    
    # 初始化现有权限的分类数据
    
    # 创建权限分类
    categories = [
        {'name': 'user_management', 'display_name': '用户管理', 'description': '用户相关权限管理', 'level': 1, 'path': '/user_management', 'is_category': 1, 'sort_order': 1},
        {'name': 'role_management', 'display_name': '角色管理', 'description': '角色相关权限管理', 'level': 1, 'path': '/role_management', 'is_category': 1, 'sort_order': 2},
        {'name': 'script_management', 'display_name': '剧本管理', 'description': '剧本相关权限管理', 'level': 1, 'path': '/script_management', 'is_category': 1, 'sort_order': 3},
        {'name': 'audio_management', 'display_name': '音频管理', 'description': '音频相关权限管理', 'level': 1, 'path': '/audio_management', 'is_category': 1, 'sort_order': 4},
        {'name': 'review_management', 'display_name': '审听管理', 'description': '审听相关权限管理', 'level': 1, 'path': '/review_management', 'is_category': 1, 'sort_order': 5},
        {'name': 'system_management', 'display_name': '系统管理', 'description': '系统相关权限管理', 'level': 1, 'path': '/system_management', 'is_category': 1, 'sort_order': 6},
    ]
    
    # 插入权限分类
    for category in categories:
        connection.execute(text("""
            INSERT INTO permissions (name, display_name, description, level, path, is_category, sort_order, is_system, is_active, created_at, updated_at)
            VALUES (:name, :display_name, :description, :level, :path, :is_category, :sort_order, 1, 1, NOW(), NOW())
        """), category)
    
    # 更新现有权限的分类信息
    permission_mappings = {
        'user:': 'user_management',
        'role:': 'role_management', 
        'script:': 'script_management',
        'audio:': 'audio_management',
        'review:': 'review_management',
        'system:': 'system_management'
    }
    
    # 为每个权限分配到对应的分类
    for prefix, category_name in permission_mappings.items():
        # 获取分类ID
        result = connection.execute(text("""
            SELECT id FROM permissions WHERE name = :category_name AND is_category = 1
        """), {'category_name': category_name})
        category_row = result.fetchone()
        
        if category_row:
            category_id = category_row[0]
            
            # 更新匹配的权限
            connection.execute(text("""
                UPDATE permissions 
                SET parent_id = :parent_id, 
                    level = 2, 
                    path = CONCAT((SELECT path FROM (SELECT path FROM permissions WHERE id = :parent_id) AS temp), '/', name)
                WHERE name LIKE :pattern AND is_category = 0
            """), {
                'parent_id': category_id,
                'pattern': f'{prefix}%'
            })


def downgrade() -> None:
    """移除权限分类相关字段"""
    # 删除索引
    op.drop_index('idx_permissions_sort_order', 'permissions')
    op.drop_index('idx_permissions_is_category', 'permissions')
    
    # 删除权限分类记录
    connection = op.get_bind()
    connection.execute(text("DELETE FROM permissions WHERE is_category = 1"))
    
    # 只删除is_category字段，其他字段在create_base_tables.py中定义
    op.drop_column('permissions', 'is_category')