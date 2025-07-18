from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class PermissionType(str, Enum):
    """权限类型枚举"""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    MANAGE = "manage"
    ASSIGN = "assign"
    EXECUTE = "execute"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    REVIEW = "review"
    APPROVE = "approve"
    REJECT = "reject"
    CONFIG = "config"
    LOG = "log"
    MONITOR = "monitor"
    ASSIGN_ROLE = "assign_role"
    ASSIGN_PERMISSION = "assign_permission"
    MANAGE_MEMBERS = "manage_members"
    VIEW_STATISTICS = "view_statistics"
    ADD_MEMBER = "add_member"
    REMOVE_MEMBER = "remove_member"


class ResourceType(str, Enum):
    """资源类型枚举"""
    USER = "user"
    ROLE = "role"
    PERMISSION = "permission"
    SCRIPT = "script"
    AUDIO = "audio"
    REVIEW = "review"
    SOCIETY = "society"
    SYSTEM = "system"
    DEPARTMENT = "department"
    DEPARTMENT_MEMBER = "department_member"
    CONTENT = "content"


class PermissionBase(BaseModel):
    """权限基础模型"""
    name: str = Field(..., max_length=100, description="权限名称")
    display_name: str = Field(..., max_length=100, description="显示名称")
    description: Optional[str] = Field(
        None, max_length=500, description="权限描述")
    module: Optional[str] = Field(None, max_length=50, description="所属模块")
    action: Optional[str] = Field(None, description="操作类型")
    resource: Optional[str] = Field(None, description="资源类型")
    sort_order: int = Field(0, description="排序顺序")
    
    # 层级权限相关字段
    parent_id: Optional[int] = Field(None, description="父权限ID")
    level: int = Field(0, description="权限层级")
    path: Optional[str] = Field(None, max_length=500, description="权限路径")
    
    @property
    def is_wildcard(self) -> bool:
        """判断是否为通配符权限"""
        return '*' in (self.name or '')

    @validator('name')
    def validate_name(cls, v):
        if not v.replace('_', '').replace(':', '').replace('*', '').isalnum():
            raise ValueError('权限名称只能包含字母、数字、下划线、冒号和星号')
        return v
    
    @validator('action')
    def validate_action(cls, v):
        if v is not None and v != '' and v not in [e.value for e in PermissionType]:
            # 对于根权限，允许为 None 或空字符串
            return v
        return v
    
    @validator('resource')
    def validate_resource(cls, v):
        if v is not None and v != '' and v not in [e.value for e in ResourceType]:
            # 对于根权限，允许为 None 或空字符串，也允许自定义值
            return v
        return v
    
    @validator('action')
    def validate_action(cls, v):
        if v is not None and v != '' and v not in [e.value for e in PermissionType]:
            # 对于根权限，允许为 None 或空字符串
            return v
        return v
    
    @validator('resource')
    def validate_resource(cls, v):
        if v is not None and v != '' and v not in [e.value for e in ResourceType]:
            # 对于根权限，允许为 None 或空字符串，也允许自定义值
            return v
        return v


class PermissionCreate(BaseModel):
    """创建权限模型"""
    name: str = Field(..., max_length=100, description="权限名称")
    display_name: str = Field(..., max_length=100, description="显示名称")
    description: Optional[str] = Field(
        None, max_length=500, description="权限描述")
    module: Optional[str] = Field(None, max_length=50, description="所属模块")
    action: Optional[str] = Field(None, description="操作类型")
    resource: Optional[str] = Field(None, description="资源类型")
    sort_order: int = Field(0, description="排序顺序")
    
    # 仅包含父权限ID，level 和 path 由系统自动计算
    parent_id: Optional[int] = Field(None, description="父权限ID")
    
    @property
    def is_wildcard(self) -> bool:
        """判断是否为通配符权限"""
        return '*' in (self.name or '')

    @validator('name')
    def validate_name(cls, v):
        if not v.replace('_', '').replace(':', '').replace('*', '').isalnum():
            raise ValueError('权限名称只能包含字母、数字、下划线、冒号和星号')
        return v


class PermissionUpdate(BaseModel):
    """更新权限模型"""
    name: Optional[str] = Field(None, max_length=100, description="权限名称")
    display_name: Optional[str] = Field(
        None, max_length=100, description="显示名称")
    description: Optional[str] = Field(
        None, max_length=500, description="权限描述")
    module: Optional[str] = Field(None, max_length=50, description="所属模块")
    action: Optional[str] = Field(None, description="操作类型")
    resource: Optional[str] = Field(None, description="资源类型")
    is_active: Optional[bool] = Field(None, description="是否激活")
    sort_order: Optional[int] = Field(None, description="排序顺序")
    
    # 允许修改父权限关系，level 和 path 由系统自动重新计算
    parent_id: Optional[int] = Field(None, description="父权限ID")
    
    @property
    def is_wildcard(self) -> bool:
        """判断是否为通配符权限"""
        return '*' in (self.name or '') if self.name else False

    @validator('name')
    def validate_name(cls, v):
        if v and not v.replace('_', '').replace(':', '').replace('*', '').isalnum():
            raise ValueError('权限名称只能包含字母、数字、下划线、冒号和星号')
        return v
    
    @validator('action')
    def validate_action(cls, v):
        if v is not None and v != '' and v not in [e.value for e in PermissionType]:
            # 对于根权限，允许为 None 或空字符串
            return v
        return v
    
    @validator('resource')
    def validate_resource(cls, v):
        if v is not None and v != '' and v not in [e.value for e in ResourceType]:
            # 对于根权限，允许为 None 或空字符串，也允许自定义值
            return v
        return v


