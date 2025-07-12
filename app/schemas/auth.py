# -*- coding: utf-8 -*-
"""
认证相关的 Pydantic 模型

定义用户认证、授权相关的请求和响应模型：
- 登录请求和响应
- 注册请求和响应
- 令牌相关模型
- 密码重置相关模型
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator
from datetime import datetime


class UserLogin(BaseModel):
    """用户登录请求模型"""
    
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    remember_me: bool = Field(default=False, description="记住我")
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "testuser",
                "password": "password123",
                "remember_me": False
            }
        }


class UserRegister(BaseModel):
    """用户注册请求模型"""
    
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    confirm_password: str = Field(..., min_length=6, max_length=128, description="确认密码")
    full_name: Optional[str] = Field(None, max_length=100, description="全名")
    
    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        if 'password' in info.data and v != info.data['password']:
            raise ValueError('密码和确认密码不匹配')
        return v
    
    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('用户名只能包含字母、数字、下划线和连字符')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "newuser",
                "email": "user@example.com",
                "password": "password123",
                "confirm_password": "password123",
                "full_name": "张三"
            }
        }


class Token(BaseModel):
    """访问令牌响应模型"""
    
    access_token: str = Field(..., description="访问令牌")
    refresh_token: Optional[str] = Field(None, description="刷新令牌")
    token_type: str = Field(default="bearer", description="令牌类型")
    expires_in: int = Field(..., description="过期时间（秒）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600
            }
        }


class TokenData(BaseModel):
    """令牌数据模型"""
    
    user_id: Optional[int] = None
    username: Optional[str] = None
    scopes: list[str] = []


class RefreshToken(BaseModel):
    """刷新令牌请求模型"""
    
    refresh_token: str = Field(..., description="刷新令牌")
    
    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class PasswordReset(BaseModel):
    """密码重置请求模型"""
    
    email: EmailStr = Field(..., description="邮箱地址")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com"
            }
        }


class PasswordResetConfirm(BaseModel):
    """密码重置确认模型"""
    
    token: str = Field(..., description="重置令牌")
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码")
    confirm_password: str = Field(..., min_length=6, max_length=128, description="确认新密码")
    
    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('密码和确认密码不匹配')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "token": "reset_token_here",
                "new_password": "newpassword123",
                "confirm_password": "newpassword123"
            }
        }


class PasswordChange(BaseModel):
    """密码修改模型"""
    
    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码")
    confirm_password: str = Field(..., min_length=6, max_length=128, description="确认新密码")
    
    @field_validator('confirm_password')
    @classmethod
    def passwords_match(cls, v, info):
        if 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('密码和确认密码不匹配')
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "current_password": "oldpassword123",
                "new_password": "newpassword123",
                "confirm_password": "newpassword123"
            }
        }


class LoginData(BaseModel):
    """登录数据模型"""
    
    avatar: Optional[str] = Field(None, description="用户头像")
    username: str = Field(..., description="用户名")
    nickname: str = Field(..., description="昵称")
    roles: list[str] = Field(default_factory=list, description="用户角色列表")
    permissions: list[str] = Field(default_factory=list, description="用户权限列表")
    access_token: str = Field(..., description="访问令牌")
    refresh_token: str = Field(..., description="刷新令牌")
    expires: str = Field(..., description="过期时间（格式：yyyy/MM/dd HH:mm:ss）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "avatar": "https://avatars.githubusercontent.com/u/44761321",
                "username": "admin",
                "nickname": "鹅子",
                "roles": ["admin"],
                "permissions": ["*:*:*"],
                "access_token": "eyJhbGciOiJIUzUxMiJ9.admin",
                "refresh_token": "eyJhbGciOiJIUzUxMiJ9.adminRefresh",
                "expires": "2025/12/31 23:59:59"
            }
        }


class LoginResponse(BaseModel):
    """登录响应模型"""
    
    code: int = Field(default=0, description="响应状态码")
    data: LoginData = Field(..., description="登录数据")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": 0,
                "data": {
                    "avatar": "https://avatars.githubusercontent.com/u/44761321",
                    "username": "admin",
                    "nickname": "鹅子",
                    "roles": ["admin"],
                    "permissions": ["*:*:*"],
                    "access_token": "eyJhbGciOiJIUzUxMiJ9.admin",
                    "refresh_token": "eyJhbGciOiJIUzUxMiJ9.adminRefresh",
                    "expires": "2025/12/31 23:59:59"
                }
            }
        }


class RegisterResponse(BaseModel):
    """注册响应模型"""
    
    user: dict = Field(..., description="用户信息")
    message: str = Field(default="注册成功", description="响应消息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "user": {
                    "id": 1,
                    "username": "newuser",
                    "email": "user@example.com",
                    "full_name": "张三",
                    "is_active": True,
                    "created_at": "2024-01-01T00:00:00Z"
                },
                "message": "注册成功"
            }
        }


class LogoutResponse(BaseModel):
    """登出响应模型"""
    
    message: str = Field(default="登出成功", description="响应消息")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "登出成功"
            }
        }


class UserProfile(BaseModel):
    """用户资料模型"""
    
    id: int = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    full_name: Optional[str] = Field(None, description="全名")
    is_active: bool = Field(..., description="是否激活")
    is_superuser: bool = Field(default=False, description="是否超级用户")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    last_login: Optional[datetime] = Field(None, description="最后登录时间")
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": 1,
                "username": "testuser",
                "email": "user@example.com",
                "full_name": "张三",
                "is_active": True,
                "is_superuser": False,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "last_login": "2024-01-01T00:00:00Z"
            }
        }