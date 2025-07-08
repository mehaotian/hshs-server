# -*- coding: utf-8 -*-
"""
FastAPI 应用主入口文件

集成所有组件：
- 应用配置
- 数据库连接
- 中间件
- 异常处理
- API 路由
- 静态文件服务
"""

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.core.middleware import setup_middleware
from app.core.exceptions import register_exception_handlers
from app.core.logger import logger
from app.api import api_router


def create_app() -> FastAPI:
    """
    创建 FastAPI 应用实例
    
    Returns:
        FastAPI: 配置完成的 FastAPI 应用实例
    """
    # 创建 FastAPI 应用
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.PROJECT_VERSION,
        openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.DEBUG else None,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
    )
    
    # 设置 CORS
    if settings.BACKEND_CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # 设置中间件
    setup_middleware(app)
    
    # 设置异常处理器
    register_exception_handlers(app)
    
    # 注册 API 路由
    app.include_router(api_router)
    
    # 静态文件服务（用于音频文件等）
    if settings.STATIC_FILES_DIR:
        app.mount("/static", StaticFiles(directory=settings.STATIC_FILES_DIR), name="static")
    
    # 健康检查端点
    @app.get("/health")
    async def health_check():
        """健康检查端点"""
        return {
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": settings.PROJECT_VERSION
        }
    
    # 根路径
    @app.get("/")
    async def root():
        """根路径"""
        return {
            "message": f"Welcome to {settings.PROJECT_NAME}",
            "version": settings.PROJECT_VERSION,
            "docs": "/docs" if settings.DEBUG else "Documentation not available in production"
        }
    
    return app


async def create_tables():
    """
    创建数据库表
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表创建完成")


# 创建应用实例
app = create_app()


@app.on_event("startup")
async def startup_event():
    """
    应用启动事件
    """
    # 日志已在导入时自动设置
    logger.info(f"启动 {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}")
    
    # 创建数据库表
    await create_tables()
    
    logger.info("应用启动完成")


@app.on_event("shutdown")
async def shutdown_event():
    """
    应用关闭事件
    """
    logger.info("应用正在关闭...")
    
    # 关闭数据库连接
    await engine.dispose()
    
    logger.info("应用已关闭")


if __name__ == "__main__":
    # 开发环境直接运行
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info",
        access_log=True
    )