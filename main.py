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
from contextlib import asynccontextmanager
from datetime import datetime
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
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
        swagger_favicon_url="/static/favicon.png",
        docs_url=None,  # 禁用默认docs，我们将手动创建
        redoc_url="/redoc" if settings.DEBUG else None,  # ReDoc 文档
        lifespan=lifespan,
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
    
    # 自定义Swagger UI文档页面
    if settings.DEBUG:
        from fastapi.responses import HTMLResponse
        
        @app.get("/docs", response_class=HTMLResponse)
        async def custom_swagger_ui_html():
            """自定义Swagger UI文档页面，使用本地静态文件"""
            return f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>{settings.PROJECT_NAME} - API Documentation</title>
                <link rel="stylesheet" type="text/css" href="/static/swagger-ui.css" />
                <link rel="icon" type="image/png" href="/static/favicon.png" />
            </head>
            <body>
                <div id="swagger-ui"></div>
                <script src="/static/swagger-ui-bundle.js"></script>
                <script>
                    SwaggerUIBundle({{
                        url: '{settings.API_V1_STR}/openapi.json',
                        dom_id: '#swagger-ui',
                        presets: [
                            SwaggerUIBundle.presets.apis,
                            SwaggerUIBundle.presets.standalone
                        ]
                    }});
                </script>
            </body>
            </html>
            """
    
    # 健康检查端点
    @app.get("/health")
    async def health_check():
        """健康检查端点"""
        return {
            "code": 0,
            "message": "服务运行正常",
            "data": {
                "status": "healthy",
                "service": settings.PROJECT_NAME,
                "version": settings.PROJECT_VERSION,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    


    # 根路径
    @app.get("/")
    async def root():
        """根路径"""
        return {
            "code": 0,
            "message": "欢迎使用API服务",
            "data": {
                "service": settings.PROJECT_NAME,
                "version": settings.PROJECT_VERSION,
                "docs": "/docs" if settings.DEBUG else "Documentation not available in production"
            }
        }

    return app


async def create_tables():
    """
    创建数据库表
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表创建完成")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    在应用启动前执行初始化操作，在应用关闭时执行清理操作
    """
    # 启动时执行
    logger.info(f"启动 {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}")
    
    # 创建数据库表
    await create_tables()
    
    logger.info("应用启动完成")
    
    # 打印服务状态信息
    print("\n" + "="*60)
    print(f"🚀 {settings.PROJECT_NAME} 启动成功!")
    print("="*60)
    print(f"📊 服务器状态：✅ 正常运行")
    print(f"🌐 访问地址：http://localhost:{settings.PORT}")
    if settings.DEBUG:
        print(f"📚 API 文档：http://localhost:{settings.PORT}/docs")
        print(f"📖 ReDoc 文档：http://localhost:{settings.PORT}/redoc")
    print(f"🔍 健康检查：http://localhost:{settings.PORT}/health")
    print(f"📝 版本信息：v{settings.PROJECT_VERSION}")
    print(f"🔧 运行模式：{'开发模式' if settings.DEBUG else '生产模式'}")
    print("="*60 + "\n")
    
    yield
    
    # 关闭时执行
    logger.info("应用正在关闭...")
    
    # 关闭数据库连接
    await engine.dispose()
    
    logger.info("应用已关闭")


# 创建应用实例
app = create_app()


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