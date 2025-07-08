from typing import Any, Dict, List, Optional, Union
from fastapi import status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime
import uuid


class ResponseModel(BaseModel):
    """标准响应模型"""
    success: bool = True
    message: str = "Success"
    data: Optional[Any] = None
    timestamp: datetime = None
    request_id: Optional[str] = None
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)


class PaginationModel(BaseModel):
    """分页模型"""
    page: int
    size: int
    total: int
    pages: int
    has_next: bool
    has_prev: bool


class PaginatedResponseModel(ResponseModel):
    """分页响应模型"""
    data: Optional[List[Any]] = None
    pagination: Optional[PaginationModel] = None


class ErrorResponseModel(BaseModel):
    """错误响应模型"""
    success: bool = False
    error: Dict[str, Any]
    data: Optional[Any] = None
    timestamp: datetime = None
    request_id: Optional[str] = None
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)


class ResponseBuilder:
    """响应构建器"""
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "操作成功",
        request_id: str = None
    ) -> JSONResponse:
        """成功响应"""
        return JSONResponse(
            status_code=200,
            content={
                "code": 0,
                "message": message,
                "data": data if data is not None else {}
            }
        )
    
    @staticmethod
    def created(
        data: Any = None,
        message: str = "创建成功",
        request_id: str = None
    ) -> JSONResponse:
        """创建成功响应"""
        return ResponseBuilder.success(
            data=data,
            message=message,
            request_id=request_id
        )
    
    @staticmethod
    def updated(
        data: Any = None,
        message: str = "更新成功",
        request_id: str = None
    ) -> JSONResponse:
        """更新成功响应"""
        return ResponseBuilder.success(
            data=data,
            message=message,
            request_id=request_id
        )
    
    @staticmethod
    def deleted(
        message: str = "删除成功",
        request_id: str = None
    ) -> JSONResponse:
        """删除成功响应"""
        return ResponseBuilder.success(
            data={},
            message=message,
            request_id=request_id
        )
    
    @staticmethod
    def no_content(
        message: str = "无内容",
        request_id: str = None
    ) -> JSONResponse:
        """无内容响应"""
        return ResponseBuilder.success(
            data={},
            message=message,
            request_id=request_id
        )
    
    @staticmethod
    def paginated(
        data: List[Any],
        page: int,
        size: int,
        total: int,
        message: str = "查询成功",
        request_id: str = None
    ) -> JSONResponse:
        """分页响应"""
        pages = (total + size - 1) // size  # 向上取整
        
        pagination = {
            "page": page,
            "size": size,
            "total": total,
            "pages": pages,
            "has_next": page < pages,
            "has_prev": page > 1
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "code": 0,
                "message": message,
                "data": {
                    "list": data,
                    "pagination": pagination
                }
            }
        )
    
    @staticmethod
    def error(
        business_code: int,
        message: str,
        data: Any = None,
        request_id: str = None
    ) -> JSONResponse:
        """错误响应"""
        return JSONResponse(
            status_code=200,
            content={
                "code": business_code,
                "message": message,
                "data": data if data is not None else {}
            }
        )
    
    @staticmethod
    def business_error(
        business_code: int,
        message: str,
        request_id: str = None
    ) -> JSONResponse:
        """业务错误响应"""
        return ResponseBuilder.error(
            business_code=business_code,
            message=message,
            request_id=request_id
        )
    
    @staticmethod
    def bad_request(
        message: str = "Bad request",
        details: Dict[str, Any] = None,
        request_id: str = None
    ) -> JSONResponse:
        """错误请求响应"""
        return ResponseBuilder.error(
            error_code="BAD_REQUEST",
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            details=details,
            request_id=request_id
        )
    
    @staticmethod
    def unauthorized(
        message: str = "Unauthorized",
        details: Dict[str, Any] = None,
        request_id: str = None
    ) -> JSONResponse:
        """未授权响应"""
        return ResponseBuilder.error(
            error_code="UNAUTHORIZED",
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
            request_id=request_id
        )
    
    @staticmethod
    def forbidden(
        message: str = "Forbidden",
        details: Dict[str, Any] = None,
        request_id: str = None
    ) -> JSONResponse:
        """禁止访问响应"""
        return ResponseBuilder.error(
            error_code="FORBIDDEN",
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
            request_id=request_id
        )
    
    @staticmethod
    def not_found(
        message: str = "Resource not found",
        details: Dict[str, Any] = None,
        request_id: str = None
    ) -> JSONResponse:
        """资源未找到响应"""
        return ResponseBuilder.error(
            error_code="NOT_FOUND",
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
            request_id=request_id
        )
    
    @staticmethod
    def conflict(
        message: str = "Resource conflict",
        details: Dict[str, Any] = None,
        request_id: str = None
    ) -> JSONResponse:
        """资源冲突响应"""
        return ResponseBuilder.error(
            error_code="CONFLICT",
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            details=details,
            request_id=request_id
        )
    
    @staticmethod
    def validation_error(
        message: str = "参数验证失败",
        validation_errors: List[Dict[str, Any]] = None,
        request_id: str = None
    ) -> JSONResponse:
        """验证错误响应"""
        data = {}
        if validation_errors:
            data["errors"] = validation_errors
        
        return JSONResponse(
            status_code=200,
            content={
                "code": 400,
                "message": message,
                "data": data
            }
        )
    
    @staticmethod
    def rate_limit_exceeded(
        message: str = "Rate limit exceeded",
        retry_after: int = None,
        request_id: str = None
    ) -> JSONResponse:
        """限流响应"""
        details = {}
        if retry_after:
            details["retry_after"] = retry_after
        
        response = ResponseBuilder.error(
            error_code="RATE_LIMIT_EXCEEDED",
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            details=details,
            request_id=request_id
        )
        
        if retry_after:
            response.headers["Retry-After"] = str(retry_after)
        
        return response
    
    @staticmethod
    def internal_error(
        message: str = "Internal server error",
        request_id: str = None
    ) -> JSONResponse:
        """内部服务器错误响应"""
        return ResponseBuilder.error(
            error_code="INTERNAL_ERROR",
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            request_id=request_id
        )
    
    @staticmethod
    def service_unavailable(
        message: str = "Service unavailable",
        retry_after: int = None,
        request_id: str = None
    ) -> JSONResponse:
        """服务不可用响应"""
        details = {}
        if retry_after:
            details["retry_after"] = retry_after
        
        response = ResponseBuilder.error(
            error_code="SERVICE_UNAVAILABLE",
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
            request_id=request_id
        )
        
        if retry_after:
            response.headers["Retry-After"] = str(retry_after)
        
        return response


