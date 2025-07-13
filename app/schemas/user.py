import email
from pydantic import BaseModel, EmailStr, Field, validator, field_validator
from pydantic_core import core_schema
from typing import Optional, List, Dict, Any, Annotated
from datetime import datetime
from enum import Enum


class SexType(int, Enum):
    """性别类型枚举"""
    MALE = 1      # 男性
    FEMALE = 2    # 女性
    OTHER = 0     # 其他/未知
    
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type, handler):
        """Pydantic v2 自定义验证器"""
        def validate_sex(value):
            if value is None:
                return value
            if isinstance(value, cls):
                return value
            if isinstance(value, int) and value in [0, 1, 2]:
                return cls(value)
            raise ValueError(f'性别值无效，请输入：0（其他/未知）、1（男性）或 2（女性），当前输入值：{value}')
        
        return core_schema.no_info_plain_validator_function(
            validate_sex,
            serialization=core_schema.to_string_ser_schema()
        )


class UserStatus(int, Enum):
    """用户状态枚举"""
    ACTIVE = 1
    INACTIVE = 0
    SUSPENDED = -1
    DELETED = -2


class UserBase(BaseModel):
    """用户基础模型"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    real_name: Optional[str] = Field(None, max_length=50, description="真实姓名")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    wechat: Optional[str] = Field(None, max_length=50, description="微信号")
    sex: Optional[SexType] = Field(None, description="性别")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")
    avatar_url: Optional[str] = Field(None, max_length=500, description="头像URL")
    dept_id: Optional[int] = Field(None, description="部门ID，为空表示无部门")
    
    @validator('username')
    def validate_username(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('用户名只能包含字母、数字、下划线和连字符')
        return v
    
    @validator('phone')
    def validate_phone(cls, v):
        if v and not v.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise ValueError('手机号格式不正确')
        return v


class UserCreate(UserBase):
    """创建用户模型"""
    password: str = Field(..., min_length=8, max_length=128, description="密码")
    confirm_password: str = Field(..., description="确认密码")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('两次输入的密码不一致')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:  # 暂时放宽到6位
            raise ValueError('密码长度至少6位')
        # 暂时注释掉复杂的密码要求
        # if not any(c.isupper() for c in v):
        #     raise ValueError('密码必须包含至少一个大写字母')
        # if not any(c.islower() for c in v):
        #     raise ValueError('密码必须包含至少一个小写字母')
        # if not any(c.isdigit() for c in v):
        #     raise ValueError('密码必须包含至少一个数字')
        return v


class UserUpdate(BaseModel):
    """更新用户模型"""
    real_name: Optional[str] = Field(None, max_length=50, description="真实姓名")
    email: Optional[EmailStr] = Field(None, description="邮箱")
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="用户名")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    wechat: Optional[str] = Field(None, max_length=50, description="微信号")
    sex: Optional[SexType] = Field(None, description="性别")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")
    avatar_url: Optional[str] = Field(None, max_length=500, description="头像URL")
    dept_id: Optional[int] = Field(None, description="部门ID，为空表示无部门")
    settings: Optional[Dict[str, Any]] = Field(None, description="个人设置")
    
    @validator('phone')
    def validate_phone(cls, v):
        if v and not v.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise ValueError('手机号格式不正确')
        return v


class UserPasswordUpdate(BaseModel):
    """更新密码模型"""
    current_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=8, max_length=128, description="新密码")
    confirm_password: str = Field(..., description="确认新密码")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('两次输入的新密码不一致')
        return v
    
    @validator('new_password')
    def validate_password(cls, v):
        if len(v) < 6:  # 暂时放宽到6位
            raise ValueError('密码长度至少6位')
        # 暂时注释掉复杂的密码要求
        # if not any(c.isupper() for c in v):
        #     raise ValueError('密码必须包含至少一个大写字母')
        # if not any(c.islower() for c in v):
        #     raise ValueError('密码必须包含至少一个小写字母')
        # if not any(c.isdigit() for c in v):
        #     raise ValueError('密码必须包含至少一个数字')
        return v


class DepartmentInfo(BaseModel):
    """部门信息模型"""
    id: int = Field(..., description="部门ID")
    name: str = Field(..., description="部门名称")
    full_name: Optional[str] = Field(None, description="部门全名（包含层级）")


class UserResponse(UserBase):
    """用户响应模型"""
    id: int
    status: UserStatus
    last_login_at: Optional[datetime]
    login_count: int
    created_at: datetime
    updated_at: datetime
    roles: List[str] = Field(default_factory=list, description="角色列表")
    permissions: List[str] = Field(default_factory=list, description="权限列表")
    department: Optional[DepartmentInfo] = Field(None, description="部门信息")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class RoleInfo(BaseModel):
    """角色信息模型"""
    name: str = Field(..., description="角色名称")
    display_name: str = Field(..., description="角色显示名称")


class UserListResponse(BaseModel):
    """用户列表响应模型"""
    id: int
    username: str
    email: str
    real_name: Optional[str]
    phone: Optional[str] = Field(None, description="手机号")
    sex: Optional[SexType] = Field(None, description="性别")
    status: UserStatus
    last_login_at: Optional[datetime]
    created_at: datetime
    roles: List[RoleInfo] = Field(default_factory=list, description="角色列表")
    department: Optional[DepartmentInfo] = Field(None, description="部门信息")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class UserProfileBase(BaseModel):
    """用户档案基础模型"""
    voice_experience: Optional[str] = Field(None, max_length=1000, description="配音经验")
    voice_characteristics: Optional[str] = Field(None, max_length=500, description="声音特点")
    specialties: Optional[List[str]] = Field(default_factory=list, description="专长领域")
    equipment_info: Optional[str] = Field(None, max_length=500, description="设备信息")
    work_schedule: Optional[str] = Field(None, max_length=500, description="工作时间安排")
    emergency_contact: Optional[str] = Field(None, max_length=100, description="紧急联系人")
    emergency_phone: Optional[str] = Field(None, max_length=20, description="紧急联系电话")
    
    @validator('emergency_phone')
    def validate_emergency_phone(cls, v):
        if v and not v.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise ValueError('紧急联系电话格式不正确')
        return v


class UserProfileCreate(UserProfileBase):
    """创建用户档案模型"""
    pass


class UserProfileUpdate(UserProfileBase):
    """更新用户档案模型"""
    pass


class UserProfileResponse(UserProfileBase):
    """用户档案响应模型"""
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class UserLogin(BaseModel):
    """用户登录模型"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")
    remember_me: bool = Field(False, description="记住我")


