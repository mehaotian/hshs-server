import time
import uuid
from typing import Callable, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import JSONResponse
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.logger import logger, log_request, log_security_event
from app.core.response import ResponseBuilder


class RequestIDMiddleware(BaseHTTPMiddleware):
    """请求ID中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # 添加请求ID到响应头
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """日志中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # 获取客户端IP
        client_ip = self._get_client_ip(request)
        
        # 记录请求开始
        logger.info(
            f"Request started: {request.method} {request.url.path} - IP: {client_ip}",
            extra={"request_id": getattr(request.state, "request_id", None)}
        )
        
        try:
            response = await call_next(request)
            
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录请求完成
            log_request(
                method=request.method,
                url=str(request.url),
                status_code=response.status_code,
                duration=process_time,
                user_id=getattr(request.state, "user_id", None),
                ip=client_ip
            )
            
            # 添加处理时间到响应头
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录异常
            try:
                error_msg = str(e).replace("{", "[").replace("}", "]")
                logger.error(
                    f"Request failed: {request.method} {request.url.path} - "
                    f"Error: {error_msg} - Duration: {process_time:.3f}s - IP: {client_ip}",
                    extra={"request_id": getattr(request.state, "request_id", None)}
                )
            except Exception as log_error:
                logger.error(
                    f"Request failed: {request.method} {request.url.path} - "
                    f"Error: [Log formatting error] - Duration: {process_time:.3f}s - IP: {client_ip}",
                    extra={"request_id": getattr(request.state, "request_id", None)}
                )
            
            raise
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        # 检查代理头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # 返回直接连接的IP
        return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """限流中间件"""
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls  # 允许的调用次数
        self.period = period  # 时间窗口（秒）
        self.clients = defaultdict(list)  # 客户端请求记录
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 获取客户端标识
        client_id = self._get_client_id(request)
        
        # 检查是否超过限制
        if self._is_rate_limited(client_id):
            log_security_event(
                "RATE_LIMIT_EXCEEDED",
                ip=self._get_client_ip(request),
                details=f"Client: {client_id}, Limit: {self.calls}/{self.period}s"
            )
            
            return ResponseBuilder.rate_limit_exceeded(
                message=f"Rate limit exceeded. Maximum {self.calls} requests per {self.period} seconds.",
                retry_after=self.period,
                request_id=getattr(request.state, "request_id", None)
            )
        
        # 记录请求
        self._record_request(client_id)
        
        return await call_next(request)
    
    def _get_client_id(self, request: Request) -> str:
        """获取客户端标识"""
        # 优先使用用户ID
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"
        
        # 使用IP地址
        return f"ip:{self._get_client_ip(request)}"
    
    def _get_client_ip(self, request: Request) -> str:
        """获取客户端IP地址"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return request.client.host if request.client else "unknown"
    
    def _is_rate_limited(self, client_id: str) -> bool:
        """检查是否超过限制"""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=self.period)
        
        # 清理过期记录
        self.clients[client_id] = [
            timestamp for timestamp in self.clients[client_id]
            if timestamp > cutoff
        ]
        
        # 检查是否超过限制
        return len(self.clients[client_id]) >= self.calls
    
    def _record_request(self, client_id: str):
        """记录请求"""
        self.clients[client_id].append(datetime.utcnow())


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # 添加安全头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # CSP头（根据需要调整）
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "img-src 'self' data: https:; "
            "font-src 'self' https://cdn.jsdelivr.net; "
            "connect-src 'self'; "
            "worker-src 'self' blob:; "
            "frame-ancestors 'none';"
        )
        response.headers["Content-Security-Policy"] = csp
        
        return response


class DatabaseMiddleware(BaseHTTPMiddleware):
    """数据库中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 在请求开始时可以进行数据库连接检查等操作
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            # 在这里可以处理数据库相关的异常
            logger.error(f"Database middleware error: {str(e)}")
            raise


class CompressionMiddleware(BaseHTTPMiddleware):
    """压缩中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # 检查是否支持gzip压缩
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" in accept_encoding.lower():
            # 对于大于1KB的响应进行压缩
            if hasattr(response, "body") and len(response.body) > 1024:
                import gzip
                compressed_body = gzip.compress(response.body)
                if len(compressed_body) < len(response.body):
                    response.body = compressed_body
                    response.headers["content-encoding"] = "gzip"
                    response.headers["content-length"] = str(len(compressed_body))
        
        return response


class HealthCheckMiddleware(BaseHTTPMiddleware):
    """健康检查中间件"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 健康检查端点直接返回
        if request.url.path in ["/ping", "/status"]:
            return JSONResponse(
                status_code=200,
                content={
                    "code": 0,
                    "message": "服务运行正常",
                    "data": {
                        "status": "healthy",
                        "timestamp": datetime.utcnow().isoformat(),
                        "version": settings.APP_VERSION
                    }
                }
            )
        
        return await call_next(request)


def setup_middleware(app):
    """设置中间件"""
    
    # 健康检查中间件（最先执行）
    app.add_middleware(HealthCheckMiddleware)
    
    # 安全头中间件
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 压缩中间件
    if settings.ENABLE_COMPRESSION:
        app.add_middleware(CompressionMiddleware)
    
    # 限流中间件
    if settings.ENABLE_RATE_LIMIT:
        app.add_middleware(
            RateLimitMiddleware,
            calls=settings.RATE_LIMIT_CALLS,
            period=settings.RATE_LIMIT_PERIOD
        )
    
    # 数据库中间件
    app.add_middleware(DatabaseMiddleware)
    
    # 日志中间件
    app.add_middleware(LoggingMiddleware)
    
    # 请求ID中间件
    app.add_middleware(RequestIDMiddleware)
    
    # CORS中间件
    if settings.CORS_ORIGINS:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Request-ID", "X-Process-Time"]
        )
    
    # 会话中间件
    if settings.SECRET_KEY:
        app.add_middleware(
            SessionMiddleware,
            secret_key=settings.SECRET_KEY,
            max_age=settings.SESSION_MAX_AGE
        )
    
    # 可信主机中间件
    if settings.ALLOWED_HOSTS:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS
        )


# 自定义中间件装饰器
def timing_middleware(func):
    """计时中间件装饰器"""
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"Function {func.__name__} executed in {duration:.3f}s")
            return result
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Function {func.__name__} failed after {duration:.3f}s: {str(e)}")
            raise
    return wrapper


def cache_middleware(ttl: int = 300):
    """缓存中间件装饰器"""
    cache = {}
    
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # 检查缓存
            if cache_key in cache:
                cached_data, timestamp = cache[cache_key]
                if time.time() - timestamp < ttl:
                    logger.debug(f"Cache hit for {func.__name__}")
                    return cached_data
                else:
                    # 缓存过期，删除
                    del cache[cache_key]
            
            # 执行函数
            result = await func(*args, **kwargs)
            
            # 存储到缓存
            cache[cache_key] = (result, time.time())
            logger.debug(f"Cache stored for {func.__name__}")
            
            return result
        return wrapper
    return decorator