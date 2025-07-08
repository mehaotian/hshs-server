from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class AudioStatus(str, Enum):
    """音频状态枚举"""
    PENDING = "pending"  # 待审听
    FIRST_REVIEW = "first_review"  # 一审中
    SECOND_REVIEW = "second_review"  # 二审中
    APPROVED = "approved"  # 已通过
    REJECTED = "rejected"  # 需反音
    ARCHIVED = "archived"  # 已归档


class AudioFormat(str, Enum):
    """音频格式枚举"""
    MP3 = "mp3"
    WAV = "wav"
    FLAC = "flac"
    M4A = "m4a"
    AAC = "aac"


class ReviewType(int, Enum):
    """审听类型枚举"""
    FIRST = 1  # 一审
    SECOND = 2  # 二审


class ReviewResult(int, Enum):
    """审听结果枚举"""
    REJECTED = 0  # 不通过
    APPROVED = 1  # 通过


class FeedbackType(str, Enum):
    """反音类型枚举"""
    TECHNICAL = "technical"  # 技术问题
    CONTENT = "content"  # 内容问题


class FeedbackStatus(int, Enum):
    """反音状态枚举"""
    PENDING = 0  # 待处理
    IN_PROGRESS = 1  # 处理中
    COMPLETED = 2  # 已完成
    CANCELLED = 3  # 已取消


class CVRecordingBase(BaseModel):
    """CV录音基础模型"""
    character_name: Optional[str] = Field(None, max_length=100, description="角色名称")
    file_name: Optional[str] = Field(None, max_length=255, description="原始文件名")
    remarks: Optional[str] = Field(None, max_length=1000, description="CV备注")
    tags: Optional[List[str]] = Field(default_factory=list, description="标签")
    
    @validator('tags')
    def validate_tags(cls, v):
        if v and len(v) > 10:
            raise ValueError('标签数量不能超过10个')
        return v


class CVRecordingCreate(CVRecordingBase):
    """创建CV录音模型"""
    script_id: int = Field(..., description="剧本ID")
    chapter_id: Optional[int] = Field(None, description="章节ID")
    file_url: str = Field(..., max_length=500, description="音频文件URL")


class CVRecordingUpdate(BaseModel):
    """更新CV录音模型"""
    character_name: Optional[str] = Field(None, max_length=100, description="角色名称")
    remarks: Optional[str] = Field(None, max_length=1000, description="CV备注")
    tags: Optional[List[str]] = Field(None, description="标签")
    metadata: Optional[Dict[str, Any]] = Field(None, description="扩展元数据")
    
    @validator('tags')
    def validate_tags(cls, v):
        if v and len(v) > 10:
            raise ValueError('标签数量不能超过10个')
        return v


