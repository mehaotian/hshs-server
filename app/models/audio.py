from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, BigInteger, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Dict, List, Any, Optional
from enum import Enum

from app.core.database import Base


class AudioStatus(Enum):
    """音频状态枚举"""
    PENDING = 0  # 待审听
    FIRST_REVIEW = 1  # 一审中
    SECOND_REVIEW = 2  # 二审中
    APPROVED = 3  # 已通过
    REJECTED = 4  # 需反音
    ARCHIVED = 5  # 已归档


class AudioFormat(Enum):
    """音频格式枚举"""
    MP3 = "mp3"
    WAV = "wav"
    FLAC = "flac"
    M4A = "m4a"
    AAC = "aac"


class CVRecording(Base):
    """CV交音记录模型"""
    __tablename__ = "cv_recordings"
    __table_args__ = {'comment': 'CV交音记录表'}

    id = Column(Integer, primary_key=True, index=True, comment="录音ID")
    script_id = Column(Integer, ForeignKey('scripts.id'), nullable=False, comment="剧本ID")
    chapter_id = Column(Integer, ForeignKey('script_chapters.id'), nullable=True, comment="章节ID")
    cv_user_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment="CV用户ID")
    character_name = Column(String(100), nullable=True, comment="角色名称")
    
    # 文件信息
    file_url = Column(String(500), nullable=False, comment="音频文件URL")
    file_name = Column(String(255), nullable=True, comment="原始文件名")
    file_size = Column(BigInteger, nullable=True, comment="文件大小（字节）")
    duration = Column(Integer, nullable=True, comment="音频时长（秒）")
    format = Column(String(20), nullable=True, comment="音频格式")
    bitrate = Column(Integer, nullable=True, comment="比特率")
    sample_rate = Column(Integer, nullable=True, comment="采样率")
    channels = Column(Integer, nullable=True, comment="声道数")
    
    # 状态和版本
    status = Column(Integer, default=AudioStatus.PENDING.value, comment="音频状态")
    version = Column(Integer, default=1, comment="版本号")
    is_latest = Column(Integer, default=1, comment="是否最新版本：1-是，0-否")
    
    # 质量信息
    quality_score = Column(Float, nullable=True, comment="质量评分（1-10）")
    technical_issues = Column(JSON, nullable=True, comment="技术问题列表")
    content_issues = Column(JSON, nullable=True, comment="内容问题列表")
    
    # 备注和标签
    remarks = Column(Text, nullable=True, comment="CV备注")
    tags = Column(JSON, nullable=True, comment="标签")
    extra_metadata = Column(JSON, nullable=True, comment="扩展元数据")
    
    # 时间信息
    uploaded_at = Column(DateTime, default=func.now(), comment="上传时间")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关系映射
    script = relationship("Script", back_populates="cv_recordings")
    chapter = relationship("ScriptChapter", back_populates="cv_recordings")
    cv_user = relationship("User", back_populates="cv_recordings")
    review_records = relationship("ReviewRecord", back_populates="recording", cascade="all, delete-orphan")
    feedback_records = relationship("FeedbackRecord", back_populates="recording", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<CVRecording(id={self.id}, script_id={self.script_id}, cv_user_id={self.cv_user_id})>"
    
    @property
    def status_name(self) -> str:
        """获取状态名称"""
        status_map = {
            AudioStatus.PENDING.value: "待审听",
            AudioStatus.FIRST_REVIEW.value: "一审中",
            AudioStatus.SECOND_REVIEW.value: "二审中",
            AudioStatus.APPROVED.value: "已通过",
            AudioStatus.REJECTED.value: "需反音",
            AudioStatus.ARCHIVED.value: "已归档"
        }
        return status_map.get(self.status, "未知")
    
    @property
    def duration_formatted(self) -> str:
        """格式化时长显示"""
        if not self.duration:
            return "未知"
        
        minutes = self.duration // 60
        seconds = self.duration % 60
        return f"{minutes:02d}:{seconds:02d}"
    
    @property
    def file_size_formatted(self) -> str:
        """格式化文件大小显示"""
        if not self.file_size:
            return "未知"
        
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"
    
    def get_latest_review(self) -> Optional['ReviewRecord']:
        """获取最新的审听记录"""
        if not self.review_records:
            return None
        return max(self.review_records, key=lambda x: x.reviewed_at)
    
    def get_review_history(self) -> List['ReviewRecord']:
        """获取审听历史记录"""
        return sorted(self.review_records, key=lambda x: x.reviewed_at, reverse=True)
    
    def to_dict(self, include_details: bool = False) -> Dict[str, Any]:
        """转换为字典格式"""
        data = {
            'id': self.id,
            'script_id': self.script_id,
            'chapter_id': self.chapter_id,
            'cv_user_id': self.cv_user_id,
            'character_name': self.character_name,
            'file_url': self.file_url,
            'file_name': self.file_name,
            'file_size': self.file_size,
            'file_size_formatted': self.file_size_formatted,
            'duration': self.duration,
            'duration_formatted': self.duration_formatted,
            'format': self.format,
            'bitrate': self.bitrate,
            'sample_rate': self.sample_rate,
            'channels': self.channels,
            'status': self.status,
            'status_name': self.status_name,
            'version': self.version,
            'is_latest': bool(self.is_latest),
            'quality_score': self.quality_score,
            'remarks': self.remarks,
            'tags': self.tags,
            'uploaded_at': self.uploaded_at.isoformat() if self.uploaded_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_details:
            data.update({
                'technical_issues': self.technical_issues,
                'content_issues': self.content_issues,
                'extra_metadata': self.extra_metadata,
                'script': self.script.to_dict() if self.script else None,
                'chapter': self.chapter.to_dict() if self.chapter else None,
                'cv_user': self.cv_user.to_dict() if self.cv_user else None,
                'latest_review': self.get_latest_review().to_dict() if self.get_latest_review() else None,
                'review_count': len(self.review_records),
            })
        
        return data


class ReviewRecord(Base):
    """审听记录模型"""
    __tablename__ = "review_records"
    __table_args__ = {'comment': '审听记录表'}

    id = Column(Integer, primary_key=True, index=True, comment="审听记录ID")
    recording_id = Column(Integer, ForeignKey('cv_recordings.id', ondelete='CASCADE'), nullable=False, comment="录音ID")
    reviewer_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment="审听者ID")
    review_type = Column(Integer, nullable=False, comment="审听类型：1-一审，2-二审")
    result = Column(Integer, nullable=False, comment="审听结果：1-通过，0-不通过")
    
    # 评分和评价
    score = Column(Integer, nullable=True, comment="评分（1-10）")
    technical_score = Column(Integer, nullable=True, comment="技术评分（1-10）")
    content_score = Column(Integer, nullable=True, comment="内容评分（1-10）")
    
    # 问题和建议
    technical_issues = Column(JSON, nullable=True, comment="技术问题")
    content_issues = Column(JSON, nullable=True, comment="内容问题")
    suggestions = Column(Text, nullable=True, comment="改进建议")
    comments = Column(Text, nullable=True, comment="审听评语")
    
    # 时间信息
    review_duration = Column(Integer, nullable=True, comment="审听用时（秒）")
    reviewed_at = Column(DateTime, default=func.now(), comment="审听时间")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")

    # 关系映射
    recording = relationship("CVRecording", back_populates="review_records")
    reviewer = relationship("User", back_populates="review_records")
    
    def __repr__(self) -> str:
        return f"<ReviewRecord(id={self.id}, recording_id={self.recording_id}, reviewer_id={self.reviewer_id})>"
    
    @property
    def review_type_name(self) -> str:
        """获取审听类型名称"""
        return "一审" if self.review_type == 1 else "二审"
    
    @property
    def result_name(self) -> str:
        """获取审听结果名称"""
        return "通过" if self.result == 1 else "不通过"
    
    @property
    def is_passed(self) -> bool:
        """是否通过审听"""
        return self.result == 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'recording_id': self.recording_id,
            'reviewer_id': self.reviewer_id,
            'review_type': self.review_type,
            'review_type_name': self.review_type_name,
            'result': self.result,
            'result_name': self.result_name,
            'is_passed': self.is_passed,
            'score': self.score,
            'technical_score': self.technical_score,
            'content_score': self.content_score,
            'technical_issues': self.technical_issues,
            'content_issues': self.content_issues,
            'suggestions': self.suggestions,
            'comments': self.comments,
            'review_duration': self.review_duration,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'reviewer': self.reviewer.to_dict() if self.reviewer else None,
        }