class UserRegister(UserCreate):
    """用户注册模型"""
    invitation_code: Optional[str] = Field(None, description="邀请码")
    agree_terms: bool = Field(..., description="同意服务条款")
    
    @validator('agree_terms')
    def must_agree_terms(cls, v):
        if not v:
            raise ValueError('必须同意服务条款')
        return v


class TokenResponse(BaseModel):
    """Token响应模型"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    user: UserResponse


class RefreshTokenRequest(BaseModel):
    """刷新Token请求模型"""
    refresh_token: str = Field(..., description="刷新令牌")


class UserSearchQuery(BaseModel):
    """用户搜索查询参数"""
    keyword: Optional[str] = Field(None, description="关键词搜索（用户名、邮箱、真实姓名）")
    username: Optional[str] = Field(None, description="真实姓名（模糊匹配）")
    phone: Optional[str] = Field(None, description="手机号码（模糊匹配）")
    sex: Optional[SexType] = Field(None, description="性别")
    status: Optional[int] = Field(None, description="用户状态")
    dept_id: Optional[int] = Field(None, description="部门ID")
    role: Optional[str] = Field(None, description="角色名称")
    created_after: Optional[datetime] = Field(None, description="创建时间起始")
    created_before: Optional[datetime] = Field(None, description="创建时间结束")
    last_login_after: Optional[datetime] = Field(None, description="最后登录时间起始")
    last_login_before: Optional[datetime] = Field(None, description="最后登录时间结束")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    order_by: Optional[str] = Field("created_at", description="排序字段")
    order_desc: bool = Field(True, description="是否降序排列")


class UserBatchOperation(BaseModel):
    """用户批量操作模型"""
    user_ids: List[int] = Field(..., min_items=1, description="用户ID列表")
    operation: str = Field(..., description="操作类型：activate, deactivate, suspend, delete")
    reason: Optional[str] = Field(None, max_length=500, description="操作原因")
    
    @validator('operation')
    def validate_operation(cls, v):
        allowed_operations = ['activate', 'deactivate', 'suspend', 'delete']
        if v not in allowed_operations:
            raise ValueError(f'操作类型必须是: {", ".join(allowed_operations)}')
        return v


class UserStatistics(BaseModel):
    """用户统计模型"""
    total_users: int
    active_users: int
    inactive_users: int
    suspended_users: int
    new_users_today: int
    new_users_this_week: int
    new_users_this_month: int
    login_users_today: int
    login_users_this_week: int
    role_distribution: Dict[str, int]
    
    class Config:
        from_attributes = True


# 为了向后兼容，创建别名
PasswordChange = UserPasswordUpdate