from typing import Any, Dict, Optional, Union
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from pydantic import ValidationError
import traceback

from app.core.logger import logger


class BaseCustomException(Exception):
    """自定义异常基类"""
    
    def __init__(
        self,
        message: str,
        error_code: str = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Dict[str, Any] = None
    ):
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class BusinessException(BaseCustomException):
    """业务异常"""
    pass


class ValidationException(BaseCustomException):
    """验证异常"""
    
    def __init__(self, message: str, field: str = None, **kwargs):
        super().__init__(message, **kwargs)
        if field:
            self.details["field"] = field


class AuthenticationException(BaseCustomException):
    """认证异常"""
    
    def __init__(self, message: str = "Authentication failed", **kwargs):
        kwargs.setdefault("status_code", status.HTTP_401_UNAUTHORIZED)
        super().__init__(message, **kwargs)


class AuthorizationException(BaseCustomException):
    """授权异常"""
    
    def __init__(self, message: str = "Access denied", **kwargs):
        kwargs.setdefault("status_code", status.HTTP_403_FORBIDDEN)
        super().__init__(message, **kwargs)


class ResourceNotFoundException(BaseCustomException):
    """资源未找到异常"""
    
    def __init__(self, resource: str, resource_id: Union[int, str] = None, **kwargs):
        message = f"{resource} not found"
        if resource_id:
            message += f" (ID: {resource_id})"
        
        kwargs.setdefault("status_code", status.HTTP_404_NOT_FOUND)
        super().__init__(message, **kwargs)
        self.details["resource"] = resource
        if resource_id:
            self.details["resource_id"] = resource_id


class DuplicateResourceException(BaseCustomException):
    """资源重复异常"""
    
    def __init__(self, resource: str, field: str = None, value: str = None, **kwargs):
        message = f"{resource} already exists"
        if field and value:
            message += f" ({field}: {value})"
        
        kwargs.setdefault("status_code", status.HTTP_409_CONFLICT)
        super().__init__(message, **kwargs)
        self.details["resource"] = resource
        if field:
            self.details["field"] = field
        if value:
            self.details["value"] = value


class FileOperationException(BaseCustomException):
    """文件操作异常"""
    
    def __init__(self, operation: str, file_path: str = None, **kwargs):
        message = f"File {operation} failed"
        if file_path:
            message += f" for {file_path}"
        
        super().__init__(message, **kwargs)
        self.details["operation"] = operation
        if file_path:
            self.details["file_path"] = file_path


class ExternalServiceException(BaseCustomException):
    """外部服务异常"""
    
    def __init__(self, service: str, operation: str = None, **kwargs):
        message = f"External service '{service}' error"
        if operation:
            message += f" during {operation}"
        
        kwargs.setdefault("status_code", status.HTTP_502_BAD_GATEWAY)
        super().__init__(message, **kwargs)
        self.details["service"] = service
        if operation:
            self.details["operation"] = operation


class RateLimitException(BaseCustomException):
    """限流异常"""
    
    def __init__(self, message: str = "Rate limit exceeded", **kwargs):
        kwargs.setdefault("status_code", status.HTTP_429_TOO_MANY_REQUESTS)
        super().__init__(message, **kwargs)


class DatabaseException(BaseCustomException):
    """数据库异常"""
    
    def __init__(self, message: str = "Database operation failed", **kwargs):
        kwargs.setdefault("status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)
        super().__init__(message, **kwargs)


class ConfigurationException(BaseCustomException):
    """配置异常"""
    
    def __init__(self, message: str = "Configuration error", **kwargs):
        kwargs.setdefault("status_code", status.HTTP_500_INTERNAL_SERVER_ERROR)
        super().__init__(message, **kwargs)


def create_error_response(
    error_code: str,
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    details: Dict[str, Any] = None,
    request_id: str = None
) -> Dict[str, Any]:
    """创建错误响应"""
    response = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
        },
        "data": None
    }
    
    if details:
        response["error"]["details"] = details
    
    if request_id:
        response["request_id"] = request_id
    
    return response