class FeedbackRecord(Base):
    """反音记录模型"""
    __tablename__ = "feedback_records"
    __table_args__ = {'comment': '反音记录表'}

    id = Column(Integer, primary_key=True, index=True, comment="反音记录ID")
    recording_id = Column(Integer, ForeignKey('cv_recordings.id', ondelete='CASCADE'), nullable=False, comment="录音ID")
    initiated_by = Column(Integer, ForeignKey('users.id'), nullable=False, comment="发起者ID")
    cv_user_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment="CV用户ID")
    
    # 反音内容
    feedback_type = Column(String(50), nullable=False, comment="反音类型：technical-技术，content-内容")
    issues = Column(JSON, nullable=False, comment="问题列表")
    requirements = Column(Text, nullable=True, comment="具体要求")
    deadline = Column(DateTime, nullable=True, comment="反音截止时间")
    priority = Column(Integer, default=0, comment="优先级：0-普通，1-高，2-紧急")
    
    # 状态跟踪
    status = Column(Integer, default=0, comment="状态：0-待处理，1-处理中，2-已完成，3-已取消")
    cv_response = Column(Text, nullable=True, comment="CV回复")
    completion_notes = Column(Text, nullable=True, comment="完成备注")
    
    # 时间信息
    initiated_at = Column(DateTime, default=func.now(), comment="发起时间")
    responded_at = Column(DateTime, nullable=True, comment="CV回复时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关系映射
    recording = relationship("CVRecording", back_populates="feedback_records")
    initiator = relationship("User", foreign_keys=[initiated_by])
    cv_user = relationship("User", foreign_keys=[cv_user_id])
    
    def __repr__(self) -> str:
        return f"<FeedbackRecord(id={self.id}, recording_id={self.recording_id}, status={self.status})>"
    
    @property
    def status_name(self) -> str:
        """获取状态名称"""
        status_map = {
            0: "待处理",
            1: "处理中",
            2: "已完成",
            3: "已取消"
        }
        return status_map.get(self.status, "未知")
    
    @property
    def is_overdue(self) -> bool:
        """检查是否已过期"""
        if not self.deadline or self.status in [2, 3]:  # 已完成或已取消
            return False
        from datetime import datetime
        return datetime.utcnow() > self.deadline
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'recording_id': self.recording_id,
            'initiated_by': self.initiated_by,
            'cv_user_id': self.cv_user_id,
            'feedback_type': self.feedback_type,
            'issues': self.issues,
            'requirements': self.requirements,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'priority': self.priority,
            'status': self.status,
            'status_name': self.status_name,
            'cv_response': self.cv_response,
            'completion_notes': self.completion_notes,
            'is_overdue': self.is_overdue,
            'initiated_at': self.initiated_at.isoformat() if self.initiated_at else None,
            'responded_at': self.responded_at.isoformat() if self.responded_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'initiator': self.initiator.to_dict() if self.initiator else None,
            'cv_user': self.cv_user.to_dict() if self.cv_user else None,
        }


