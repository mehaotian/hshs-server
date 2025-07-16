from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, backref
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
    is_system = Column(Integer, default=0, comment="是否系统角色：1-是，0-否")
    is_active = Column(Integer, default=1, comment="是否激活：1-是，0-否")
    sort_order = Column(Integer, default=0, comment="排序顺序")
    
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关系映射
    user_roles = relationship("UserRole", back_populates="role", cascade="all, delete-orphan")
    role_permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name='{self.name}', display_name='{self.display_name}')>"
    
    @property
    def permission_list(self) -> List[str]:
        """获取权限列表"""
        return [rp.permission.name for rp in self.role_permissions if rp.permission]
    
    def has_permission(self, permission: str) -> bool:
        """检查角色是否拥有指定权限（支持通配符权限匹配）"""
        for rp in self.role_permissions:
            if not rp.permission:
                continue
                
            perm_name = rp.permission.name
            
            # 精确匹配
            if perm_name == permission:
                return True
            
            # 通配符权限匹配
            if perm_name == '*' or perm_name == '*:*':
                # 超级权限，匹配所有权限
                return True
            elif perm_name.endswith(':*'):
                # 模块通配符权限，如 user:*
                module = perm_name[:-2]  # 移除 ':*'
                if permission.startswith(f"{module}:"):
                    return True
            elif perm_name.startswith('*:'):
                # 操作通配符权限，如 *:read
                action = perm_name[2:]  # 移除 '*:'
                if permission.endswith(f":{action}"):
                    return True
        
        return False
    
    def add_permission(self, permission_id: int) -> None:
        """添加权限"""
        # 检查是否已存在该权限
        existing = any(rp.permission_id == permission_id for rp in self.role_permissions)
        if not existing:
            from app.models.role import RolePermission
            role_permission = RolePermission(role_id=self.id, permission_id=permission_id)
            self.role_permissions.append(role_permission)
    
    def remove_permission(self, permission_id: int) -> None:
        """移除权限"""
        self.role_permissions = [rp for rp in self.role_permissions if rp.permission_id != permission_id]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'name': self.name,
            'display_name': self.display_name,
            'description': self.description,
            'permissions': self.permission_list,
            'is_system': bool(self.is_system),
            'is_active': bool(self.is_active),
            'sort_order': self.sort_order,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    # 移除 get_system_roles 方法，现在角色完全由数据库管理


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
    # is_wildcard 字段已移除，现在通过权限名称自动判断
    is_active = Column(Integer, default=1, comment="是否激活：1-是，0-否")
    sort_order = Column(Integer, default=0, comment="排序顺序")
    
    # 层级权限相关字段
    parent_id = Column(Integer, ForeignKey('permissions.id', ondelete='CASCADE'), nullable=True, comment="父权限ID")
    level = Column(Integer, default=0, comment="权限层级：0-根级，1-一级，2-二级等")
    path = Column(String(500), nullable=True, comment="权限路径，用于快速查询子权限")
    
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 关系映射
    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")
    # 自引用关系：父子权限
    children = relationship("Permission", backref=backref("parent", remote_side=[id]), cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Permission(id={self.id}, name='{self.name}')>"
    
    @property
    def is_wildcard(self) -> bool:
        """判断是否为通配符权限"""
        return '*' in (self.name or '')
    
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
            'is_wildcard': self.is_wildcard,
            'is_active': bool(self.is_active),
            'sort_order': self.sort_order,
            'parent_id': self.parent_id,
            'level': self.level,
            'path': self.path,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
    
    def get_all_children(self) -> List['Permission']:
        """递归获取所有子权限"""
        all_children = []
        for child in self.children:
            all_children.append(child)
            all_children.extend(child.get_all_children())
        return all_children
    
    def get_ancestors(self) -> List['Permission']:
        """获取所有祖先权限"""
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return ancestors
    
    def build_path(self) -> str:
        """构建权限路径"""
        if not self.parent:
            return f"/{self.name}"
        return f"{self.parent.build_path()}/{self.name}"
    
    def to_tree_dict(self, include_children: bool = True) -> Dict[str, Any]:
        """转换为树形结构字典"""
        result = self.to_dict()
        if include_children and self.children:
            result['children'] = [child.to_tree_dict(include_children=True) for child in sorted(self.children, key=lambda x: x.sort_order)]
        return result
    
    # 移除 get_system_permissions 方法，现在权限完全由数据库管理


class RolePermission(Base):
    """角色权限关联模型"""
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint('role_id', 'permission_id', name='uk_role_permission'),
        {'comment': '角色权限关联表'}
    )

    id = Column(Integer, primary_key=True, index=True, comment="关联ID")
    role_id = Column(Integer, ForeignKey('roles.id', ondelete='CASCADE'), nullable=False, comment="角色ID")
    permission_id = Column(Integer, ForeignKey('permissions.id', ondelete='CASCADE'), nullable=False, comment="权限ID")
    granted_by = Column(Integer, ForeignKey('users.id'), nullable=True, comment="授权者ID")
    granted_at = Column(DateTime, default=func.now(), comment="授权时间")
    expires_at = Column(DateTime, nullable=True, comment="过期时间")
    
    created_at = Column(DateTime, default=func.now(), comment="创建时间")

    # 关系映射
    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")
    granter = relationship("User", foreign_keys=[granted_by])
    
    def __repr__(self) -> str:
        return f"<RolePermission(role_id={self.role_id}, permission_id={self.permission_id})>"
    
    @property
    def is_expired(self) -> bool:
        """检查权限是否已过期"""
        if not self.expires_at:
            return False
        from datetime import datetime
        return datetime.utcnow() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'role_id': self.role_id,
            'permission_id': self.permission_id,
            'role_name': self.role.name if self.role else None,
            'permission_name': self.permission.name if self.permission else None,
            'granted_by': self.granted_by,
            'granted_at': self.granted_at.isoformat() if self.granted_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_expired': self.is_expired,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# 移除硬编码的系统权限和角色定义
# 现在所有权限和角色都通过数据库管理