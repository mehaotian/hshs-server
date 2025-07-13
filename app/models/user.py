from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.core.database import Base


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    __table_args__ = {'comment': '用户基础信息表'}
    
    # 用户状态常量
    STATUS_ACTIVE = 1      # 启用
    STATUS_INACTIVE = 0    # 禁用
    STATUS_SUSPENDED = -1  # 暂停
    STATUS_DELETED = -2    # 删除

    id = Column(Integer, primary_key=True, index=True, comment="用户ID")
    username = Column(String(50), unique=True, index=True, nullable=False, comment="用户名")
    email = Column(String(100), unique=True, index=True, nullable=True, comment="邮箱地址")
    password_hash = Column(String(255), nullable=False, comment="密码哈希值")
    real_name = Column(String(100), nullable=True, comment="真实姓名")
    avatar_url = Column(String(500), nullable=True, comment="头像URL")
    phone = Column(String(20), nullable=True, comment="手机号码")
    wechat = Column(String(100), nullable=True, comment="微信号")
    sex = Column(Integer, nullable=True, comment="性别：1-男，2-女，0-其他/未知")
    bio = Column(Text, nullable=True, comment="个人简介")
    status = Column(Integer, default=1, comment="用户状态：1-启用，0-禁用")
    last_login_at = Column(DateTime, nullable=True, comment="最后登录时间")
    login_count = Column(Integer, default=0, comment="登录次数")
    settings = Column(JSON, nullable=True, comment="用户个人设置")
    
    # 时间戳字段
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关系映射
    user_roles = relationship("UserRole", back_populates="user", foreign_keys="UserRole.user_id", cascade="all, delete-orphan")
    script_assignments = relationship("ScriptAssignment", back_populates="user", foreign_keys="ScriptAssignment.user_id")
    cv_recordings = relationship("CVRecording", back_populates="cv_user")
    review_records = relationship("ReviewRecord", back_populates="reviewer")
    created_scripts = relationship("Script", back_populates="creator")
    profile = relationship("UserProfile", uselist=False, cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', real_name='{self.real_name}')>"
    
    @property
    def is_active(self) -> bool:
        """检查用户是否激活"""
        return self.status == self.STATUS_ACTIVE
    
    @property
    def display_name(self) -> str:
        """获取显示名称"""
        return self.real_name or self.username
    
    async def get_roles(self, db=None) -> List[str]:
        """获取用户角色列表"""
        if db is None:
            # 如果没有传入db会话，尝试从已加载的关系中获取
            return [user_role.role.name for user_role in self.user_roles if user_role.role]
        
        # 使用数据库会话查询角色
        from sqlalchemy import select
        from app.models.role import UserRole, Role
        
        result = await db.execute(
            select(Role.name)
            .join(UserRole, Role.id == UserRole.role_id)
            .where(UserRole.user_id == self.id)
        )
        return [row[0] for row in result.fetchall()]
    
    async def has_role(self, role_name: str, db=None) -> bool:
        """检查用户是否拥有指定角色"""
        roles = await self.get_roles(db)
        return role_name in roles
    
    async def get_permissions(self, db=None) -> List[str]:
        """获取用户所有权限"""
        if db is None:
            # 如果没有传入db会话，尝试从已加载的关系中获取
            try:
                permissions = set()
                for user_role in self.user_roles:
                    if user_role.role:
                        # 使用Role模型的permission_list属性来获取权限
                        role_permissions = user_role.role.permission_list
                        permissions.update(role_permissions)
                return list(permissions)
            except Exception as e:
                # 如果出错，记录错误并返回空列表
                print(f"Error getting permissions: {e}")
                return []
        
        # 使用数据库会话查询权限
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.models.role import UserRole, Role, RolePermission
        
        # 查询用户的角色，并预加载权限信息
        result = await db.execute(
            select(Role)
            .options(
                selectinload(Role.role_permissions).selectinload(RolePermission.permission)
            )
            .join(UserRole, Role.id == UserRole.role_id)
            .where(UserRole.user_id == self.id)
        )
        
        permissions = set()
        roles = result.scalars().all()
        for role in roles:
            try:
                # 使用Role模型的permission_list属性来获取权限
                role_permissions = role.permission_list
                permissions.update(role_permissions)
            except Exception as e:
                # 如果出错，记录错误并继续处理其他角色
                print(f"Error getting permissions for role {role.name}: {e}")
                continue
        return list(permissions)
    
    async def has_permission(self, permission: str, db=None) -> bool:
        """检查用户是否拥有指定权限（支持通配符匹配）"""
        if db is None:
            # 如果没有传入db会话，尝试从已加载的关系中获取
            try:
                for user_role in self.user_roles:
                    if user_role.role and user_role.role.has_permission(permission):
                        return True
                return False
            except Exception as e:
                print(f"Error checking permission: {e}")
                return False
        
        # 使用数据库会话查询角色并检查权限
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.models.role import UserRole, Role, RolePermission
        
        result = await db.execute(
            select(Role)
            .options(
                selectinload(Role.role_permissions).selectinload(RolePermission.permission)
            )
            .join(UserRole, Role.id == UserRole.role_id)
            .where(UserRole.user_id == self.id)
        )
        
        roles = result.scalars().all()
        for role in roles:
            if role.has_permission(permission):
                return True
        
        return False
    
    async def get_expanded_permissions(self, db=None) -> List[str]:
        """获取用户的展开权限列表（将通配符权限展开为具体权限）"""
        from app.models.role import SYSTEM_PERMISSIONS
        
        # 获取用户的原始权限列表
        raw_permissions = await self.get_permissions(db)
        expanded_permissions = set()
        
        for permission in raw_permissions:
            if permission == '*' or permission == '*:*':
                # 超级权限，添加所有系统权限
                expanded_permissions.update(SYSTEM_PERMISSIONS.keys())
            elif permission.endswith(':*'):
                # 模块通配符权限，添加该模块的所有权限
                module = permission[:-2]  # 移除 ':*'
                for sys_perm in SYSTEM_PERMISSIONS.keys():
                    if sys_perm.startswith(f"{module}:"):
                        expanded_permissions.add(sys_perm)
            elif permission.startswith('*:'):
                # 操作通配符权限，添加所有模块的该操作权限
                action = permission[2:]  # 移除 '*:'
                for sys_perm in SYSTEM_PERMISSIONS.keys():
                    if sys_perm.endswith(f":{action}"):
                        expanded_permissions.add(sys_perm)
            else:
                # 具体权限，直接添加
                expanded_permissions.add(permission)
        
        return sorted(list(expanded_permissions))
    
    def update_login_info(self) -> None:
        """更新登录信息"""
        self.last_login_at = datetime.utcnow()
        # 确保 login_count 不为 None
        if self.login_count is None:
            self.login_count = 0
        self.login_count += 1
    
    async def to_dict(self, include_sensitive: bool = False, db=None) -> Dict[str, Any]:
        """转换为字典格式"""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'real_name': self.real_name,
            'avatar_url': self.avatar_url,
            'phone': self.phone,
            'wechat': self.wechat,
            'sex': self.sex,
            'bio': self.bio,
            'status': self.status,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'login_count': self.login_count,
            'settings': self.settings,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'roles': await self.get_roles(db),
            'display_name': self.display_name,
            'is_active': self.is_active,
        }
        
        if include_sensitive:
            data['permissions'] = await self.get_permissions(db)
        
        return data
    
    def to_dict_sync(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """同步版本的转换为字典格式（用于不需要数据库查询的场景）"""
        # 尝试从已加载的关系中获取角色
        try:
            roles = [user_role.role.name for user_role in self.user_roles if user_role.role]
        except:
            roles = []
        
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'real_name': self.real_name,
            'avatar_url': self.avatar_url,
            'phone': self.phone,
            'wechat': self.wechat,
            'sex': self.sex,
            'bio': self.bio,
            'status': self.status,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'login_count': self.login_count,
            'settings': self.settings,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'roles': roles,
            'display_name': self.display_name,
            'is_active': self.is_active,
        }
        
        if include_sensitive:
            # 尝试从已加载的关系中获取权限
            try:
                permissions = set()
                for user_role in self.user_roles:
                    if user_role.role:
                        # 使用Role模型的permission_list属性来获取权限
                        role_permissions = user_role.role.permission_list
                        permissions.update(role_permissions)
                data['permissions'] = list(permissions)
            except Exception as e:
                # 如果出错，记录错误并返回空列表
                print(f"Error getting permissions: {e}")
                data['permissions'] = []
        
        return data


class UserProfile(Base):
    """用户扩展信息模型"""
    __tablename__ = "user_profiles"
    __table_args__ = {'comment': '用户扩展信息表'}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, unique=True, comment="用户ID")
    cv_experience = Column(Text, nullable=True, comment="配音经验")
    voice_characteristics = Column(Text, nullable=True, comment="声音特点")
    specialties = Column(JSON, nullable=True, comment="专长领域")
    equipment_info = Column(Text, nullable=True, comment="设备信息")
    work_schedule = Column(JSON, nullable=True, comment="工作时间安排")
    emergency_contact = Column(String(100), nullable=True, comment="紧急联系人")
    emergency_phone = Column(String(20), nullable=True, comment="紧急联系电话")
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # 关系映射
    user = relationship("User", back_populates="profile")
    
    def __repr__(self) -> str:
        return f"<UserProfile(user_id={self.user_id})>"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'cv_experience': self.cv_experience,
            'voice_characteristics': self.voice_characteristics,
            'specialties': self.specialties,
            'equipment_info': self.equipment_info,
            'work_schedule': self.work_schedule,
            'emergency_contact': self.emergency_contact,
            'emergency_phone': self.emergency_phone,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }