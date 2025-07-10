from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import IntEnum


class DepartmentStatus(IntEnum):
    """部门状态枚举"""
    DELETED = -1
    INACTIVE = 0
    ACTIVE = 1


class MemberStatus(IntEnum):
    """成员状态枚举"""
    INACTIVE = 0
    ACTIVE = 1
    TRANSFERRED = 2


# 基础部门信息
class DepartmentBase(BaseModel):
    """部门基础信息"""
    name: str = Field(..., min_length=1, max_length=100, description="部门名称")
    parent_id: Optional[int] = Field(None, description="上级部门ID")
    manager_id: Optional[int] = Field(None, description="负责人ID")
    manager_name: Optional[str] = Field(None, max_length=100, description="负责人姓名")
    manager_phone: Optional[str] = Field(None, max_length=20, description="负责人手机号")
    manager_email: Optional[str] = Field(None, max_length=100, description="负责人邮箱")
    description: Optional[str] = Field(None, description="部门描述")
    sort_order: int = Field(0, description="排序序号")
    status: DepartmentStatus = Field(DepartmentStatus.ACTIVE, description="部门状态")
    remarks: Optional[str] = Field(None, description="备注信息")
    
    @validator('manager_email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('邮箱格式不正确')
        return v
    
    @validator('manager_phone')
    def validate_phone(cls, v):
        if v and not v.isdigit():
            raise ValueError('手机号只能包含数字')
        return v


# 创建部门请求
class DepartmentCreate(DepartmentBase):
    """创建部门请求"""
    pass


# 更新部门请求
class DepartmentUpdate(BaseModel):
    """更新部门请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="部门名称")
    parent_id: Optional[int] = Field(None, description="上级部门ID")
    manager_id: Optional[int] = Field(None, description="负责人ID")
    manager_name: Optional[str] = Field(None, max_length=100, description="负责人姓名")
    manager_phone: Optional[str] = Field(None, max_length=20, description="负责人手机号")
    manager_email: Optional[str] = Field(None, max_length=100, description="负责人邮箱")
    description: Optional[str] = Field(None, description="部门描述")
    sort_order: Optional[int] = Field(None, description="排序序号")
    status: Optional[DepartmentStatus] = Field(None, description="部门状态")
    remarks: Optional[str] = Field(None, description="备注信息")
    
    @validator('manager_email')
    def validate_email(cls, v):
        if v and '@' not in v:
            raise ValueError('邮箱格式不正确')
        return v
    
    @validator('manager_phone')
    def validate_phone(cls, v):
        if v and not v.isdigit():
            raise ValueError('手机号只能包含数字')
        return v


# 部门管理员信息
class DepartmentManager(BaseModel):
    """部门管理员信息"""
    id: int
    username: str
    real_name: Optional[str]
    display_name: str


# 部门成员信息
class DepartmentMemberInfo(BaseModel):
    """部门成员信息"""
    id: int
    username: str
    real_name: Optional[str]
    display_name: str
    avatar_url: Optional[str]
    position: Optional[str]
    is_manager: bool
    status: MemberStatus
    joined_at: datetime
    left_at: Optional[datetime]


# 部门响应信息
class DepartmentResponse(DepartmentBase):
    """部门响应信息"""
    id: int
    level: int
    path: Optional[str]
    created_at: datetime
    updated_at: datetime
    is_active: bool
    is_root: bool
    member_count: Optional[int] = None
    manager: Optional[DepartmentManager] = None
    children: Optional[List['DepartmentResponse']] = None
    members: Optional[List[DepartmentMemberInfo]] = None
    
    class Config:
        from_attributes = True


# 部门树形结构响应
class DepartmentTreeResponse(BaseModel):
    """部门树形结构响应"""
    id: int
    name: str
    parent_id: Optional[int]
    level: int
    sort_order: int
    status: DepartmentStatus
    member_count: int
    manager: Optional[DepartmentManager]
    children: List['DepartmentTreeResponse'] = []
    
    class Config:
        from_attributes = True


# 部门成员管理
class DepartmentMemberBase(BaseModel):
    """部门成员基础信息"""
    user_id: int = Field(..., description="用户ID")
    position: Optional[str] = Field(None, max_length=100, description="职位")
    is_manager: bool = Field(False, description="是否为部门负责人")
    status: MemberStatus = Field(MemberStatus.ACTIVE, description="成员状态")
    remarks: Optional[str] = Field(None, description="备注信息")


class DepartmentMemberCreate(DepartmentMemberBase):
    """添加部门成员请求"""
    pass


class DepartmentMemberUpdate(BaseModel):
    """更新部门成员请求"""
    position: Optional[str] = Field(None, max_length=100, description="职位")
    is_manager: Optional[bool] = Field(None, description="是否为部门负责人")
    status: Optional[MemberStatus] = Field(None, description="成员状态")
    remarks: Optional[str] = Field(None, description="备注信息")


class DepartmentMemberResponse(DepartmentMemberBase):
    """部门成员响应信息"""
    id: int
    department_id: int
    joined_at: datetime
    left_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    is_active: bool
    user: Optional[Dict[str, Any]] = None
    department: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True


# 批量操作
class DepartmentBatchOperation(BaseModel):
    """部门批量操作"""
    department_ids: List[int] = Field(..., min_items=1, description="部门ID列表")
    operation: str = Field(..., description="操作类型：activate, deactivate, delete")
    
    @validator('operation')
    def validate_operation(cls, v):
        allowed_operations = ['activate', 'deactivate', 'delete']
        if v not in allowed_operations:
            raise ValueError(f'操作类型必须是以下之一：{allowed_operations}')
        return v


# 部门查询参数
class DepartmentQuery(BaseModel):
    """部门查询参数"""
    name: Optional[str] = Field(None, description="部门名称（模糊搜索）")
    parent_id: Optional[int] = Field(None, description="上级部门ID")
    manager_id: Optional[int] = Field(None, description="负责人ID")
    status: Optional[DepartmentStatus] = Field(None, description="部门状态")
    level: Optional[int] = Field(None, description="部门层级")
    include_children: bool = Field(False, description="是否包含子部门")
    include_members: bool = Field(False, description="是否包含成员信息")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")


# 部门统计信息
class DepartmentStatistics(BaseModel):
    """部门统计信息"""
    total_departments: int = Field(..., description="总部门数")
    active_departments: int = Field(..., description="活跃部门数")
    inactive_departments: int = Field(..., description="非活跃部门数")
    root_departments: int = Field(..., description="根部门数")
    total_members: int = Field(..., description="总成员数")
    departments_by_level: Dict[int, int] = Field(..., description="按层级统计的部门数")
    top_departments_by_members: List[Dict[str, Any]] = Field(..., description="成员数最多的部门")


# 部门移动操作
class DepartmentMove(BaseModel):
    """部门移动操作"""
    target_parent_id: Optional[int] = Field(None, description="目标父部门ID，None表示移动到根级别")
    sort_order: Optional[int] = Field(None, description="新的排序位置")


# 更新递归引用
DepartmentResponse.model_rebuild()
DepartmentTreeResponse.model_rebuild()