# -*- coding: utf-8 -*-
"""
API 模块初始化文件

统一管理所有版本的 API 路由，目前包括：
- v1 版本的 API 路由

未来可以扩展更多版本的 API 路由，如 v2, v3 等
"""

from fastapi import APIRouter

from .v1 import api_v1_router

# 创建主 API 路由
api_router = APIRouter(prefix="/api")

# 注册 v1 版本路由
api_router.include_router(api_v1_router)

# 导出主路由
__all__ = ["api_router"]