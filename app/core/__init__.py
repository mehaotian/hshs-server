"""核心模块

包含应用程序的核心功能：
- 配置管理
- 数据库连接
- 认证授权
- 日志记录
- 异常处理
- 响应格式化
- 中间件
"""

from .config import settings
from .database import (
    engine,
    AsyncSessionLocal,
    get_db,
    init_db,
    close_db,
    DatabaseManager
)
from .auth import (
    AuthManager,
    get_current_user,
    get_current_active_user,
    require_permission,
    require_role,
    require_roles
)
from .logger import (
    logger,
    get_logger,
    log_request,
    log_database_query,
    log_security_event,
    log_auth_attempt,
    log_permission_denied,
    log_file_operation,
    log_ai_request,
    log_background_task,
    log_performance_metric
)
from .exceptions import (
    BaseCustomException,
    BusinessException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    ResourceNotFoundException,
    DuplicateResourceException,
    FileOperationException,
    ExternalServiceException,
    RateLimitException,
    DatabaseException,
    ConfigurationException,
    register_exception_handlers,
    raise_not_found,
    raise_duplicate,
    raise_validation_error,
    raise_auth_error,
    raise_permission_error,
    raise_business_error,
    raise_external_service_error,
    raise_file_operation_error
)
from .response import (
    ResponseBuilder,
    ResponseFormatter,
    success_response,
    error_response,
    paginated_response
)
from .middleware import (
    setup_middleware,
    timing_middleware,
    cache_middleware
)

__all__ = [
    # 配置
    "settings",
    
    # 数据库
    "engine",
    "AsyncSessionLocal",
    "get_db",
    "init_db",
    "close_db",
    "DatabaseManager",
    
    # 认证
    "AuthManager",
    "get_current_user",
    "get_current_active_user",
    "require_permission",
    "require_role",
    "require_roles",
    
    # 日志
    "logger",
    "get_logger",
    "log_request",
    "log_database_query",
    "log_security_event",
    "log_auth_attempt",
    "log_permission_denied",
    "log_file_operation",
    "log_ai_request",
    "log_background_task",
    "log_performance_metric",
    
    # 异常
    "BaseCustomException",
    "BusinessException",
    "ValidationException",
    "AuthenticationException",
    "AuthorizationException",
    "ResourceNotFoundException",
    "DuplicateResourceException",
    "FileOperationException",
    "ExternalServiceException",
    "RateLimitException",
    "DatabaseException",
    "ConfigurationException",
    "register_exception_handlers",
    "raise_not_found",
    "raise_duplicate",
    "raise_validation_error",
    "raise_auth_error",
    "raise_permission_error",
    "raise_business_error",
    "raise_external_service_error",
    "raise_file_operation_error",
    
    # 响应
    "ResponseBuilder",
    "ResponseFormatter",
    "success_response",
    "error_response",
    "paginated_response",
    
    # 中间件
    "setup_middleware",
    "timing_middleware",
    "cache_middleware",
]