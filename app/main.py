from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import time

from app.core.config import settings
from app.core.database import init_db
from app.core.exceptions import register_exception_handlers
from app.api.v1 import auth, users, scripts, audios, roles

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("Starting application...")
    
    # 初始化数据库
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # 关闭时执行
    logger.info("Shutting down application...")


# 创建FastAPI应用实例
app = FastAPI(
    title=settings.APP_NAME,
    description="话说话说 - 剧本杀配音平台 API",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# 注册异常处理器
register_exception_handlers(app)

# 添加CORS中间件
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 添加可信主机中间件（生产环境）
if not settings.DEBUG:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# 注册路由
app.include_router(
    auth.router,
    prefix="/api/v1/auth",
    tags=["认证"]
)

app.include_router(
    users.router,
    prefix="/api/v1/users",
    tags=["用户管理"]
)

app.include_router(
    scripts.router,
    prefix="/api/v1/scripts",
    tags=["剧本管理"]
)

app.include_router(
    audios.router,
    prefix="/api/v1/audios",
    tags=["音频管理"]
)

app.include_router(
    roles.router,
    prefix="/api/v1/roles",
    tags=["角色管理"]
)


@app.get("/", tags=["根路径"])
async def root():
    """根路径"""
    return {
        "message": "欢迎使用话说话说API",
        "version": "1.0.0",
        "docs": "/docs" if settings.DEBUG else "文档已禁用"
    }


@app.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z"
    }


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """请求日志中间件"""
    start_time = time.time()
    
    # 记录请求信息
    logger.info(
        f"Request: {request.method} {request.url.path} "
        f"from {request.client.host if request.client else 'unknown'}"
    )
    
    response = await call_next(request)
    
    # 记录响应信息
    process_time = time.time() - start_time
    logger.info(
        f"Response: {response.status_code} "
        f"in {process_time:.4f}s"
    )
    
    return response


if __name__ == "__main__":
    import uvicorn
    import time
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )