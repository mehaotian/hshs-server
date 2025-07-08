import sys
import os
from pathlib import Path
from typing import Dict, Any
from loguru import logger
from app.core.config import settings


class LoggerManager:
    """日志管理器"""
    
    def __init__(self):
        self.logger = logger
        self._setup_logger()
    
    def _setup_logger(self):
        """设置日志配置"""
        # 移除默认处理器
        self.logger.remove()
        
        # 确保日志目录存在
        log_dir = Path(settings.LOG_FILE).parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # 控制台输出配置
        console_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
        
        # 文件输出配置
        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        )
        
        # 添加控制台处理器
        if settings.DEBUG:
            self.logger.add(
                sys.stdout,
                format=console_format,
                level="DEBUG",
                colorize=True,
                backtrace=True,
                diagnose=True
            )
        else:
            self.logger.add(
                sys.stdout,
                format=console_format,
                level="INFO",
                colorize=True
            )
        
        # 添加文件处理器 - 所有日志
        self.logger.add(
            log_dir / "app.log",
            format=file_format,
            level="INFO",
            rotation="10 MB",
            retention="30 days",
            compression="zip",
            encoding="utf-8"
        )
        
        # 添加错误日志文件处理器
        self.logger.add(
            log_dir / "error.log",
            format=file_format,
            level="ERROR",
            rotation="10 MB",
            retention="90 days",
            compression="zip",
            encoding="utf-8"
        )
        
        # 添加访问日志文件处理器
        self.logger.add(
            log_dir / "access.log",
            format=file_format,
            level="INFO",
            rotation="10 MB",
            retention="30 days",
            compression="zip",
            encoding="utf-8",
            filter=lambda record: "access" in record["extra"]
        )
        
        # 添加数据库日志文件处理器
        self.logger.add(
            log_dir / "database.log",
            format=file_format,
            level="DEBUG" if settings.DEBUG else "INFO",
            rotation="10 MB",
            retention="7 days",
            compression="zip",
            encoding="utf-8",
            filter=lambda record: "database" in record["extra"]
        )
        
        # 添加安全日志文件处理器
        self.logger.add(
            log_dir / "security.log",
            format=file_format,
            level="WARNING",
            rotation="10 MB",
            retention="180 days",
            compression="zip",
            encoding="utf-8",
            filter=lambda record: "security" in record["extra"]
        )
    
    def get_logger(self, name: str = None):
        """获取日志器"""
        if name:
            return self.logger.bind(name=name)
        return self.logger
    
    def log_request(self, method: str, url: str, status_code: int, 
                   duration: float, user_id: int = None, ip: str = None):
        """记录请求日志"""
        self.logger.bind(access=True).info(
            f"{method} {url} - {status_code} - {duration:.3f}s - "
            f"User: {user_id or 'Anonymous'} - IP: {ip or 'Unknown'}"
        )
    
    def log_database_query(self, query: str, duration: float = None, 
                          params: Dict[str, Any] = None):
        """记录数据库查询日志"""
        log_msg = f"Database Query: {query}"
        if duration is not None:
            log_msg += f" - Duration: {duration:.3f}s"
        if params:
            log_msg += f" - Params: {params}"
        
        self.logger.bind(database=True).debug(log_msg)
    
    def log_security_event(self, event_type: str, user_id: int = None, 
                          ip: str = None, details: str = None):
        """记录安全事件日志"""
        log_msg = f"Security Event: {event_type}"
        if user_id:
            log_msg += f" - User: {user_id}"
        if ip:
            log_msg += f" - IP: {ip}"
        if details:
            log_msg += f" - Details: {details}"
        
        self.logger.bind(security=True).warning(log_msg)
    
    def log_auth_attempt(self, username: str, success: bool, ip: str = None):
        """记录认证尝试"""
        status = "SUCCESS" if success else "FAILED"
        self.log_security_event(
            "AUTH_ATTEMPT",
            details=f"Username: {username}, Status: {status}, IP: {ip}"
        )
    
    def log_permission_denied(self, user_id: int, resource: str, 
                             action: str, ip: str = None):
        """记录权限拒绝"""
        self.log_security_event(
            "PERMISSION_DENIED",
            user_id=user_id,
            ip=ip,
            details=f"Resource: {resource}, Action: {action}"
        )
    
    def log_file_operation(self, operation: str, file_path: str, 
                          user_id: int = None, success: bool = True):
        """记录文件操作"""
        level = "info" if success else "error"
        status = "SUCCESS" if success else "FAILED"
        
        getattr(self.logger, level)(
            f"File Operation: {operation} - {file_path} - "
            f"Status: {status} - User: {user_id or 'System'}"
        )
    
    def log_ai_request(self, service: str, operation: str, 
                      duration: float = None, success: bool = True,
                      error: str = None):
        """记录AI服务请求"""
        level = "info" if success else "error"
        status = "SUCCESS" if success else "FAILED"
        
        log_msg = f"AI Request: {service} - {operation} - Status: {status}"
        if duration is not None:
            log_msg += f" - Duration: {duration:.3f}s"
        if error:
            log_msg += f" - Error: {error}"
        
        getattr(self.logger, level)(log_msg)
    
    def log_background_task(self, task_name: str, status: str, 
                           duration: float = None, details: str = None):
        """记录后台任务"""
        log_msg = f"Background Task: {task_name} - Status: {status}"
        if duration is not None:
            log_msg += f" - Duration: {duration:.3f}s"
        if details:
            log_msg += f" - Details: {details}"
        
        if status.upper() in ["SUCCESS", "COMPLETED"]:
            self.logger.info(log_msg)
        elif status.upper() in ["FAILED", "ERROR"]:
            self.logger.error(log_msg)
        else:
            self.logger.info(log_msg)
    
    def log_performance_metric(self, metric_name: str, value: float, 
                              unit: str = None, context: Dict[str, Any] = None):
        """记录性能指标"""
        log_msg = f"Performance Metric: {metric_name} = {value}"
        if unit:
            log_msg += f" {unit}"
        if context:
            log_msg += f" - Context: {context}"
        
        self.logger.info(log_msg)
    
    def configure_uvicorn_logging(self):
        """配置Uvicorn日志"""
        # 禁用uvicorn的默认日志配置
        import logging
        
        # 获取uvicorn相关的logger
        uvicorn_logger = logging.getLogger("uvicorn")
        uvicorn_access_logger = logging.getLogger("uvicorn.access")
        
        # 清除现有处理器
        uvicorn_logger.handlers.clear()
        uvicorn_access_logger.handlers.clear()
        
        # 设置日志级别
        uvicorn_logger.setLevel(logging.INFO)
        uvicorn_access_logger.setLevel(logging.INFO)
        
        # 添加自定义处理器
        class InterceptHandler(logging.Handler):
            def emit(self, record):
                # 获取对应的loguru级别
                try:
                    level = self.logger.level(record.levelname).name
                except ValueError:
                    level = record.levelno
                
                # 查找调用者
                frame, depth = logging.currentframe(), 2
                while frame.f_code.co_filename == logging.__file__:
                    frame = frame.f_back
                    depth += 1
                
                self.logger.opt(depth=depth, exception=record.exc_info).log(
                    level, record.getMessage()
                )
        
        # 添加拦截处理器
        intercept_handler = InterceptHandler()
        uvicorn_logger.addHandler(intercept_handler)
        uvicorn_access_logger.addHandler(intercept_handler)
        
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                },
            },
            "handlers": {
                "default": {
                    "formatter": "default",
                    "class": "app.core.logger.InterceptHandler",
                },
            },
            "root": {
                "level": "INFO",
                "handlers": ["default"],
            },
        }


# 创建全局日志管理器实例
logger_manager = LoggerManager()

# 导出常用的日志器
logger = logger_manager.get_logger()
get_logger = logger_manager.get_logger

# 导出日志记录方法
log_request = logger_manager.log_request
log_database_query = logger_manager.log_database_query
log_security_event = logger_manager.log_security_event
log_auth_attempt = logger_manager.log_auth_attempt
log_permission_denied = logger_manager.log_permission_denied
log_file_operation = logger_manager.log_file_operation
log_ai_request = logger_manager.log_ai_request
log_background_task = logger_manager.log_background_task
log_performance_metric = logger_manager.log_performance_metric