class AudioTemplate(Base):
    """音频模板模型（用于标准化音频要求）"""
    __tablename__ = "audio_templates"
    __table_args__ = {'comment': '音频模板表'}

    id = Column(Integer, primary_key=True, index=True, comment="模板ID")
    name = Column(String(100), nullable=False, comment="模板名称")
    description = Column(Text, nullable=True, comment="模板描述")
    
    # 技术要求
    required_format = Column(String(20), nullable=True, comment="要求格式")
    min_bitrate = Column(Integer, nullable=True, comment="最小比特率")
    required_sample_rate = Column(Integer, nullable=True, comment="要求采样率")
    required_channels = Column(Integer, nullable=True, comment="要求声道数")
    max_file_size = Column(BigInteger, nullable=True, comment="最大文件大小")
    
    # 质量标准
    quality_standards = Column(JSON, nullable=True, comment="质量标准")
    technical_checklist = Column(JSON, nullable=True, comment="技术检查清单")
    content_checklist = Column(JSON, nullable=True, comment="内容检查清单")
    
    # 使用范围
    script_types = Column(JSON, nullable=True, comment="适用剧本类型")
    is_default = Column(Integer, default=0, comment="是否默认模板")
    
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")
    
    def __repr__(self) -> str:
        return f"<AudioTemplate(id={self.id}, name='{self.name}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'required_format': self.required_format,
            'min_bitrate': self.min_bitrate,
            'required_sample_rate': self.required_sample_rate,
            'required_channels': self.required_channels,
            'max_file_size': self.max_file_size,
            'quality_standards': self.quality_standards,
            'technical_checklist': self.technical_checklist,
            'content_checklist': self.content_checklist,
            'script_types': self.script_types,
            'is_default': bool(self.is_default),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }