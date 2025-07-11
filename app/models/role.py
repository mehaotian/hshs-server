from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Dict, List, Any, Optional

from app.core.database import Base


class Role(Base):
    """角色模型"""
    __tablename__ = "roles"
    __table_args__ = {'comment': '角色定义表'}

    id = Column(Integer, primary_key=True, index=True, comment="角色ID")
    name = Column(String(50), unique=True, nullable=False, comment="角色名称")
    display_name = Column(String(100), nullable=True, comment="角色显示名称")
    description = Column(Text, nullable=True, comment="角色描述")
    permissions = Column(JSON, nullable=True, comment="权限配置JSON")
    is_system = Column(Integer, default=0, comment="是否系统角色：1-是，0-否")
    sort_order = Column(Integer, default=0, comment="排序顺序")
    
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关系映射
    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.name}', display_name='{self.display_name}')>"
    
    @property
    def permission_list(self) -> List[str]:
        """获取权限列表"""
        if not self.permissions:
            return []
        # 兼容处理：如果permissions是列表，直接返回；如果是字典，取permissions字段
        if isinstance(self.permissions, list):
            return self.permissions
        elif isinstance(self.permissions, dict):
            return self.permissions.get('permissions', [])
        else:
            return []
    
    def has_permission(self, permission: str) -> bool:
        """检查角色是否拥有指定权限（支持通配符匹配）"""
        permissions = self.permission_list
        
        # 1. 检查超级权限 *:* 或 *
        if '*:*' in permissions or '*' in permissions:
            return True
        
        # 2. 精确匹配
        if permission in permissions:
            return True
        
        # 3. 通配符匹配
        if ':' in permission:
            module, action = permission.split(':', 1)
            
            # 检查模块通配符 module:*
            module_wildcard = f"{module}:*"
            if module_wildcard in permissions:
                return True
            
            # 检查操作通配符 *:action
            action_wildcard = f"*:{action}"
            if action_wildcard in permissions:
                return True
        
        return False
    
    def add_permission(self, permission: str) -> None:
        """添加权限"""
        if not self.permissions:
            self.permissions = {'permissions': []}
        
        # 兼容处理：统一转换为字典格式
        if isinstance(self.permissions, list):
            permissions = self.permissions
            if permission not in permissions:
                permissions.append(permission)
            self.permissions = {'permissions': permissions}
        elif isinstance(self.permissions, dict):
            permissions = self.permissions.get('permissions', [])
            if permission not in permissions:
                permissions.append(permission)
                self.permissions = {'permissions': permissions}
        else:
            self.permissions = {'permissions': [permission]}
    
    def remove_permission(self, permission: str) -> None:
        """移除权限"""
        if not self.permissions:
            return
        
        # 兼容处理：统一转换为字典格式
        if isinstance(self.permissions, list):
            permissions = self.permissions
            if permission in permissions:
                permissions.remove(permission)
            self.permissions = {'permissions': permissions}
        elif isinstance(self.permissions, dict):
            permissions = self.permissions.get('permissions', [])
            if permission in permissions:
                permissions.remove(permission)
                self.permissions = {'permissions': permissions}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'permissions': self.permission_list,
            'is_system': bool(self.is_system),
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def get_system_roles(cls) -> List[Dict[str, Any]]:
        """获取系统角色定义"""
        roles = []
        for name, config in SYSTEM_ROLES.items():
            roles.append({
                'name': name,
                'display_name': config['display_name'],
                'description': config['description'],
                'permissions': config['permissions'],
                'is_system': 1,
                'sort_order': len(roles)
            })
        return roles


