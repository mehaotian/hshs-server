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
    
    def __init__(self, message: str, business_code: int = 1000, **kwargs):
        # 业务异常统一返回HTTP 200，通过business_code区分具体错误
        kwargs.setdefault("status_code", status.HTTP_200_OK)
        super().__init__(message, **kwargs)
        self.business_code = business_code


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


def translate_error_message(exc: BaseCustomException) -> str:
    """翻译错误信息为中文"""
    if isinstance(exc, DuplicateResourceException):
        # 资源名称映射
        resource_names = {
            "Role": "角色",
            "User": "用户",
            "Permission": "权限",
            "Script": "剧本",
            "Audio": "音频",
            "Project": "项目"
        }
        
        # 字段名称映射
        field_names = {
            "name": "名称",
            "username": "用户名",
            "email": "邮箱",
            "title": "标题"
        }
        
        resource = exc.details.get("resource", "")
        field = exc.details.get("field", "")
        value = exc.details.get("value", "")
        
        resource_cn = resource_names.get(resource, resource)
        field_cn = field_names.get(field, field)
        
        if field and value:
            return f"{resource_cn}已存在 ({field_cn}: {value})"
        else:
            return f"{resource_cn}已存在"
    
    elif isinstance(exc, ResourceNotFoundException):
        resource_names = {
            "Role": "角色",
            "User": "用户",
            "Permission": "权限",
            "Script": "剧本",
            "Audio": "音频",
            "Project": "项目"
        }
        
        resource = exc.details.get("resource", "")
        resource_cn = resource_names.get(resource, resource)
        return f"{resource_cn}不存在"
    
    elif isinstance(exc, ValidationException):
        # 对于验证异常，直接返回原始消息（通常已经是中文）
        return exc.message
    
    elif isinstance(exc, AuthenticationException):
        return "认证失败，请重新登录"
    
    elif isinstance(exc, AuthorizationException):
        return "权限不足，无法执行此操作"
    
    # 其他异常类型保持原始消息
    return exc.message