async def custom_exception_handler(request: Request, exc: BaseCustomException):
    """自定义异常处理器"""
    request_id = getattr(request.state, "request_id", None)
    
    # 记录异常日志
    logger.error(
        f"Custom Exception: {exc.error_code} - {exc.message} - "
        f"Path: {request.url.path} - Method: {request.method} - "
        f"Request ID: {request_id}",
        extra={"exception": exc, "request_id": request_id}
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details,
            request_id=request_id
        )
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理器"""
    request_id = getattr(request.state, "request_id", None)
    
    # 记录异常日志
    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail} - "
        f"Path: {request.url.path} - Method: {request.method} - "
        f"Request ID: {request_id}",
        extra={"request_id": request_id}
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=create_error_response(
            error_code="HTTP_ERROR",
            message=str(exc.detail),
            request_id=request_id
        )
    )


def translate_validation_error(error_type: str, error_msg: str, field: str = None) -> str:
    """将Pydantic验证错误信息翻译为中文"""
    
    # 错误类型映射表
    error_type_mapping = {
        "missing": "此字段为必填项",
        "string_too_short": "字符串长度不足",
        "string_too_long": "字符串长度过长",
        "value_error": "值错误",
        "type_error": "类型错误",
        "value_error.email": "邮箱格式不正确",
        "value_error.url": "URL格式不正确",
        "value_error.number.not_gt": "数值必须大于指定值",
        "value_error.number.not_ge": "数值必须大于等于指定值",
        "value_error.number.not_lt": "数值必须小于指定值",
        "value_error.number.not_le": "数值必须小于等于指定值",
        "value_error.list.min_items": "列表项目数量不足",
        "value_error.list.max_items": "列表项目数量过多",
        "value_error.datetime": "日期时间格式不正确",
        "value_error.uuid": "UUID格式不正确",
        "value_error.json": "JSON格式不正确",
    }
    
    # 处理自定义验证器返回的错误信息，去掉"Value error, "前缀
    if "Value error, " in error_msg:
        clean_msg = error_msg.replace("Value error, ", "")
        return clean_msg
    
    # 特殊错误信息处理
    if "email" in error_msg.lower() and "valid" in error_msg.lower():
        return "邮箱地址格式不正确"
    
    # 处理邮箱验证的具体错误信息
    if "The email address is not valid" in error_msg:
        return "邮箱地址格式不正确"
    
    if "exactly one @-sign" in error_msg:
        return "邮箱地址格式不正确，必须包含一个@符号"
    
    # 处理字符串长度验证
    if "String should have at least" in error_msg and "characters" in error_msg:
        # 提取最小字符数
        import re
        match = re.search(r'at least (\d+) characters', error_msg)
        if match:
            min_chars = match.group(1)
            return f"至少需要{min_chars}个字符"
        return "字符串长度不足"
    
    if "String should have at most" in error_msg and "characters" in error_msg:
        # 提取最大字符数
        import re
        match = re.search(r'at most (\d+) characters', error_msg)
        if match:
            max_chars = match.group(1)
            return f"最多允许{max_chars}个字符"
        return "字符串长度过长"
    
    # 兼容旧版本的字符串长度验证
    if "at least" in error_msg and "characters" in error_msg:
        import re
        match = re.search(r'at least (\d+) characters', error_msg)
        if match:
            min_chars = match.group(1)
            return f"至少需要{min_chars}个字符"
        return "字符串长度不足"
    
    if "at most" in error_msg and "characters" in error_msg:
        import re
        match = re.search(r'at most (\d+) characters', error_msg)
        if match:
            max_chars = match.group(1)
            return f"最多允许{max_chars}个字符"
        return "字符串长度过长"
    
    if "Field required" in error_msg:
        return "此字段为必填项"
    
    if "ensure this value is greater than" in error_msg:
        import re
        match = re.search(r'greater than (\d+)', error_msg)
        if match:
            min_val = match.group(1)
            return f"值必须大于{min_val}"
        return "值必须大于指定值"
    
    if "ensure this value is less than" in error_msg:
        import re
        match = re.search(r'less than (\d+)', error_msg)
        if match:
            max_val = match.group(1)
            return f"值必须小于{max_val}"
        return "值必须小于指定值"
    
    # 处理自定义验证器的中文错误信息（如果已经是中文，直接返回）
    if any(ord(char) > 127 for char in error_msg):
        return error_msg
    
    # 使用错误类型映射
    if error_type in error_type_mapping:
        return error_type_mapping[error_type]
    
    # 如果没有找到对应的翻译，返回原始错误信息
    return error_msg


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证异常处理器"""
    request_id = getattr(request.state, "request_id", None)
    
    # 格式化验证错误
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"][1:])  # 跳过 'body'
        
        # 翻译错误信息为中文
        translated_message = translate_validation_error(
            error["type"], 
            error["msg"], 
            field
        )
        
        errors.append({
            "field": field,
            "message": translated_message,
            "type": error["type"]
        })
    
    # 记录异常日志
    logger.warning(
        f"Validation Error: {len(errors)} validation errors - "
        f"Path: {request.url.path} - Method: {request.method} - "
        f"Request ID: {request_id}",
        extra={"validation_errors": errors, "request_id": request_id}
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=create_error_response(
            error_code="VALIDATION_ERROR",
            message="请求数据验证失败",
            details={"validation_errors": errors},
            request_id=request_id
        )
    )


