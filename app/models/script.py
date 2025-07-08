from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import Dict, List, Any, Optional
from enum import Enum

from app.core.database import Base


class ScriptStatus(Enum):
    """剧本状态枚举"""
    PENDING = 0  # 待分配
    IN_PROGRESS = 1  # 制作中
    COMPLETED = 2  # 已完成
    ARCHIVED = 3  # 已归档


class ScriptType(Enum):
    """剧本类型枚举"""
    RADIO_DRAMA = "radio_drama"  # 广播剧
    AUDIOBOOK = "audiobook"  # 有声书
    PODCAST = "podcast"  # 播客
    COMMERCIAL = "commercial"  # 商业配音
    OTHER = "other"  # 其他


class DramaSociety(Base):
    """剧社模型"""
    __tablename__ = "drama_societies"
    __table_args__ = {'comment': '剧社信息表'}

    id = Column(Integer, primary_key=True, index=True, comment="剧社ID")
    name = Column(String(100), nullable=False, comment="剧社名称")
    description = Column(Text, nullable=True, comment="剧社描述")
    logo_url = Column(String(500), nullable=True, comment="剧社Logo URL")
    contact_info = Column(JSON, nullable=True, comment="联系信息")
    settings = Column(JSON, nullable=True, comment="剧社配置")
    status = Column(Integer, default=1, comment="状态：1-活跃，0-停用")
    
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关系映射
    scripts = relationship("Script", back_populates="society")
    
    def __repr__(self) -> str:
        return f"<DramaSociety(id={self.id}, name='{self.name}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'logo_url': self.logo_url,
            'contact_info': self.contact_info,
            'settings': self.settings,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class Script(Base):
    """剧本模型"""
    __tablename__ = "scripts"
    __table_args__ = {'comment': '剧本信息表'}

    id = Column(Integer, primary_key=True, index=True, comment="剧本ID")
    title = Column(String(200), nullable=False, comment="剧本标题")
    author = Column(String(100), nullable=True, comment="原作者")
    adapter = Column(String(100), nullable=True, comment="改编者")
    description = Column(Text, nullable=True, comment="剧本描述")
    type = Column(String(50), default=ScriptType.RADIO_DRAMA.value, comment="剧本类型")
    genre = Column(String(50), nullable=True, comment="题材类型")
    tags = Column(JSON, nullable=True, comment="标签")
    
    # 文件信息
    file_url = Column(String(500), nullable=True, comment="剧本文件URL")
    file_type = Column(String(20), nullable=True, comment="文件类型")
    file_size = Column(Integer, nullable=True, comment="文件大小（字节）")
    
    # 状态和进度
    status = Column(Integer, default=ScriptStatus.PENDING.value, comment="剧本状态")
    progress = Column(Integer, default=0, comment="制作进度（百分比）")
    priority = Column(Integer, default=0, comment="优先级：0-普通，1-高，2-紧急")
    
    # 时间信息
    deadline = Column(DateTime, nullable=True, comment="截止时间")
    estimated_duration = Column(Integer, nullable=True, comment="预估总时长（分钟）")
    actual_duration = Column(Integer, nullable=True, comment="实际总时长（分钟）")
    
    # 关联信息
    society_id = Column(Integer, ForeignKey('drama_societies.id'), nullable=True, comment="所属剧社ID")
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False, comment="创建者ID")
    
    # 扩展信息
    extra_metadata = Column(JSON, nullable=True, comment="扩展元数据")
    notes = Column(Text, nullable=True, comment="备注信息")
    
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关系映射
    society = relationship("DramaSociety", back_populates="scripts")
    creator = relationship("User", back_populates="created_scripts")
    chapters = relationship("ScriptChapter", back_populates="script", cascade="all, delete-orphan")
    assignments = relationship("ScriptAssignment", back_populates="script", cascade="all, delete-orphan")
    cv_recordings = relationship("CVRecording", back_populates="script")
    
    def __repr__(self) -> str:
        return f"<Script(id={self.id}, title='{self.title}', status={self.status})>"
    
    @property
    def status_name(self) -> str:
        """获取状态名称"""
        status_map = {
            ScriptStatus.PENDING.value: "待分配",
            ScriptStatus.IN_PROGRESS.value: "制作中",
            ScriptStatus.COMPLETED.value: "已完成",
            ScriptStatus.ARCHIVED.value: "已归档"
        }
        return status_map.get(self.status, "未知")
    
    @property
    def type_name(self) -> str:
        """获取类型名称"""
        type_map = {
            ScriptType.RADIO_DRAMA.value: "广播剧",
            ScriptType.AUDIOBOOK.value: "有声书",
            ScriptType.PODCAST.value: "播客",
            ScriptType.COMMERCIAL.value: "商业配音",
            ScriptType.OTHER.value: "其他"
        }
        return type_map.get(self.type, "未知")
    
    @property
    def is_overdue(self) -> bool:
        """检查是否已过期"""
        if not self.deadline:
            return False
        from datetime import datetime
        return datetime.utcnow() > self.deadline
    
    def get_team_members(self) -> List[Dict[str, Any]]:
        """获取团队成员信息"""
        members = []
        for assignment in self.assignments:
            if assignment.user:
                members.append({
                    'user_id': assignment.user_id,
                    'username': assignment.user.username,
                    'real_name': assignment.user.real_name,
                    'role_type': assignment.role_type,
                    'character_name': assignment.character_name,
                    'chapter_ids': assignment.chapter_ids
                })
        return members
    
    def to_dict(self, include_details: bool = False) -> Dict[str, Any]:
        """转换为字典格式"""
        data = {
            'id': self.id,
            'title': self.title,
            'author': self.author,
            'adapter': self.adapter,
            'description': self.description,
            'type': self.type,
            'type_name': self.type_name,
            'genre': self.genre,
            'tags': self.tags,
            'file_url': self.file_url,
            'file_type': self.file_type,
            'file_size': self.file_size,
            'status': self.status,
            'status_name': self.status_name,
            'progress': self.progress,
            'priority': self.priority,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'estimated_duration': self.estimated_duration,
            'actual_duration': self.actual_duration,
            'society_id': self.society_id,
            'created_by': self.created_by,
            'notes': self.notes,
            'is_overdue': self.is_overdue,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
        
        if include_details:
            data.update({
                'extra_metadata': self.extra_metadata,
                'society': self.society.to_dict() if self.society else None,
                'creator': self.creator.to_dict() if self.creator else None,
                'chapters_count': len(self.chapters),
                'team_members': self.get_team_members(),
            })
        
        return data


class ScriptChapter(Base):
    """剧本章节模型"""
    __tablename__ = "script_chapters"
    __table_args__ = {'comment': '剧本章节表'}

    id = Column(Integer, primary_key=True, index=True, comment="章节ID")
    script_id = Column(Integer, ForeignKey('scripts.id', ondelete='CASCADE'), nullable=False, comment="剧本ID")
    chapter_number = Column(Integer, nullable=False, comment="章节序号")
    title = Column(String(200), nullable=True, comment="章节标题")
    content = Column(Text, nullable=True, comment="章节内容")
    character_list = Column(JSON, nullable=True, comment="角色列表")
    duration_estimate = Column(Integer, nullable=True, comment="预估时长（秒）")
    notes = Column(Text, nullable=True, comment="章节备注")
    
    created_at = Column(DateTime, default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), comment="更新时间")

    # 关系映射
    script = relationship("Script", back_populates="chapters")
    cv_recordings = relationship("CVRecording", back_populates="chapter")
    
    def __repr__(self) -> str:
        return f"<ScriptChapter(id={self.id}, script_id={self.script_id}, number={self.chapter_number})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'script_id': self.script_id,
            'chapter_number': self.chapter_number,
            'title': self.title,
            'content': self.content,
            'character_list': self.character_list,
            'duration_estimate': self.duration_estimate,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ScriptAssignment(Base):
    """剧本人员分配模型"""
    __tablename__ = "script_assignments"
    __table_args__ = {'comment': '剧本人员分配表'}

    id = Column(Integer, primary_key=True, index=True, comment="分配ID")
    script_id = Column(Integer, ForeignKey('scripts.id', ondelete='CASCADE'), nullable=False, comment="剧本ID")
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, comment="用户ID")
    role_type = Column(String(50), nullable=False, comment="角色类型")
    character_name = Column(String(100), nullable=True, comment="CV角色名称")
    chapter_ids = Column(ARRAY(Integer), nullable=True, comment="负责的章节ID数组")
    assigned_by = Column(Integer, ForeignKey('users.id'), nullable=False, comment="分配者ID")
    status = Column(Integer, default=1, comment="分配状态：1-有效，0-无效")
    notes = Column(Text, nullable=True, comment="分配备注")
    
    assigned_at = Column(DateTime, default=func.now(), comment="分配时间")
    created_at = Column(DateTime, default=func.now(), comment="创建时间")

    # 关系映射
    script = relationship("Script", back_populates="assignments")
    user = relationship("User", back_populates="script_assignments", foreign_keys=[user_id])
    assigner = relationship("User", foreign_keys=[assigned_by])
    
    def __repr__(self) -> str:
        return f"<ScriptAssignment(script_id={self.script_id}, user_id={self.user_id}, role='{self.role_type}')>"
    
    @property
    def role_type_name(self) -> str:
        """获取角色类型名称"""
        role_map = {
            'project_leader': '项目组长',
            'director': '导演',
            'scriptwriter': '编剧',
            'cv': 'CV配音演员',
            'post_production': '后期制作',
            'first_reviewer': '一审',
            'second_reviewer': '二审'
        }
        return role_map.get(self.role_type, self.role_type)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'script_id': self.script_id,
            'user_id': self.user_id,
            'role_type': self.role_type,
            'role_type_name': self.role_type_name,
            'character_name': self.character_name,
            'chapter_ids': self.chapter_ids,
            'assigned_by': self.assigned_by,
            'status': self.status,
            'notes': self.notes,
            'assigned_at': self.assigned_at.isoformat() if self.assigned_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'user': self.user.to_dict() if self.user else None,
            'assigner': self.assigner.to_dict() if self.assigner else None,
        }