async def custom_exception_handler(request: Request, exc: BaseCustomException):
    """自定义异常处理器"""
    request_id = getattr(request.state, "request_id", None)
    
    # 映射自定义异常到业务状态码
    exception_code_mapping = {
        "AuthenticationException": 2001,  # 未登录
        "AuthorizationException": 2003,   # 权限不足
        "ResourceNotFoundException": 1005,  # 资源不存在
        "DuplicateResourceException": 1003,  # 资源重复
        "ValidationException": 1003,       # 验证错误
        "BusinessException": 1000,         # 业务异常
        "FileOperationException": 1000,    # 文件操作异常
        "ExternalServiceException": 1000,  # 外部服务异常
        "RateLimitException": 1006,        # 限流异常
        "DatabaseException": 1000,         # 数据库异常
        "ConfigurationException": 1000,    # 配置异常
    }
    
    # 处理BusinessException，使用其自定义的business_code
    if isinstance(exc, BusinessException):
        business_code = exc.business_code
    else:
        business_code = exception_code_mapping.get(exc.error_code, 1000)
    
    # 翻译错误信息为中文
    translated_message = translate_error_message(exc)
    
    # 记录异常日志
    logger.error(
        f"Custom Exception: {exc.error_code} - {exc.message} - "
        f"Path: {request.url.path} - Method: {request.method} - "
        f"Request ID: {request_id}",
        extra={"exception": exc, "request_id": request_id}
    )
    
    return JSONResponse(
        status_code=200,
        content={
            "code": business_code,
            "message": translated_message,
            "data": {}
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理器"""
    request_id = getattr(request.state, "request_id", None)
    
    # 映射HTTP状态码到业务状态码和中文错误消息
    status_code_mapping = {
        401: (2001, "未登录"),  # 未登录
        403: (2003, "权限不足"),  # 权限不足
        404: (1005, "请求路径不存在"),  # 请求路径不存在
        405: (1004, "请求方法不支持"),  # 请求方法不支持
        429: (1006, "请求频率过高"),  # 请求频率过高
        500: (1000, "系统内部错误"),  # 系统内部错误
        503: (1007, "服务暂不可用"),  # 服务暂不可用
    }
    
    # 对于400状态码的业务异常，保留原始错误信息
    if exc.status_code == 400:
        business_code = 1001  # 业务逻辑错误
        error_message = exc.detail  # 保留原始错误信息
    else:
        business_code, error_message = status_code_mapping.get(exc.status_code, (1000, "系统内部错误"))
    
    # 记录异常日志
    logger.warning(
        f"HTTP Exception: {exc.status_code} - {exc.detail} - "
        f"Path: {request.url.path} - Method: {request.method} - "
        f"Request ID: {request_id}",
        extra={"status_code": exc.status_code, "detail": exc.detail, "request_id": request_id}
    )
    
    return JSONResponse(
        status_code=200,
        content={
            "code": business_code,
            "message": error_message,
            "data": {}
        }
    )


def translate_validation_error(error_type: str, error_msg: str, field: str = "") -> str:
    """
    将 Pydantic 验证错误信息翻译为中文
    """
    # 字段名称映射
    field_names = {
        "username": "用户名",
        "email": "邮箱",
        "password": "密码",
        "confirm_password": "确认密码",
        "title": "标题",
        "content": "内容",
        "name": "名称",
        "description": "描述",
        "full_name": "姓名",
        "real_name": "真实姓名",
        "phone": "手机号",
        "wechat": "微信号",
        "bio": "个人简介",
        "avatar_url": "头像",
        "current_password": "当前密码",
        "new_password": "新密码",
        "invitation_code": "邀请码",
        "agree_terms": "服务条款"
    }
    
    field_display = field_names.get(field, field)
    
    # 特殊错误信息处理（优先处理自定义验证器的错误）
    special_error_patterns = {
        "两次输入的密码不一致": "密码和确认密码不匹配",
        "密码必须包含至少一个大写字母": "密码必须包含至少一个大写字母",
        "密码必须包含至少一个小写字母": "密码必须包含至少一个小写字母",
        "密码必须包含至少一个数字": "密码必须包含至少一个数字",
        "密码长度至少8位": "密码长度至少需要8位",
        "用户名只能包含字母、数字、下划线和连字符": "用户名只能包含字母、数字、下划线和连字符",
        "手机号格式不正确": "手机号格式不正确",
        "必须同意服务条款": "必须同意服务条款",
        "Value error, 密码必须包含至少一个大写字母": "密码必须包含至少一个大写字母",
        "Value error, 密码必须包含至少一个小写字母": "密码必须包含至少一个小写字母",
        "Value error, 密码必须包含至少一个数字": "密码必须包含至少一个数字",
        "Value error, 密码长度至少8位": "密码长度至少需要8位",
        "Value error, 两次输入的密码不一致": "密码和确认密码不匹配",
        "Value error, 用户名只能包含字母、数字、下划线和连字符": "用户名只能包含字母、数字、下划线和连字符"
    }
    
    # 检查是否有特殊错误信息
    for pattern, translation in special_error_patterns.items():
        if pattern in error_msg:
            return translation
    
    # 处理必填字段错误
    if error_type == "missing":
        return f"{field_display}为必填项"
    
    # 处理字符串长度错误
    if error_type in ["string_too_short", "string_too_long"]:
        import re
        numbers = re.findall(r'\d+', error_msg)
        if numbers:
            length = numbers[0]
            if error_type == "string_too_short":
                return f"{field_display}至少需要{length}个字符"
            else:
                return f"{field_display}最多允许{length}个字符"
    
    # 处理邮箱验证错误
    if "email" in error_msg.lower() or "value is not a valid email address" in error_msg:
        return "邮箱地址格式不正确"
    
    # 处理自定义验证器返回的中文错误信息
    if "Value error, " in error_msg:
        clean_msg = error_msg.replace("Value error, ", "")
        return clean_msg
    
    # 处理类型错误
    if error_type == "type_error":
        return f"{field_display}数据类型错误"
    
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
            if field == "password":
                return f"密码长度至少需要{min_chars}位"
            return f"{field_display}至少需要{min_chars}个字符"
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
    
    # 默认返回原始消息
    return error_msg


def map_validation_error_to_business_code(field: str, error_type: str, error_msg: str):
    """将验证错误映射为业务状态码"""
    # 翻译错误信息为中文
    translated_msg = translate_validation_error(error_type, error_msg, field)
    
    # 根据字段和错误类型映射具体的业务状态码
    if error_type == "missing":
        return 1002, translated_msg  # 参数缺失
    
    # 用户名相关错误
    if field == "username":
        if "string_too_short" in error_type or "string_too_long" in error_type:
            return 3002, translated_msg  # 用户名长度错误
        elif "value_error" in error_type:
            return 3001, translated_msg  # 用户名格式错误
    
    # 邮箱相关错误
    elif field == "email":
        return 3004, translated_msg  # 邮箱格式错误
    
    # 密码相关错误
    elif field == "password":
        if "string_too_short" in error_type or "string_too_long" in error_type:
            return 3006, translated_msg  # 密码长度错误
        elif "value_error" in error_type:
            return 3007, translated_msg  # 密码格式错误
    
    # 确认密码错误
    elif field == "confirm_password":
        if "value_error" in error_type:
            return 3008, translated_msg  # 密码不匹配
    
    # 通用错误
    if "string_too_short" in error_type or "string_too_long" in error_type:
        return 1003, translated_msg  # 参数值无效
    elif "type_error" in error_type:
        return 1001, translated_msg  # 参数错误
    else:
        return 1003, translated_msg  # 参数值无效


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """请求验证异常处理器 - 返回第一个验证错误"""
    request_id = getattr(request.state, "request_id", None)
    
    # 获取第一个错误
    first_error = exc.errors()[0]
    field = ".".join(str(loc) for loc in first_error["loc"][1:])  # 跳过 'body'
    error_type = first_error["type"]
    error_msg = first_error["msg"]
    
    # 根据错误类型映射业务状态码
    business_code, translated_msg = map_validation_error_to_business_code(field, error_type, error_msg)
    
    # 记录异常日志
    logger.warning(
        f"Validation Error: {error_type} - {translated_msg} - "
        f"Field: {field} - Path: {request.url.path} - Method: {request.method} - "
        f"Request ID: {request_id}",
        extra={"field": field, "error_type": error_type, "request_id": request_id}
    )
    
    return JSONResponse(
        status_code=200,
        content={
            "code": business_code,
            "message": translated_msg,
            "data": {}
        }
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
        error_message = "数据完整性约束违反"
        business_code = 1003
        if "duplicate key" in str(exc).lower():
            error_message = "数据重复"
            business_code = 1003
        elif "foreign key" in str(exc).lower():
            error_message = "引用的资源不存在"
            business_code = 1005
        
        return JSONResponse(
            status_code=200,
            content={
                "code": business_code,
                "message": error_message,
                "data": {}
            }
        )
    
    # 通用数据库错误
    return JSONResponse(
        status_code=200,
        content={
            "code": 1000,
            "message": "数据库操作失败",
            "data": {}
        }
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
        status_code=200,
        content={
            "code": 1000,
            "message": "系统内部错误",
            "data": {}
        }
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


def raise_business_error(message: str, business_code: int = 1000):
    """抛出业务异常"""
    raise BusinessException(message, business_code)


# 常用业务异常快捷方式
def raise_user_not_found():
    """抛出用户不存在异常"""
    raise BusinessException("用户不存在", 3009)


def raise_username_exists():
    """抛出用户名已存在异常"""
    raise BusinessException("用户名已存在", 3003)


def raise_email_exists():
    """抛出邮箱已存在异常"""
    raise BusinessException("邮箱已存在", 3005)


def raise_invalid_credentials():
    """抛出用户名或密码错误异常"""
    raise BusinessException("用户名或密码错误", 2001)


def raise_unauthorized():
    """抛出未登录异常"""
    raise BusinessException("未登录", 2001)


def raise_forbidden():
    """抛出权限不足异常"""
    raise BusinessException("权限不足", 2003)


def raise_not_found_resource(resource_name: str):
    """抛出资源不存在异常"""
    raise BusinessException(f"{resource_name}不存在", 1005)


def raise_duplicate_resource(resource_name: str):
    """抛出资源重复异常"""
    raise BusinessException(f"{resource_name}已存在", 1003)


def raise_invalid_operation(message: str = "操作无效"):
    """抛出无效操作异常"""
    raise BusinessException(message, 1003)


def raise_server_error(message: str = "服务器内部错误"):
    """抛出服务器错误异常"""
    raise BusinessException(message, 1000)


def raise_external_service_error(service: str, operation: str = None):
    """抛出外部服务异常"""
    raise ExternalServiceException(service, operation)


def raise_file_operation_error(operation: str, file_path: str = None):
    """抛出文件操作异常"""
    raise FileOperationException(operation, file_path)