async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    """SQLAlchemy异常处理器"""
    request_id = getattr(request.state, "request_id", None)
    
    # 记录异常日志
    logger.error(
        f"Database Error: {type(exc).__name__} - {str(exc)} - "
        f"Path: {request.url.path} - Method: {request.method} - "
        f"Request ID: {request_id}",
        extra={"exception": exc, "request_id": request_id}
    )
    
    # 处理特定的数据库异常
    if isinstance(exc, IntegrityError):
        # 完整性约束违反
        error_message = "Data integrity constraint violation"
        if "duplicate key" in str(exc).lower():
            error_message = "Duplicate entry found"
        elif "foreign key" in str(exc).lower():
            error_message = "Referenced resource not found"
        
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=create_error_response(
                error_code="INTEGRITY_ERROR",
                message=error_message,
                request_id=request_id
            )
        )
    
    # 通用数据库错误
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            error_code="DATABASE_ERROR",
            message="Database operation failed",
            request_id=request_id
        )
    )


async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理器"""
    request_id = getattr(request.state, "request_id", None)
    
    # 记录异常日志
    logger.error(
        f"Unhandled Exception: {type(exc).__name__} - {str(exc)} - "
        f"Path: {request.url.path} - Method: {request.method} - "
        f"Request ID: {request_id}\n{traceback.format_exc()}",
        extra={"exception": exc, "request_id": request_id}
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=create_error_response(
            error_code="INTERNAL_ERROR",
            message="Internal server error",
            request_id=request_id
        )
    )


def register_exception_handlers(app):
    """注册异常处理器"""
    # 自定义异常
    app.add_exception_handler(BaseCustomException, custom_exception_handler)
    
    # HTTP异常
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    
    # 验证异常
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    
    # 数据库异常
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    
    # 通用异常（必须放在最后）
    app.add_exception_handler(Exception, general_exception_handler)


# 常用异常快捷方式
def raise_not_found(resource: str, resource_id: Union[int, str] = None):
    """抛出资源未找到异常"""
    raise ResourceNotFoundException(resource, resource_id)


def raise_duplicate(resource: str, field: str = None, value: str = None):
    """抛出资源重复异常"""
    raise DuplicateResourceException(resource, field, value)


def raise_validation_error(message: str, field: str = None):
    """抛出验证异常"""
    raise ValidationException(message, field)


def raise_auth_error(message: str = "Authentication failed"):
    """抛出认证异常"""
    raise AuthenticationException(message)


def raise_permission_error(message: str = "Access denied"):
    """抛出权限异常"""
    raise AuthorizationException(message)


def raise_business_error(message: str, error_code: str = None):
    """抛出业务异常"""
    raise BusinessException(message, error_code)


def raise_external_service_error(service: str, operation: str = None):
    """抛出外部服务异常"""
    raise ExternalServiceException(service, operation)


def raise_file_operation_error(operation: str, file_path: str = None):
    """抛出文件操作异常"""
    raise FileOperationException(operation, file_path)