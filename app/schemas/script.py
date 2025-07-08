from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ScriptStatus(str, Enum):
    """剧本状态枚举"""
    DRAFT = "draft"  # 草稿
    REVIEWING = "reviewing"  # 审核中
    APPROVED = "approved"  # 已通过
    REJECTED = "rejected"  # 已拒绝
    PUBLISHED = "published"  # 已发布
    ARCHIVED = "archived"  # 已归档


class ScriptType(str, Enum):
    """剧本类型枚举"""
    ORIGINAL = "original"  # 原创
    ADAPTED = "adapted"  # 改编
    TRANSLATED = "translated"  # 翻译
    COLLABORATION = "collaboration"  # 合作


class AssignmentStatus(str, Enum):
    """分配状态枚举"""
    PENDING = "pending"  # 待确认
    ACCEPTED = "accepted"  # 已接受
    REJECTED = "rejected"  # 已拒绝
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消


class DramaSocietyBase(BaseModel):
    """剧社基础模型"""
    name: str = Field(..., min_length=2, max_length=100, description="剧社名称")
    description: Optional[str] = Field(None, max_length=1000, description="剧社描述")
    logo_url: Optional[str] = Field(None, max_length=500, description="剧社Logo URL")
    website: Optional[str] = Field(None, max_length=200, description="官方网站")
    contact_email: Optional[str] = Field(None, max_length=100, description="联系邮箱")
    contact_phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    social_links: Optional[Dict[str, str]] = Field(default_factory=dict, description="社交媒体链接")
    
    @validator('contact_phone')
    def validate_phone(cls, v):
        if v and not v.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise ValueError('联系电话格式不正确')
        return v


class DramaSocietyCreate(DramaSocietyBase):
    """创建剧社模型"""
    pass


class DramaSocietyUpdate(BaseModel):
    """更新剧社模型"""
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="剧社名称")
    description: Optional[str] = Field(None, max_length=1000, description="剧社描述")
    logo_url: Optional[str] = Field(None, max_length=500, description="剧社Logo URL")
    website: Optional[str] = Field(None, max_length=200, description="官方网站")
    contact_email: Optional[str] = Field(None, max_length=100, description="联系邮箱")
    contact_phone: Optional[str] = Field(None, max_length=20, description="联系电话")
    social_links: Optional[Dict[str, str]] = Field(None, description="社交媒体链接")
    settings: Optional[Dict[str, Any]] = Field(None, description="剧社设置")
    
    @validator('contact_phone')
    def validate_phone(cls, v):
        if v and not v.replace('+', '').replace('-', '').replace(' ', '').isdigit():
            raise ValueError('联系电话格式不正确')
        return v


class DramaSocietyResponse(DramaSocietyBase):
    """剧社响应模型"""
    id: int
    owner_id: int
    member_count: int
    script_count: int
    is_active: bool
    settings: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class ScriptBase(BaseModel):
    """剧本基础模型"""
    title: str = Field(..., min_length=1, max_length=200, description="剧本标题")
    description: Optional[str] = Field(None, max_length=2000, description="剧本描述")
    script_type: ScriptType = Field(..., description="剧本类型")
    genre: Optional[str] = Field(None, max_length=100, description="剧本类别")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签")
    cover_url: Optional[str] = Field(None, max_length=500, description="封面图片URL")
    estimated_duration: Optional[int] = Field(None, ge=0, description="预计时长（分钟）")
    target_audience: Optional[str] = Field(None, max_length=100, description="目标受众")
    content_rating: Optional[str] = Field(None, max_length=20, description="内容分级")
    
    @validator('tags')
    def validate_tags(cls, v):
        if v and len(v) > 20:
            raise ValueError('标签数量不能超过20个')
        return v


class ScriptCreate(ScriptBase):
    """创建剧本模型"""
    society_id: int = Field(..., description="剧社ID")
    content: Optional[str] = Field(None, description="剧本内容")