class UserRole(Base):
    """用户角色关联模型"""
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint('user_id', 'role_id', name='uk_user_role'),
        {'comment': '用户角色关联表'}
    )

    id = Column(Integer, primary_key=True, index=True, comment="关联ID")
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, comment="用户ID")
    role_id = Column(Integer, ForeignKey('roles.id', ondelete='CASCADE'), nullable=False, comment="角色ID")
    assigned_by = Column(Integer, ForeignKey('users.id'), nullable=True, comment="分配者ID")
    assigned_at = Column(DateTime, default=func.now(), comment="分配时间")
    expires_at = Column(DateTime, nullable=True, comment="过期时间")
    
    created_at = Column(DateTime, default=func.now(), comment="创建时间")

    # 关系映射
    user = relationship("User", back_populates="user_roles", foreign_keys=[user_id])
    role = relationship("Role", back_populates="user_roles")
    assigner = relationship("User", foreign_keys=[assigned_by])
    
    def __repr__(self) -> str:
        return f"<UserRole(user_id={self.user_id}, role_id={self.role_id})>"
    
    @property
    def is_expired(self) -> bool:
        """检查角色是否已过期"""
        if not self.expires_at:
            return False
        from datetime import datetime
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'role_id': self.role_id,
            'role_name': self.role.name if self.role else None,
            'role_display_name': self.role.display_name if self.role else None,
            'assigned_by': self.assigned_by,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_expired': self.is_expired,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class Permission(Base):
    """权限定义模型"""
    __tablename__ = "permissions"
    __table_args__ = {'comment': '权限定义表'}

    id = Column(Integer, primary_key=True, index=True, comment="权限ID")
    name = Column(String(100), unique=True, nullable=False, comment="权限名称")
    display_name = Column(String(100), nullable=True, comment="权限显示名称")
    description = Column(Text, nullable=True, comment="权限描述")
    module = Column(String(50), nullable=True, comment="所属模块")
    action = Column(String(50), nullable=True, comment="操作类型")
    resource = Column(String(50), nullable=True, comment="资源类型")
    is_system = Column(Integer, default=0, comment="是否系统权限")
    sort_order = Column(Integer, default=0, comment="排序顺序")
    
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name='{self.name}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'module': self.module,
            'action': self.action,
            'resource': self.resource,
            'is_system': bool(self.is_system),
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def get_system_permissions(cls) -> List[Dict[str, Any]]:
        """获取系统权限定义"""
        permissions = []
        for name, display_name in SYSTEM_PERMISSIONS.items():
            # 解析权限名称获取模块和操作
            parts = name.split(':')
            module = parts[0] if len(parts) > 0 else None
            action = parts[1] if len(parts) > 1 else None
            
            permissions.append({
                'name': name,
                'display_name': display_name,
                'description': display_name,
                'module': module,
                'action': action,
                'resource': module,
                'is_system': 1,
                'sort_order': len(permissions)
            })
        return permissions


# 预定义的系统权限
SYSTEM_PERMISSIONS = {
    # 用户管理
    'user:create': '创建用户',
    'user:read': '查看用户',
    'user:update': '更新用户',
    'user:delete': '删除用户',
    'user:assign_role': '分配角色',
    
    # 角色管理
    'role:create': '创建角色',
    'role:read': '查看角色',
    'role:update': '更新角色',
    'role:delete': '删除角色',
    'role:assign_permission': '分配权限',
    
    # 剧本管理
    'script:create': '创建剧本',
    'script:read': '查看剧本',
    'script:update': '更新剧本',
    'script:delete': '删除剧本',
    'script:assign': '分配剧本',
    
    # 音频管理
    'audio:upload': '上传音频',
    'audio:download': '下载音频',
    'audio:delete': '删除音频',
    'audio:review': '审听音频',
    
    # 审听管理
    'review:create': '创建审听',
    'review:read': '查看审听',
    'review:update': '更新审听',
    'review:approve': '审批通过',
    'review:reject': '审批拒绝',
    
    # 系统管理
    'system:config': '系统配置',
    'system:log': '查看日志',
    'system:monitor': '系统监控',
}

# 预定义的系统角色
SYSTEM_ROLES = {
    'super_admin': {
        'display_name': '超级管理员',
        'description': '系统最高权限管理员',
        'permissions': list(SYSTEM_PERMISSIONS.keys())
    },
    'project_leader': {
        'display_name': '项目组长',
        'description': '项目负责人，管理项目全流程',
        'permissions': [
            'script:create', 'script:read', 'script:update', 'script:assign',
            'audio:upload', 'audio:download', 'audio:review',
            'review:create', 'review:read', 'review:update',
            'user:read'
        ]
    },
    'director': {
        'display_name': '导演',
        'description': '艺术指导和质量监督',
        'permissions': [
            'script:read', 'audio:download', 'audio:review',
            'review:create', 'review:read', 'review:update'
        ]
    },
    'scriptwriter': {
        'display_name': '编剧',
        'description': '剧本创作和内容管理',
        'permissions': [
            'script:create', 'script:read', 'script:update'
        ]
    },
    'cv': {
        'display_name': 'CV配音演员',
        'description': '角色配音和音频录制',
        'permissions': [
            'script:read', 'audio:upload', 'audio:download'
        ]
    },
    'post_production': {
        'display_name': '后期制作',
        'description': '音频处理和技术制作',
        'permissions': [
            'audio:upload', 'audio:download', 'audio:delete'
        ]
    },
    'first_reviewer': {
        'display_name': '一审',
        'description': '技术质量审听',
        'permissions': [
            'audio:download', 'audio:review',
            'review:create', 'review:read', 'review:update'
        ]
    },
    'second_reviewer': {
        'display_name': '二审',
        'description': '内容质量审听',
        'permissions': [
            'audio:download', 'audio:review',
            'review:create', 'review:read', 'review:update',
            'review:approve', 'review:reject'
        ]
    }
}