class ResponseFormatter:
    """响应格式化器"""
    
    @staticmethod
    def format_user_data(user_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化用户数据"""
        # 移除敏感信息
        sensitive_fields = ['password_hash', 'password']
        formatted_data = {k: v for k, v in user_data.items() if k not in sensitive_fields}
        
        # 格式化时间字段
        time_fields = ['created_at', 'updated_at', 'last_login_at']
        for field in time_fields:
            if field in formatted_data and formatted_data[field]:
                if isinstance(formatted_data[field], datetime):
                    formatted_data[field] = formatted_data[field].isoformat()
        
        return formatted_data
    
    @staticmethod
    def format_script_data(script_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化剧本数据"""
        formatted_data = script_data.copy()
        
        # 格式化时间字段
        time_fields = ['created_at', 'updated_at', 'deadline']
        for field in time_fields:
            if field in formatted_data and formatted_data[field]:
                if isinstance(formatted_data[field], datetime):
                    formatted_data[field] = formatted_data[field].isoformat()
        
        return formatted_data
    
    @staticmethod
    def format_audio_data(audio_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化音频数据"""
        formatted_data = audio_data.copy()
        
        # 格式化时间字段
        time_fields = ['created_at', 'updated_at', 'recorded_at', 'reviewed_at']
        for field in time_fields:
            if field in formatted_data and formatted_data[field]:
                if isinstance(formatted_data[field], datetime):
                    formatted_data[field] = formatted_data[field].isoformat()
        
        # 格式化文件大小
        if 'file_size' in formatted_data and formatted_data['file_size']:
            formatted_data['file_size_human'] = ResponseFormatter.format_file_size(
                formatted_data['file_size']
            )
        
        return formatted_data
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "0 B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        import math
        i = int(math.floor(math.log(size_bytes, 1024)))
        p = math.pow(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_names[i]}"
    
    @staticmethod
    def format_duration(seconds: float) -> str:
        """格式化时长"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            remaining_seconds = seconds % 60
            return f"{minutes}m {remaining_seconds:.1f}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            remaining_seconds = seconds % 60
            return f"{hours}h {minutes}m {remaining_seconds:.1f}s"


# 快捷响应函数
def success_response(
    data: Any = None,
    message: str = "Success",
    status_code: int = status.HTTP_200_OK,
    request_id: str = None
) -> JSONResponse:
    """成功响应快捷函数"""
    return ResponseBuilder.success(data, message, status_code, request_id)


def error_response(
    error_code: str,
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    details: Dict[str, Any] = None,
    request_id: str = None
) -> JSONResponse:
    """错误响应快捷函数"""
    return ResponseBuilder.error(error_code, message, status_code, details, request_id)


def paginated_response(
    data: List[Any],
    page: int,
    size: int,
    total: int,
    message: str = "Success",
    request_id: str = None
) -> JSONResponse:
    """分页响应快捷函数"""
    return ResponseBuilder.paginated(data, page, size, total, message, request_id)