class PermissionResponse(PermissionBase):
    """权限响应模型"""
    id: int = Field(..., description="权限ID")
    is_system: bool
    is_active: bool = Field(True, description="是否激活")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class PermissionTreeNode(BaseModel):
    """权限树节点模型"""
    id: int
    name: str
    display_name: str
    description: Optional[str]
    parent_id: Optional[int]
    level: int
    path: Optional[str]
    is_category: bool
    is_system: bool
    is_active: bool
    sort_order: int
    children: List['PermissionTreeNode'] = Field(default_factory=list, description="子权限列表")
    
    class Config:
        from_attributes = True


class PermissionTreeResponse(BaseModel):
    """权限树响应模型"""
    tree: List[PermissionTreeNode]
    total: int
    
    class Config:
        from_attributes = True





class PermissionListResponse(BaseModel):
    """权限列表响应模型"""
    permissions: List[PermissionResponse] = Field(..., description="权限列表")
    total: int = Field(..., description="总数")
    page: int = Field(..., description="当前页")
    page_size: int = Field(..., description="每页大小")

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


class RoleCreate(BaseModel):
    """创建角色模型"""
    name: str = Field(..., max_length=50, description="角色名称")
    display_name: str = Field(..., max_length=100, description="显示名称")
    description: Optional[str] = Field(
        None, max_length=500, description="角色描述")
    sort_order: Optional[int] = Field(None, description="排序顺序")
    is_active: bool = Field(True, description="是否激活")
    permission_ids: List[int] = Field(default_factory=list, description="权限ID列表")

    @validator('name')
    def validate_name(cls, v):
        if not v.replace('_', '').isalnum():
            raise ValueError('角色名称只能包含字母、数字和下划线')
        return v


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

    @validator('name')
    def validate_name(cls, v):
        if v is not None and not v.replace('_', '').isalnum():
            raise ValueError('角色名称只能包含字母、数字和下划线')
        return v


class RoleStatusUpdate(BaseModel):
    """角色状态更新模型"""
    is_active: bool = Field(..., description="是否激活")


class PermissionSimple(BaseModel):
    """简化权限模型"""
    id: int
    name: str
    display_name: str

    class Config:
        from_attributes = True


class RoleResponse(RoleBase):
    """角色响应模型"""
    id: int
    is_system: bool
    is_active: bool
    permissions: List[PermissionSimple] = Field(
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


# 更新前向引用
PermissionTreeNode.model_rebuild()


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
    status: Optional[int] = Field(None, ge=-1, le=1, description="角色状态（-1=全部，1=激活，0=禁用）")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    order_by: str = Field("sort_order", description="排序字段")
    order_desc: bool = Field(True, description="是否降序")


class PermissionSearchQuery(BaseModel):
    """权限搜索查询模型"""
    keyword: Optional[str] = Field(None, description="关键词搜索（权限名称、显示名称）")
    module: Optional[str] = Field(None, description="所属模块")
    action: Optional[str] = Field(None, description="操作类型")
    resource: Optional[str] = Field(None, description="资源类型")
    is_system: Optional[bool] = Field(None, description="是否系统权限")
    # 权限分类相关查询字段
    parent_id: Optional[int] = Field(None, description="父权限ID")
    level: Optional[int] = Field(None, description="权限层级")
    is_category: Optional[bool] = Field(None, description="是否为分类")
    include_children: bool = Field(False, description="是否包含子权限")
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


class RolePermissionSync(BaseModel):
    """角色权限同步模型 - 根据权限ID列表同步角色权限（增删）"""
    role_id: int = Field(..., description="角色ID")
    permission_ids: List[int] = Field(..., description="权限ID列表（将同步为角色的完整权限列表）")


class RolePermissionBatch(BaseModel):
    """批量角色权限分配模型（向后兼容）"""
    role_id: int = Field(..., description="角色ID")
    permission_ids: List[int] = Field(..., min_items=1, description="权限ID列表")


class UserRoleSync(BaseModel):
    """用户角色同步模型 - 根据角色ID列表同步用户角色（增删）"""
    user_id: int = Field(..., description="用户ID")
    role_ids: List[int] = Field(..., description="角色ID列表（将同步为用户的完整角色列表）")
    expires_at: Optional[datetime] = Field(None, description="过期时间")

    @validator('expires_at')
    def validate_expires_at(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError('过期时间必须大于当前时间')
        return v
