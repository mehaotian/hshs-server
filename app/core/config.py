from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, List, Union
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """应用配置类"""
    
    model_config = {
        "env_file": BASE_DIR / ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }
    
    # 应用基础配置
    APP_NAME: str = "绘声绘社管理系统"
    PROJECT_NAME: str = "绘声绘社管理系统"
    PROJECT_DESCRIPTION: str = "绘声绘社有声剧本管理系统 - 提供剧本管理、音频处理、角色分配等功能"
    APP_VERSION: str = "1.0.0"
    PROJECT_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True
    
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./hshs_db.sqlite"
    DATABASE_ECHO: bool = False  # 是否打印SQL语句
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    
    # Redis配置
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None
    
    # JWT配置
    SECRET_KEY: str = "your-super-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30   # 从.env文件读取，默认30分钟
    REFRESH_TOKEN_EXPIRE_DAYS: int = 14     # 14天，平衡安全性和用户体验
    
    # 跨域配置
    BACKEND_CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080,http://localhost:5173"
    CORS_ORIGINS: Optional[List[str]] = None
    
    # 中间件配置
    ENABLE_COMPRESSION: bool = True
    ENABLE_RATE_LIMIT: bool = True
    RATE_LIMIT_CALLS: int = 100
    RATE_LIMIT_PERIOD: int = 60
    SESSION_MAX_AGE: int = 3600  # 1小时
    ALLOWED_HOSTS: Optional[List[str]] = None
    
    def get_cors_origins(self) -> List[str]:
        """获取 CORS 来源列表"""
        if isinstance(self.BACKEND_CORS_ORIGINS, str):
            if ',' in self.BACKEND_CORS_ORIGINS:
                return [i.strip() for i in self.BACKEND_CORS_ORIGINS.split(',') if i.strip()]
            elif self.BACKEND_CORS_ORIGINS.strip():
                return [self.BACKEND_CORS_ORIGINS.strip()]
            else:
                return []
        return []
    
    # 文件上传配置
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")
    STATIC_FILES_DIR: str = str(BASE_DIR / "static")
    MAX_FILE_SIZE: int = 100 * 1024 * 1024  # 100MB
    ALLOWED_AUDIO_EXTENSIONS: List[str] = [".mp3", ".wav", ".flac", ".m4a"]
    ALLOWED_SCRIPT_EXTENSIONS: List[str] = [".txt", ".docx", ".pdf"]
    
    # 阿里云OSS配置（可选）
    OSS_ACCESS_KEY_ID: Optional[str] = None
    OSS_ACCESS_KEY_SECRET: Optional[str] = None
    OSS_BUCKET_NAME: Optional[str] = None
    OSS_ENDPOINT: Optional[str] = None
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = str(BASE_DIR / "logs" / "app.log")
    
    # Celery配置
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # 邮件配置
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = None
    
    # 分页配置
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    



# 创建全局配置实例
settings = Settings()

# 确保必要的目录存在
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.STATIC_FILES_DIR, exist_ok=True)
os.makedirs(os.path.dirname(settings.LOG_FILE), exist_ok=True)