class ScriptUpdate(BaseModel):
    """更新剧本模型"""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="剧本标题")
    description: Optional[str] = Field(None, max_length=2000, description="剧本描述")
    script_type: Optional[ScriptType] = Field(None, description="剧本类型")
    genre: Optional[str] = Field(None, max_length=100, description="剧本类别")
    tags: Optional[List[str]] = Field(None, description="标签")
    cover_url: Optional[str] = Field(None, max_length=500, description="封面图片URL")
    estimated_duration: Optional[int] = Field(None, ge=0, description="预计时长（分钟）")
    target_audience: Optional[str] = Field(None, max_length=100, description="目标受众")
    content_rating: Optional[str] = Field(None, max_length=20, description="内容分级")
    content: Optional[str] = Field(None, description="剧本内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="扩展元数据")
    
    @validator('tags')
    def validate_tags(cls, v):
        if v and len(v) > 20:
            raise ValueError('标签数量不能超过20个')
        return v


class ScriptResponse(ScriptBase):
    """剧本响应模型"""
    id: int
    society_id: int
    author_id: int
    status: ScriptStatus
    version: int
    word_count: int
    chapter_count: int
    assignment_count: int
    recording_count: int
    view_count: int
    like_count: int
    is_public: bool
    published_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    # 关联数据
    society: Optional[DramaSocietyResponse] = None
    author: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class ScriptDetailResponse(ScriptResponse):
    """剧本详情响应模型"""
    content: Optional[str] = None
    metadata: Dict[str, Any]
    chapters: List['ScriptChapterResponse'] = Field(default_factory=list)
    assignments: List['ScriptAssignmentResponse'] = Field(default_factory=list)


class ScriptChapterBase(BaseModel):
    """剧本章节基础模型"""
    title: str = Field(..., min_length=1, max_length=200, description="章节标题")
    content: str = Field(..., min_length=1, description="章节内容")
    chapter_number: int = Field(..., ge=1, description="章节序号")
    description: Optional[str] = Field(None, max_length=500, description="章节描述")
    estimated_duration: Optional[int] = Field(None, ge=0, description="预计时长（分钟）")
    character_list: Optional[List[str]] = Field(default_factory=list, description="角色列表")
    notes: Optional[str] = Field(None, max_length=1000, description="章节备注")


class ScriptChapterCreate(ScriptChapterBase):
    """创建剧本章节模型"""
    script_id: int = Field(..., description="剧本ID")


class ScriptChapterUpdate(BaseModel):
    """更新剧本章节模型"""
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="章节标题")
    content: Optional[str] = Field(None, min_length=1, description="章节内容")
    chapter_number: Optional[int] = Field(None, ge=1, description="章节序号")
    description: Optional[str] = Field(None, max_length=500, description="章节描述")
    estimated_duration: Optional[int] = Field(None, ge=0, description="预计时长（分钟）")
    character_list: Optional[List[str]] = Field(None, description="角色列表")
    notes: Optional[str] = Field(None, max_length=1000, description="章节备注")
    metadata: Optional[Dict[str, Any]] = Field(None, description="扩展元数据")


