from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PermissionType(str, Enum):
    """权限类型枚举"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXECUTE = "execute"
    MANAGE = "manage"


class ResourceType(str, Enum):
    """资源类型枚举"""
    USER = "user"
    ROLE = "role"
    SCRIPT = "script"
    AUDIO = "audio"
    REVIEW = "review"
    SOCIETY = "society"
    SYSTEM = "system"


class PermissionBase(BaseModel):
    """权限基础模型"""
    name: str = Field(..., max_length=100, description="权限名称")
    display_name: str = Field(..., max_length=100, description="显示名称")
    description: Optional[str] = Field(
        None, max_length=500, description="权限描述")
    module: str = Field(..., max_length=50, description="所属模块")
    action: PermissionType = Field(..., description="操作类型")
    resource: ResourceType = Field(..., description="资源类型")
    # is_wildcard 字段已移除，现在通过权限名称自动判断
    sort_order: int = Field(0, description="排序顺序")
    
    @property
    def is_wildcard(self) -> bool:
        """判断是否为通配符权限"""
        return '*' in (self.name or '')

    @validator('name')
    def validate_name(cls, v):
        if not v.replace('_', '').replace(':', '').isalnum():
            raise ValueError('权限名称只能包含字母、数字、下划线和冒号')
        return v


class PermissionCreate(PermissionBase):
    """创建权限模型"""
    pass


class PermissionUpdate(BaseModel):
    """更新权限模型"""
    name: Optional[str] = Field(None, max_length=100, description="权限名称")
    display_name: Optional[str] = Field(
        None, max_length=100, description="显示名称")
    description: Optional[str] = Field(
        None, max_length=500, description="权限描述")
    module: Optional[str] = Field(None, max_length=50, description="所属模块")
    action: Optional[PermissionType] = Field(None, description="操作类型")
    resource: Optional[ResourceType] = Field(None, description="资源类型")
    # is_wildcard 字段已移除，现在通过权限名称自动判断
    is_active: Optional[bool] = Field(None, description="是否激活")
    sort_order: Optional[int] = Field(None, description="排序顺序")
    
    @property
    def is_wildcard(self) -> bool:
        """判断是否为通配符权限"""
        return '*' in (self.name or '') if self.name else False

    @validator('name')
    def validate_name(cls, v):
        if v and not v.replace('_', '').replace(':', '').isalnum():
            raise ValueError('权限名称只能包含字母、数字、下划线和冒号')
        return v


class PermissionResponse(PermissionBase):
    """权限响应模型"""
    id: int
    is_system: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class PermissionListResponse(BaseModel):
    """权限列表响应模型"""
    items: List[PermissionResponse]
    total: int
    page: int
    size: int
    pages: int

    class Config:
        from_attributes = True


class RoleBase(BaseModel):
    """角色基础模型"""
    name: str = Field(..., max_length=50, description="角色名称")
    display_name: str = Field(..., max_length=100, description="显示名称")
    description: Optional[str] = Field(
        None, max_length=500, description="角色描述")
    sort_order: int = Field(0, description="排序顺序")

    @validator('name')
    def validate_name(cls, v):
        if not v.replace('_', '').isalnum():
            raise ValueError('角色名称只能包含字母、数字和下划线')
        return v


class RoleCreate(RoleBase):
    """创建角色模型"""
    permission_ids: List[int] = Field(default_factory=list, description="权限ID列表")


class RoleUpdate(BaseModel):
    """更新角色模型"""
    name: Optional[str] = Field(None, max_length=100, description="角色名称")
    display_name: Optional[str] = Field(
        None, max_length=100, description="显示名称")
    description: Optional[str] = Field(
        None, max_length=500, description="角色描述")
    is_active: Optional[bool] = Field(None, description="是否激活")
    sort_order: Optional[int] = Field(None, description="排序顺序")
    permission_ids: Optional[List[int]] = Field(None, description="权限ID列表")


class RoleResponse(RoleBase):
    """角色响应模型"""
    id: int
    is_system: bool
    is_active: bool
    permissions: List[PermissionResponse] = Field(
        default_factory=list, description="权限列表")
    user_count: int = Field(0, description="用户数量")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class RoleListResponse(BaseModel):
    """角色列表响应模型"""
    id: int
    name: str
    display_name: str
    description: Optional[str]
    is_system: bool
    is_active: bool
    user_count: int
    permission_count: int
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class UserRoleBase(BaseModel):
    """用户角色基础模型"""
    user_id: int = Field(..., description="用户ID")
    role_id: int = Field(..., description="角色ID")
    expires_at: Optional[datetime] = Field(None, description="过期时间")

    @validator('expires_at')
    def validate_expires_at(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError('过期时间必须大于当前时间')
        return v


class UserRoleCreate(UserRoleBase):
    """创建用户角色模型"""
    pass


class UserRoleUpdate(BaseModel):
    """更新用户角色模型"""
    expires_at: Optional[datetime] = Field(None, description="过期时间")

    @validator('expires_at')
    def validate_expires_at(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError('过期时间必须大于当前时间')
        return v


class UserRoleResponse(UserRoleBase):
    """用户角色响应模型"""
    id: int
    assigned_by: Optional[int]
    assigned_at: datetime
    is_expired: bool
    role: RoleResponse

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class RoleAssignmentBatch(BaseModel):
    """批量角色分配模型"""
    user_ids: List[int] = Field(..., min_items=1, description="用户ID列表")
    role_ids: List[int] = Field(..., min_items=1, description="角色ID列表")
    expires_at: Optional[datetime] = Field(None, description="过期时间")

    @validator('expires_at')
    def validate_expires_at(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError('过期时间必须大于当前时间')
        return v


class RoleSearchQuery(BaseModel):
    """角色搜索查询模型"""
    keyword: Optional[str] = Field(None, description="关键词搜索（角色名称、显示名称）")
    is_system: Optional[bool] = Field(None, description="是否系统角色")
    has_users: Optional[bool] = Field(None, description="是否有用户")
    permission: Optional[str] = Field(None, description="包含特定权限")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    order_by: str = Field("sort_order", description="排序字段")
    order_desc: bool = Field(False, description="是否降序")


class PermissionSearchQuery(BaseModel):
    """权限搜索查询模型"""
    keyword: Optional[str] = Field(None, description="关键词搜索（权限名称、显示名称）")
    module: Optional[str] = Field(None, description="所属模块")
    action: Optional[str] = Field(None, description="操作类型")
    resource: Optional[str] = Field(None, description="资源类型")
    is_system: Optional[bool] = Field(None, description="是否系统权限")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    order_by: str = Field("sort_order", description="排序字段")
    order_desc: bool = Field(False, description="是否降序")
    
    @validator('action')
    def validate_action(cls, v):
        """验证操作类型"""
        if v is not None:
            valid_actions = [e.value for e in PermissionType]
            if v not in valid_actions:
                raise ValueError(f'操作类型必须是以下值之一: {", ".join(valid_actions)}')
        return v
    
    @validator('resource')
    def validate_resource(cls, v):
        """验证资源类型"""
        if v is not None:
            valid_resources = [e.value for e in ResourceType]
            if v not in valid_resources:
                raise ValueError(f'资源类型必须是以下值之一: {", ".join(valid_resources)}')
        return v


class RolePermissionMatrix(BaseModel):
    """角色权限矩阵模型"""
    role_id: int
    role_name: str
    role_display_name: str
    # {module: {permission: has_permission}}
    permissions: Dict[str, Dict[str, bool]]

    class Config:
        from_attributes = True


class PermissionCheck(BaseModel):
    """权限检查模型"""
    user_id: int = Field(..., description="用户ID")
    permission: str = Field(..., description="权限名称")
    resource_id: Optional[int] = Field(None, description="资源ID")


class PermissionCheckResult(BaseModel):
    """权限检查结果模型"""
    has_permission: bool
    reason: Optional[str] = None
    granted_by_roles: List[str] = Field(
        default_factory=list, description="授权角色列表")


class RoleStatistics(BaseModel):
    """角色统计信息模型"""
    total_roles: int
    active_roles: int
    inactive_roles: int
    total_permissions: int
    active_permissions: int
    inactive_permissions: int
    total_users_with_roles: int

    class Config:
        from_attributes = True


class UserRoleAssignment(BaseModel):
    """用户角色分配模型"""
    user_id: int
    role_ids: List[int] = Field(..., min_items=1, description="角色ID列表")
    expires_at: Optional[datetime] = Field(None, description="过期时间")

    @validator('expires_at')
    def validate_expires_at(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError('过期时间必须大于当前时间')
        return v

    class Config:
        from_attributes = True


class UserRoleRemoval(BaseModel):
    """用户角色移除模型"""
    user_id: int
    role_ids: List[int] = Field(..., min_items=1, description="要移除的角色ID列表")

    class Config:
        from_attributes = True


# UserRoleBatchOperation 模型已删除，使用 RoleAssignmentBatch 替代
# 批量分配使用 RoleAssignmentBatch
# 批量移除也使用 RoleAssignmentBatch（复用相同的数据结构）


class RoleTemplate(BaseModel):
    """角色模板模型"""
    name: str = Field(..., description="模板名称")
    display_name: str = Field(..., description="显示名称")
    description: str = Field(..., description="模板描述")
    permissions: List[str] = Field(..., description="权限列表")
    is_builtin: bool = Field(True, description="是否内置模板")

    class Config:
        from_attributes = True


class RoleImportExport(BaseModel):
    """角色导入导出模型"""
    roles: List[Dict[str, Any]] = Field(..., description="角色数据")
    permissions: List[Dict[str, Any]] = Field(..., description="权限数据")
    role_permissions: List[Dict[str, Any]] = Field(..., description="角色权限关联数据")

    class Config:
        from_attributes = True


class RolePermissionBase(BaseModel):
    """角色权限关联基础模型"""
    role_id: int = Field(..., description="角色ID")
    permission_id: int = Field(..., description="权限ID")
    expires_at: Optional[datetime] = Field(None, description="过期时间")

    @validator('expires_at')
    def validate_expires_at(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError('过期时间必须大于当前时间')
        return v


class RolePermissionCreate(RolePermissionBase):
    """创建角色权限关联模型"""
    pass


class RolePermissionUpdate(BaseModel):
    """更新角色权限关联模型"""
    expires_at: Optional[datetime] = Field(None, description="过期时间")

    @validator('expires_at')
    def validate_expires_at(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError('过期时间必须大于当前时间')
        return v


class RolePermissionResponse(RolePermissionBase):
    """角色权限关联响应模型"""
    id: int
    granted_by: Optional[int]
    granted_at: datetime
    is_expired: bool
    role_name: Optional[str]
    permission_name: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class RolePermissionBatch(BaseModel):
    """批量角色权限操作模型"""
    role_id: int = Field(..., description="角色ID")
    permission_ids: List[int] = Field(..., min_items=1, description="权限ID列表")
    expires_at: Optional[datetime] = Field(None, description="过期时间")

    @validator('expires_at')
    def validate_expires_at(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError('过期时间必须大于当前时间')
        return v
