# -*- coding: utf-8 -*-
"""
API v1 路由初始化模块

统一管理和导入所有 v1 版本的 API 路由，包括：
- 认证相关路由 (auth)
- 用户管理路由 (users)
- 角色权限路由 (roles)
- 剧本管理路由 (scripts)
- 音频管理路由 (audios)
- 部门管理路由 (departments)
"""

from fastapi import APIRouter

from .auth import router as auth_router
from .users import router as users_router
from .roles import router as roles_router
from .scripts import router as scripts_router
from .audios import router as audios_router
from .departments import router as departments_router

# 创建 v1 版本的主路由
api_v1_router = APIRouter(prefix="/v1")

# 注册各个子路由
api_v1_router.include_router(
    auth_router,
    prefix="/auth",
    tags=["认证"]
)

api_v1_router.include_router(
    users_router,
    prefix="/users",
    tags=["用户管理"]
)

api_v1_router.include_router(
    roles_router,
    prefix="/roles",
    tags=["角色权限"]
)

api_v1_router.include_router(
    scripts_router,
    prefix="/scripts",
    tags=["剧本管理"]
)

api_v1_router.include_router(
    audios_router,
    prefix="/audios",
    tags=["音频管理"]
)

api_v1_router.include_router(
    departments_router
)

# 导出主路由
__all__ = ["api_v1_router"]