class ScriptChapterResponse(ScriptChapterBase):
    """剧本章节响应模型"""
    id: int
    script_id: int
    word_count: int
    assignment_count: int
    recording_count: int
    is_completed: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class ScriptAssignmentBase(BaseModel):
    """剧本分配基础模型"""
    role_type: str = Field(..., max_length=50, description="角色类型")
    character_name: Optional[str] = Field(None, max_length=100, description="角色名称")
    requirements: Optional[str] = Field(None, max_length=1000, description="具体要求")
    deadline: Optional[datetime] = Field(None, description="截止时间")
    priority: int = Field(0, ge=0, le=2, description="优先级：0-普通，1-高，2-紧急")
    notes: Optional[str] = Field(None, max_length=500, description="备注")
    
    @validator('deadline')
    def validate_deadline(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError('截止时间必须大于当前时间')
        return v


class ScriptAssignmentCreate(ScriptAssignmentBase):
    """创建剧本分配模型"""
    script_id: int = Field(..., description="剧本ID")
    chapter_id: Optional[int] = Field(None, description="章节ID")
    assigned_to: int = Field(..., description="分配给用户ID")


class ScriptAssignmentUpdate(BaseModel):
    """更新剧本分配模型"""
    role_type: Optional[str] = Field(None, max_length=50, description="角色类型")
    character_name: Optional[str] = Field(None, max_length=100, description="角色名称")
    requirements: Optional[str] = Field(None, max_length=1000, description="具体要求")
    deadline: Optional[datetime] = Field(None, description="截止时间")
    priority: Optional[int] = Field(None, ge=0, le=2, description="优先级")
    notes: Optional[str] = Field(None, max_length=500, description="备注")
    status: Optional[AssignmentStatus] = Field(None, description="分配状态")
    
    @validator('deadline')
    def validate_deadline(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError('截止时间必须大于当前时间')
        return v


class ScriptAssignmentResponse(ScriptAssignmentBase):
    """剧本分配响应模型"""
    id: int
    script_id: int
    chapter_id: Optional[int]
    assigned_to: int
    assigned_by: int
    status: AssignmentStatus
    accepted_at: Optional[datetime]
    completed_at: Optional[datetime]
    is_overdue: bool
    created_at: datetime
    updated_at: datetime
    
    # 关联数据
    script: Optional[Dict[str, Any]] = None
    chapter: Optional[Dict[str, Any]] = None
    assignee: Optional[Dict[str, Any]] = None
    assigner: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class ScriptSearchQuery(BaseModel):
    """剧本搜索查询模型"""
    keyword: Optional[str] = Field(None, description="关键词搜索（标题、描述）")
    society_id: Optional[int] = Field(None, description="剧社ID")
    author_id: Optional[int] = Field(None, description="作者ID")
    status: Optional[ScriptStatus] = Field(None, description="剧本状态")
    script_type: Optional[ScriptType] = Field(None, description="剧本类型")
    genre: Optional[str] = Field(None, description="剧本类别")
    tags: Optional[List[str]] = Field(None, description="标签筛选")
    is_public: Optional[bool] = Field(None, description="是否公开")
    created_after: Optional[datetime] = Field(None, description="创建时间起始")
    created_before: Optional[datetime] = Field(None, description="创建时间结束")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    order_by: str = Field("created_at", description="排序字段")
    order_desc: bool = Field(True, description="是否降序")


class AssignmentSearchQuery(BaseModel):
    """分配搜索查询模型"""
    script_id: Optional[int] = Field(None, description="剧本ID")
    chapter_id: Optional[int] = Field(None, description="章节ID")
    assigned_to: Optional[int] = Field(None, description="分配给用户ID")
    assigned_by: Optional[int] = Field(None, description="分配者ID")
    status: Optional[AssignmentStatus] = Field(None, description="分配状态")
    role_type: Optional[str] = Field(None, description="角色类型")
    is_overdue: Optional[bool] = Field(None, description="是否过期")
    deadline_after: Optional[datetime] = Field(None, description="截止时间起始")
    deadline_before: Optional[datetime] = Field(None, description="截止时间结束")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    order_by: str = Field("created_at", description="排序字段")
    order_desc: bool = Field(True, description="是否降序")


class ScriptStatistics(BaseModel):
    """剧本统计模型"""
    total_scripts: int
    draft_scripts: int
    published_scripts: int
    total_chapters: int
    total_assignments: int
    pending_assignments: int
    completed_assignments: int
    overdue_assignments: int
    scripts_by_type: Dict[str, int]
    scripts_by_status: Dict[str, int]
    popular_genres: Dict[str, int]
    
    class Config:
        from_attributes = True


class ScriptBatchOperation(BaseModel):
    """剧本批量操作模型"""
    script_ids: List[int] = Field(..., min_items=1, description="剧本ID列表")
    operation: str = Field(..., description="操作类型：publish, archive, delete")
    reason: Optional[str] = Field(None, max_length=500, description="操作原因")
    
    @validator('operation')
    def validate_operation(cls, v):
        allowed_operations = ['publish', 'archive', 'delete', 'approve', 'reject']
        if v not in allowed_operations:
            raise ValueError(f'操作类型必须是: {", ".join(allowed_operations)}')
        return v


class ScriptImportExport(BaseModel):
    """剧本导入导出模型"""
    format: str = Field(..., description="格式：json, csv, txt")
    include_chapters: bool = Field(True, description="是否包含章节")
    include_assignments: bool = Field(False, description="是否包含分配")
    filter_status: Optional[List[ScriptStatus]] = Field(None, description="状态筛选")
    
    @validator('format')
    def validate_format(cls, v):
        allowed_formats = ['json', 'csv', 'txt']
        if v not in allowed_formats:
            raise ValueError(f'格式必须是: {", ".join(allowed_formats)}')
        return v


# 前向引用解决
ScriptDetailResponse.model_rebuild()