class CVRecordingResponse(CVRecordingBase):
    """CV录音响应模型"""
    id: int
    script_id: int
    chapter_id: Optional[int]
    cv_user_id: int
    file_url: str
    file_size: Optional[int]
    file_size_formatted: str
    duration: Optional[int]
    duration_formatted: str
    format: Optional[str]
    bitrate: Optional[int]
    sample_rate: Optional[int]
    channels: Optional[int]
    status: AudioStatus
    status_name: str
    version: int
    is_latest: bool
    quality_score: Optional[float]
    uploaded_at: datetime
    created_at: datetime
    updated_at: datetime
    
    # 关联数据
    script: Optional[Dict[str, Any]] = None
    chapter: Optional[Dict[str, Any]] = None
    cv_user: Optional[Dict[str, Any]] = None
    latest_review: Optional['ReviewRecordResponse'] = None
    review_count: int = 0
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class CVRecordingDetailResponse(CVRecordingResponse):
    """CV录音详情响应模型"""
    technical_issues: Optional[List[str]] = None
    content_issues: Optional[List[str]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    review_history: List['ReviewRecordResponse'] = Field(default_factory=list)
    feedback_records: List['FeedbackRecordResponse'] = Field(default_factory=list)


class ReviewRecordBase(BaseModel):
    """审听记录基础模型"""
    review_type: ReviewType = Field(..., description="审听类型")
    result: ReviewResult = Field(..., description="审听结果")
    score: Optional[int] = Field(None, ge=1, le=10, description="总体评分")
    technical_score: Optional[int] = Field(None, ge=1, le=10, description="技术评分")
    content_score: Optional[int] = Field(None, ge=1, le=10, description="内容评分")
    technical_issues: Optional[List[str]] = Field(default_factory=list, description="技术问题")
    content_issues: Optional[List[str]] = Field(default_factory=list, description="内容问题")
    suggestions: Optional[str] = Field(None, max_length=2000, description="改进建议")
    comments: Optional[str] = Field(None, max_length=2000, description="审听评语")
    review_duration: Optional[int] = Field(None, ge=0, description="审听用时（秒）")


class ReviewRecordCreate(ReviewRecordBase):
    """创建审听记录模型"""
    recording_id: int = Field(..., description="录音ID")


class ReviewRecordUpdate(BaseModel):
    """更新审听记录模型"""
    result: Optional[ReviewResult] = Field(None, description="审听结果")
    score: Optional[int] = Field(None, ge=1, le=10, description="总体评分")
    technical_score: Optional[int] = Field(None, ge=1, le=10, description="技术评分")
    content_score: Optional[int] = Field(None, ge=1, le=10, description="内容评分")
    technical_issues: Optional[List[str]] = Field(None, description="技术问题")
    content_issues: Optional[List[str]] = Field(None, description="内容问题")
    suggestions: Optional[str] = Field(None, max_length=2000, description="改进建议")
    comments: Optional[str] = Field(None, max_length=2000, description="审听评语")
    review_duration: Optional[int] = Field(None, ge=0, description="审听用时（秒）")


class ReviewRecordResponse(ReviewRecordBase):
    """审听记录响应模型"""
    id: int
    recording_id: int
    reviewer_id: int
    review_type_name: str
    result_name: str
    is_passed: bool
    reviewed_at: datetime
    created_at: datetime
    
    # 关联数据
    reviewer: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class FeedbackRecordBase(BaseModel):
    """反音记录基础模型"""
    feedback_type: FeedbackType = Field(..., description="反音类型")
    issues: List[str] = Field(..., min_items=1, description="问题列表")
    requirements: Optional[str] = Field(None, max_length=2000, description="具体要求")
    deadline: Optional[datetime] = Field(None, description="反音截止时间")
    priority: int = Field(0, ge=0, le=2, description="优先级：0-普通，1-高，2-紧急")
    
    @validator('deadline')
    def validate_deadline(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError('截止时间必须大于当前时间')
        return v


class FeedbackRecordCreate(FeedbackRecordBase):
    """创建反音记录模型"""
    recording_id: int = Field(..., description="录音ID")
    cv_user_id: int = Field(..., description="CV用户ID")


class FeedbackRecordUpdate(BaseModel):
    """更新反音记录模型"""
    issues: Optional[List[str]] = Field(None, min_items=1, description="问题列表")
    requirements: Optional[str] = Field(None, max_length=2000, description="具体要求")
    deadline: Optional[datetime] = Field(None, description="反音截止时间")
    priority: Optional[int] = Field(None, ge=0, le=2, description="优先级")
    status: Optional[FeedbackStatus] = Field(None, description="状态")
    cv_response: Optional[str] = Field(None, max_length=1000, description="CV回复")
    completion_notes: Optional[str] = Field(None, max_length=1000, description="完成备注")
    
    @validator('deadline')
    def validate_deadline(cls, v):
        if v and v <= datetime.utcnow():
            raise ValueError('截止时间必须大于当前时间')
        return v


class FeedbackRecordResponse(FeedbackRecordBase):
    """反音记录响应模型"""
    id: int
    recording_id: int
    initiated_by: int
    cv_user_id: int
    status: FeedbackStatus
    status_name: str
    cv_response: Optional[str]
    completion_notes: Optional[str]
    is_overdue: bool
    initiated_at: datetime
    responded_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    # 关联数据
    initiator: Optional[Dict[str, Any]] = None
    cv_user: Optional[Dict[str, Any]] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class AudioTemplateBase(BaseModel):
    """音频模板基础模型"""
    name: str = Field(..., min_length=1, max_length=100, description="模板名称")
    description: Optional[str] = Field(None, max_length=500, description="模板描述")
    required_format: Optional[AudioFormat] = Field(None, description="要求格式")
    min_bitrate: Optional[int] = Field(None, ge=64, description="最小比特率")
    required_sample_rate: Optional[int] = Field(None, ge=8000, description="要求采样率")
    required_channels: Optional[int] = Field(None, ge=1, le=8, description="要求声道数")
    max_file_size: Optional[int] = Field(None, ge=1024, description="最大文件大小（字节）")
    quality_standards: Optional[Dict[str, Any]] = Field(default_factory=dict, description="质量标准")
    technical_checklist: Optional[List[str]] = Field(default_factory=list, description="技术检查清单")
    content_checklist: Optional[List[str]] = Field(default_factory=list, description="内容检查清单")
    script_types: Optional[List[str]] = Field(default_factory=list, description="适用剧本类型")


class AudioTemplateCreate(AudioTemplateBase):
    """创建音频模板模型"""
    pass


class AudioTemplateUpdate(BaseModel):
    """更新音频模板模型"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="模板名称")
    description: Optional[str] = Field(None, max_length=500, description="模板描述")
    required_format: Optional[AudioFormat] = Field(None, description="要求格式")
    min_bitrate: Optional[int] = Field(None, ge=64, description="最小比特率")
    required_sample_rate: Optional[int] = Field(None, ge=8000, description="要求采样率")
    required_channels: Optional[int] = Field(None, ge=1, le=8, description="要求声道数")
    max_file_size: Optional[int] = Field(None, ge=1024, description="最大文件大小（字节）")
    quality_standards: Optional[Dict[str, Any]] = Field(None, description="质量标准")
    technical_checklist: Optional[List[str]] = Field(None, description="技术检查清单")
    content_checklist: Optional[List[str]] = Field(None, description="内容检查清单")
    script_types: Optional[List[str]] = Field(None, description="适用剧本类型")
    is_default: Optional[bool] = Field(None, description="是否默认模板")


class AudioTemplateResponse(AudioTemplateBase):
    """音频模板响应模型"""
    id: int
    is_default: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


class AudioSearchQuery(BaseModel):
    """音频搜索查询模型"""
    keyword: Optional[str] = Field(None, description="关键词搜索（文件名、角色名称）")
    script_id: Optional[int] = Field(None, description="剧本ID")
    chapter_id: Optional[int] = Field(None, description="章节ID")
    cv_user_id: Optional[int] = Field(None, description="CV用户ID")
    status: Optional[AudioStatus] = Field(None, description="音频状态")
    format: Optional[AudioFormat] = Field(None, description="音频格式")
    is_latest: Optional[bool] = Field(None, description="是否最新版本")
    quality_score_min: Optional[float] = Field(None, ge=0, le=10, description="最低质量评分")
    quality_score_max: Optional[float] = Field(None, ge=0, le=10, description="最高质量评分")
    uploaded_after: Optional[datetime] = Field(None, description="上传时间起始")
    uploaded_before: Optional[datetime] = Field(None, description="上传时间结束")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    order_by: str = Field("uploaded_at", description="排序字段")
    order_desc: bool = Field(True, description="是否降序")


class ReviewSearchQuery(BaseModel):
    """审听搜索查询模型"""
    recording_id: Optional[int] = Field(None, description="录音ID")
    reviewer_id: Optional[int] = Field(None, description="审听者ID")
    review_type: Optional[ReviewType] = Field(None, description="审听类型")
    result: Optional[ReviewResult] = Field(None, description="审听结果")
    score_min: Optional[int] = Field(None, ge=1, le=10, description="最低评分")
    score_max: Optional[int] = Field(None, ge=1, le=10, description="最高评分")
    reviewed_after: Optional[datetime] = Field(None, description="审听时间起始")
    reviewed_before: Optional[datetime] = Field(None, description="审听时间结束")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    order_by: str = Field("reviewed_at", description="排序字段")
    order_desc: bool = Field(True, description="是否降序")


class FeedbackSearchQuery(BaseModel):
    """反音搜索查询模型"""
    recording_id: Optional[int] = Field(None, description="录音ID")
    initiated_by: Optional[int] = Field(None, description="发起者ID")
    cv_user_id: Optional[int] = Field(None, description="CV用户ID")
    feedback_type: Optional[FeedbackType] = Field(None, description="反音类型")
    status: Optional[FeedbackStatus] = Field(None, description="反音状态")
    priority: Optional[int] = Field(None, ge=0, le=2, description="优先级")
    is_overdue: Optional[bool] = Field(None, description="是否过期")
    initiated_after: Optional[datetime] = Field(None, description="发起时间起始")
    initiated_before: Optional[datetime] = Field(None, description="发起时间结束")
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(20, ge=1, le=100, description="每页数量")
    order_by: str = Field("initiated_at", description="排序字段")
    order_desc: bool = Field(True, description="是否降序")


class AudioStatistics(BaseModel):
    """音频统计模型"""
    total_recordings: int
    pending_recordings: int
    approved_recordings: int
    rejected_recordings: int
    total_reviews: int
    first_reviews: int
    second_reviews: int
    total_feedbacks: int
    pending_feedbacks: int
    overdue_feedbacks: int
    recordings_by_status: Dict[str, int]
    recordings_by_format: Dict[str, int]
    average_quality_score: Optional[float]
    review_pass_rate: Optional[float]
    
    class Config:
        from_attributes = True


class AudioBatchOperation(BaseModel):
    """音频批量操作模型"""
    recording_ids: List[int] = Field(..., min_items=1, description="录音ID列表")
    operation: str = Field(..., description="操作类型：approve, reject, archive, delete")
    reason: Optional[str] = Field(None, max_length=500, description="操作原因")
    
    @validator('operation')
    def validate_operation(cls, v):
        allowed_operations = ['approve', 'reject', 'archive', 'delete']
        if v not in allowed_operations:
            raise ValueError(f'操作类型必须是: {", ".join(allowed_operations)}')
        return v


class AudioQualityCheck(BaseModel):
    """音频质量检查模型"""
    recording_id: int = Field(..., description="录音ID")
    check_technical: bool = Field(True, description="检查技术质量")
    check_content: bool = Field(True, description="检查内容质量")
    template_id: Optional[int] = Field(None, description="使用的模板ID")


class AudioQualityResult(BaseModel):
    """音频质量检查结果模型"""
    overall_score: float = Field(..., ge=0, le=10, description="总体评分")
    technical_score: float = Field(..., ge=0, le=10, description="技术评分")
    content_score: float = Field(..., ge=0, le=10, description="内容评分")
    technical_issues: List[str] = Field(default_factory=list, description="技术问题")
    content_issues: List[str] = Field(default_factory=list, description="内容问题")
    suggestions: List[str] = Field(default_factory=list, description="改进建议")
    is_qualified: bool = Field(..., description="是否合格")
    checked_at: datetime = Field(..., description="检查时间")
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }


# 前向引用解决
CVRecordingResponse.model_rebuild()
CVRecordingDetailResponse.model_rebuild()