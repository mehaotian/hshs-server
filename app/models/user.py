from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.core.database import Base


class User(Base):
    """用户模型"""
    __tablename__ = "users"
    __table_args__ = {'comment': '用户基础信息表'}

    id = Column(Integer, primary_key=True, index=True, comment="用户ID")
    username = Column(String(50), unique=True, index=True, nullable=False, comment="用户名")
    email = Column(String(100), unique=True, index=True, nullable=True, comment="邮箱地址")
    password_hash = Column(String(255), nullable=False, comment="密码哈希值")
    real_name = Column(String(100), nullable=True, comment="真实姓名")
    avatar_url = Column(String(500), nullable=True, comment="头像URL")
    phone = Column(String(20), nullable=True, comment="手机号码")
    wechat = Column(String(100), nullable=True, comment="微信号")
    bio = Column(Text, nullable=True, comment="个人简介")
    status = Column(Integer, default=1, comment="用户状态：1-启用，0-禁用")
    last_login_at = Column(DateTime, nullable=True, comment="最后登录时间")
    login_count = Column(Integer, default=0, comment="登录次数")
    settings = Column(JSON, nullable=True, comment="用户个人设置")
    
    # 时间戳字段
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关系映射
    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    script_assignments = relationship("ScriptAssignment", back_populates="user")
    cv_recordings = relationship("CVRecording", back_populates="cv_user")
    review_records = relationship("ReviewRecord", back_populates="reviewer")
    created_scripts = relationship("Script", back_populates="creator")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', real_name='{self.real_name}')>"
    
    @property
    def is_active(self) -> bool:
        """检查用户是否激活"""
        return self.status == 1
    
    @property
    def display_name(self) -> str:
        """获取显示名称"""
        return self.real_name or self.username
    
    def get_roles(self) -> List[str]:
        """获取用户角色列表"""
        return [user_role.role.name for user_role in self.user_roles if user_role.role]
    
    def has_role(self, role_name: str) -> bool:
        """检查用户是否拥有指定角色"""
        return role_name in self.get_roles()
    
    def get_permissions(self) -> List[str]:
        """获取用户所有权限"""
        permissions = set()
        for user_role in self.user_roles:
            if user_role.role and user_role.role.permissions:
                role_permissions = user_role.role.permissions.get('permissions', [])
                permissions.update(role_permissions)
        return list(permissions)
    
    def has_permission(self, permission: str) -> bool:
        """检查用户是否拥有指定权限"""
        return permission in self.get_permissions()
    
    def update_login_info(self) -> None:
        """更新登录信息"""
        self.last_login_at = datetime.utcnow()
        self.login_count += 1
    
    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """转换为字典格式"""
        data = {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'real_name': self.real_name,
            'avatar_url': self.avatar_url,
            'phone': self.phone,
            'wechat': self.wechat,
            'bio': self.bio,
            'status': self.status,
            'last_login_at': self.last_login_at.isoformat() if self.last_login_at else None,
            'login_count': self.login_count,
            'settings': self.settings,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'roles': self.get_roles(),
            'display_name': self.display_name,
            'is_active': self.is_active,
        }
        
        if include_sensitive:
            data['permissions'] = self.get_permissions()
        
        return data


class UserProfile(Base):
    """用户扩展信息模型"""
    __tablename__ = "user_profiles"
    __table_args__ = {'comment': '用户扩展信息表'}

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, unique=True, comment="用户ID")
    cv_experience = Column(Text, nullable=True, comment="配音经验")
    voice_characteristics = Column(Text, nullable=True, comment="声音特点")
    specialties = Column(JSON, nullable=True, comment="专长领域")
    equipment_info = Column(Text, nullable=True, comment="设备信息")
    work_schedule = Column(JSON, nullable=True, comment="工作时间安排")
    emergency_contact = Column(String(100), nullable=True, comment="紧急联系人")
    emergency_phone = Column(String(20), nullable=True, comment="紧急联系电话")
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def __repr__(self) -> str:
        return f"<UserProfile(user_id={self.user_id})>"