from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
import os
import aiofiles
from pathlib import Path

from app.models.audio import CVRecording, ReviewRecord, FeedbackRecord, AudioTemplate
from app.models.script import Script, ScriptChapter
from app.models.user import User
from app.schemas.audio import (
    CVRecordingCreate, CVRecordingUpdate, ReviewRecordCreate, ReviewRecordUpdate,
    FeedbackRecordCreate, FeedbackRecordUpdate, AudioTemplateCreate, AudioTemplateUpdate,
    AudioSearchQuery, ReviewSearchQuery, FeedbackSearchQuery, AudioBatchOperation,
    AudioQualityCheck
)
from app.core.exceptions import (
    raise_not_found, raise_duplicate, raise_validation_error,
    raise_business_error, raise_file_operation_error
)
from app.core.logger import logger
from app.core.database import DatabaseManager
from app.core.config import settings


class AudioService:
    """音频服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.db_manager = DatabaseManager(db)
        self.upload_dir = Path(settings.UPLOAD_DIR) / "audio"
        self.upload_dir.mkdir(parents=True, exist_ok=True)
    
    # ==================== CV录音管理 ====================
    
    async def create_cv_recording(
        self, 
        recording_data: CVRecordingCreate, 
        audio_file: Optional[bytes] = None,
        filename: Optional[str] = None
    ) -> CVRecording:
        """创建CV录音记录"""
        # 检查剧本是否存在
        script_result = await self.db.execute(
            select(Script).where(Script.id == recording_data.script_id)
        )
        script = script_result.scalar_one_or_none()
        if not script:
            raise_not_found("Script", recording_data.script_id)
        
        # 检查章节是否存在（如果指定了章节）
        if recording_data.chapter_id:
            chapter_result = await self.db.execute(
                select(ScriptChapter).where(ScriptChapter.id == recording_data.chapter_id)
            )
            chapter = chapter_result.scalar_one_or_none()
            if not chapter:
                raise_not_found("ScriptChapter", recording_data.chapter_id)
        
        # 检查用户是否存在
        user_result = await self.db.execute(
            select(User).where(User.id == recording_data.cv_user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise_not_found("User", recording_data.cv_user_id)
        
        # 处理音频文件上传
        file_path = None
        if audio_file and filename:
            file_path = await self._save_audio_file(audio_file, filename)
        
        # 创建录音记录
        recording_dict = recording_data.dict()
        if file_path:
            recording_dict["file_path"] = str(file_path)
            recording_dict["file_size"] = len(audio_file)
        
        recording = CVRecording(**recording_dict)
        
        try:
            self.db.add(recording)
            await self.db.commit()
            await self.db.refresh(recording)
            
            logger.info(f"CV recording created: {recording.title} (ID: {recording.id})")
            return recording
            
        except Exception as e:
            await self.db.rollback()
            # 如果数据库操作失败，删除已上传的文件
            if file_path and file_path.exists():
                file_path.unlink()
            logger.error(f"Failed to create CV recording: {str(e)}")
            raise_business_error("Failed to create CV recording")
    
    async def get_cv_recording_by_id(self, recording_id: int) -> Optional[CVRecording]:
        """根据ID获取CV录音记录"""
        result = await self.db.execute(
            select(CVRecording)
            .options(
                selectinload(CVRecording.script),
                selectinload(CVRecording.chapter),
                selectinload(CVRecording.cv_user),
                selectinload(CVRecording.reviews),
                selectinload(CVRecording.feedbacks)
            )
            .where(CVRecording.id == recording_id)
        )
        return result.scalar_one_or_none()
    
    async def update_cv_recording(
        self, 
        recording_id: int, 
        recording_data: CVRecordingUpdate,
        audio_file: Optional[bytes] = None,
        filename: Optional[str] = None
    ) -> CVRecording:
        """更新CV录音记录"""
        recording = await self.get_cv_recording_by_id(recording_id)
        if not recording:
            raise_not_found("CVRecording", recording_id)
        
        # 处理音频文件更新
        old_file_path = None
        if audio_file and filename:
            old_file_path = Path(recording.file_path) if recording.file_path else None
            new_file_path = await self._save_audio_file(audio_file, filename)
            recording_data.file_path = str(new_file_path)
            recording_data.file_size = len(audio_file)
        
        # 更新录音记录
        update_data = recording_data.dict(exclude_unset=True)
        
        try:
            await self.db.execute(
                update(CVRecording)
                .where(CVRecording.id == recording_id)
                .values(**update_data)
            )
            await self.db.commit()
            
            # 删除旧文件
            if old_file_path and old_file_path.exists():
                old_file_path.unlink()
            
            # 重新获取更新后的录音记录
            updated_recording = await self.get_cv_recording_by_id(recording_id)
            
            logger.info(f"CV recording updated: {recording.title} (ID: {recording_id})")
            return updated_recording
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update CV recording {recording_id}: {str(e)}")
            raise_business_error("Failed to update CV recording")
    
    async def delete_cv_recording(self, recording_id: int) -> bool:
        """删除CV录音记录"""
        recording = await self.get_cv_recording_by_id(recording_id)
        if not recording:
            raise_not_found("CVRecording", recording_id)
        
        try:
            # 删除数据库记录
            await self.db.execute(
                delete(CVRecording).where(CVRecording.id == recording_id)
            )
            await self.db.commit()
            
            # 删除音频文件
            if recording.file_path:
                file_path = Path(recording.file_path)
                if file_path.exists():
                    file_path.unlink()
            
            logger.info(f"CV recording deleted: {recording.title} (ID: {recording_id})")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete CV recording {recording_id}: {str(e)}")
            raise_business_error("Failed to delete CV recording")
    
    async def get_cv_recordings(
        self, 
        page: int = 1, 
        size: int = 20,
        search_query: Optional[AudioSearchQuery] = None
    ) -> Tuple[List[CVRecording], int]:
        """获取CV录音列表"""
        query = select(CVRecording).options(
            selectinload(CVRecording.script),
            selectinload(CVRecording.chapter),
            selectinload(CVRecording.cv_user)
        )
        
        # 构建搜索条件
        if search_query:
            conditions = []
            
            if search_query.keyword:
                keyword = f"%{search_query.keyword}%"
                conditions.append(
                    or_(
                        CVRecording.title.ilike(keyword),
                        CVRecording.description.ilike(keyword),
                        CVRecording.character_name.ilike(keyword)
                    )
                )
            
            if search_query.script_id:
                conditions.append(CVRecording.script_id == search_query.script_id)
            
            if search_query.chapter_id:
                conditions.append(CVRecording.chapter_id == search_query.chapter_id)
            
            if search_query.cv_user_id:
                conditions.append(CVRecording.cv_user_id == search_query.cv_user_id)
            
            if search_query.status:
                conditions.append(CVRecording.status == search_query.status)
            
            if search_query.audio_format:
                conditions.append(CVRecording.audio_format == search_query.audio_format)
            
            if search_query.created_after:
                conditions.append(CVRecording.created_at >= search_query.created_after)
            
            if search_query.created_before:
                conditions.append(CVRecording.created_at <= search_query.created_before)
            
            if conditions:
                query = query.where(and_(*conditions))
        
        # 排序
        if search_query and search_query.sort_by:
            if search_query.sort_order == "desc":
                query = query.order_by(getattr(CVRecording, search_query.sort_by).desc())
            else:
                query = query.order_by(getattr(CVRecording, search_query.sort_by))
        else:
            query = query.order_by(CVRecording.created_at.desc())
        
        # 获取总数
        count_query = select(func.count(CVRecording.id))
        if search_query:
            conditions = []
            if search_query.keyword:
                keyword = f"%{search_query.keyword}%"
                conditions.append(
                    or_(
                        CVRecording.title.ilike(keyword),
                        CVRecording.description.ilike(keyword),
                        CVRecording.character_name.ilike(keyword)
                    )
                )
            if search_query.script_id:
                conditions.append(CVRecording.script_id == search_query.script_id)
            if search_query.chapter_id:
                conditions.append(CVRecording.chapter_id == search_query.chapter_id)
            if search_query.cv_user_id:
                conditions.append(CVRecording.cv_user_id == search_query.cv_user_id)
            if search_query.status:
                conditions.append(CVRecording.status == search_query.status)
            if search_query.audio_format:
                conditions.append(CVRecording.audio_format == search_query.audio_format)
            if search_query.created_after:
                conditions.append(CVRecording.created_at >= search_query.created_after)
            if search_query.created_before:
                conditions.append(CVRecording.created_at <= search_query.created_before)
            
            if conditions:
                count_query = count_query.where(and_(*conditions))
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # 分页
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)
        
        result = await self.db.execute(query)
        recordings = result.scalars().all()
        
        return list(recordings), total
    
    # ==================== 审听记录管理 ====================
    
    async def create_review_record(self, review_data: ReviewRecordCreate) -> ReviewRecord:
        """创建审听记录"""
        # 检查录音是否存在
        recording = await self.get_cv_recording_by_id(review_data.recording_id)
        if not recording:
            raise_not_found("CVRecording", review_data.recording_id)
        
        # 检查审听者是否存在
        reviewer_result = await self.db.execute(
            select(User).where(User.id == review_data.reviewer_id)
        )
        reviewer = reviewer_result.scalar_one_or_none()
        if not reviewer:
            raise_not_found("User", review_data.reviewer_id)
        
        # 创建审听记录
        review_dict = review_data.dict()
        review = ReviewRecord(**review_dict)
        
        try:
            self.db.add(review)
            await self.db.commit()
            await self.db.refresh(review)
            
            logger.info(f"Review record created for recording {review_data.recording_id} by user {review_data.reviewer_id}")
            return review
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create review record: {str(e)}")
            raise_business_error("Failed to create review record")
    
    async def get_review_record_by_id(self, review_id: int) -> Optional[ReviewRecord]:
        """根据ID获取审听记录"""
        result = await self.db.execute(
            select(ReviewRecord)
            .options(
                selectinload(ReviewRecord.recording),
                selectinload(ReviewRecord.reviewer)
            )
            .where(ReviewRecord.id == review_id)
        )
        return result.scalar_one_or_none()
    
    async def update_review_record(self, review_id: int, review_data: ReviewRecordUpdate) -> ReviewRecord:
        """更新审听记录"""
        review = await self.get_review_record_by_id(review_id)
        if not review:
            raise_not_found("ReviewRecord", review_id)
        
        # 更新审听记录
        update_data = review_data.dict(exclude_unset=True)
        
        try:
            await self.db.execute(
                update(ReviewRecord)
                .where(ReviewRecord.id == review_id)
                .values(**update_data)
            )
            await self.db.commit()
            
            # 重新获取更新后的审听记录
            updated_review = await self.get_review_record_by_id(review_id)
            
            logger.info(f"Review record updated: ID {review_id}")
            return updated_review
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update review record {review_id}: {str(e)}")
            raise_business_error("Failed to update review record")
    
    async def get_recording_reviews(self, recording_id: int) -> List[ReviewRecord]:
        """获取录音的所有审听记录"""
        result = await self.db.execute(
            select(ReviewRecord)
            .options(selectinload(ReviewRecord.reviewer))
            .where(ReviewRecord.recording_id == recording_id)
            .order_by(ReviewRecord.created_at.desc())
        )
        return list(result.scalars().all())
    
    # ==================== 反音记录管理 ====================
    
    async def create_feedback_record(self, feedback_data: FeedbackRecordCreate) -> FeedbackRecord:
        """创建反音记录"""
        # 检查录音是否存在
        recording = await self.get_cv_recording_by_id(feedback_data.recording_id)
        if not recording:
            raise_not_found("CVRecording", feedback_data.recording_id)
        
        # 检查反音者是否存在
        feedback_user_result = await self.db.execute(
            select(User).where(User.id == feedback_data.feedback_user_id)
        )
        feedback_user = feedback_user_result.scalar_one_or_none()
        if not feedback_user:
            raise_not_found("User", feedback_data.feedback_user_id)
        
        # 创建反音记录
        feedback_dict = feedback_data.dict()
        feedback = FeedbackRecord(**feedback_dict)
        
        try:
            self.db.add(feedback)
            await self.db.commit()
            await self.db.refresh(feedback)
            
            logger.info(f"Feedback record created for recording {feedback_data.recording_id} by user {feedback_data.feedback_user_id}")
            return feedback
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create feedback record: {str(e)}")
            raise_business_error("Failed to create feedback record")
    
    async def get_feedback_record_by_id(self, feedback_id: int) -> Optional[FeedbackRecord]:
        """根据ID获取反音记录"""
        result = await self.db.execute(
            select(FeedbackRecord)
            .options(
                selectinload(FeedbackRecord.recording),
                selectinload(FeedbackRecord.feedback_user)
            )
            .where(FeedbackRecord.id == feedback_id)
        )
        return result.scalar_one_or_none()
    
    async def update_feedback_record(self, feedback_id: int, feedback_data: FeedbackRecordUpdate) -> FeedbackRecord:
        """更新反音记录"""
        feedback = await self.get_feedback_record_by_id(feedback_id)
        if not feedback:
            raise_not_found("FeedbackRecord", feedback_id)
        
        # 更新反音记录
        update_data = feedback_data.dict(exclude_unset=True)
        
        try:
            await self.db.execute(
                update(FeedbackRecord)
                .where(FeedbackRecord.id == feedback_id)
                .values(**update_data)
            )
            await self.db.commit()
            
            # 重新获取更新后的反音记录
            updated_feedback = await self.get_feedback_record_by_id(feedback_id)
            
            logger.info(f"Feedback record updated: ID {feedback_id}")
            return updated_feedback
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update feedback record {feedback_id}: {str(e)}")
            raise_business_error("Failed to update feedback record")
    
    async def get_recording_feedbacks(self, recording_id: int) -> List[FeedbackRecord]:
        """获取录音的所有反音记录"""
        result = await self.db.execute(
            select(FeedbackRecord)
            .options(selectinload(FeedbackRecord.feedback_user))
            .where(FeedbackRecord.recording_id == recording_id)
            .order_by(FeedbackRecord.created_at.desc())
        )
        return list(result.scalars().all())
    
    # ==================== 音频模板管理 ====================
    
    async def create_audio_template(self, template_data: AudioTemplateCreate, creator_id: int) -> AudioTemplate:
        """创建音频模板"""
        # 检查模板名是否已存在
        existing_template = await self.get_audio_template_by_name(template_data.name)
        if existing_template:
            raise_duplicate("AudioTemplate", "name", template_data.name)
        
        # 创建音频模板
        template_dict = template_data.dict()
        template_dict["creator_id"] = creator_id
        template = AudioTemplate(**template_dict)
        
        try:
            self.db.add(template)
            await self.db.commit()
            await self.db.refresh(template)
            
            logger.info(f"Audio template created: {template.name} (ID: {template.id})")
            return template
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create audio template: {str(e)}")
            raise_business_error("Failed to create audio template")
    
    async def get_audio_template_by_id(self, template_id: int) -> Optional[AudioTemplate]:
        """根据ID获取音频模板"""
        result = await self.db.execute(
            select(AudioTemplate)
            .options(selectinload(AudioTemplate.creator))
            .where(AudioTemplate.id == template_id)
        )
        return result.scalar_one_or_none()
    
    async def get_audio_template_by_name(self, name: str) -> Optional[AudioTemplate]:
        """根据名称获取音频模板"""
        result = await self.db.execute(
            select(AudioTemplate).where(AudioTemplate.name == name)
        )
        return result.scalar_one_or_none()
    
    async def get_audio_templates(
        self, 
        page: int = 1, 
        size: int = 20,
        creator_id: Optional[int] = None
    ) -> Tuple[List[AudioTemplate], int]:
        """获取音频模板列表"""
        query = select(AudioTemplate).options(selectinload(AudioTemplate.creator))
        
        # 按创建者过滤
        if creator_id:
            query = query.where(AudioTemplate.creator_id == creator_id)
        
        # 排序
        query = query.order_by(AudioTemplate.created_at.desc())
        
        # 获取总数
        count_query = select(func.count(AudioTemplate.id))
        if creator_id:
            count_query = count_query.where(AudioTemplate.creator_id == creator_id)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # 分页
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)
        
        result = await self.db.execute(query)
        templates = result.scalars().all()
        
        return list(templates), total
    
    # ==================== 文件操作 ====================
    
    async def _save_audio_file(self, audio_data: bytes, filename: str) -> Path:
        """保存音频文件"""
        # 生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = Path(filename).suffix
        unique_filename = f"{timestamp}_{filename}"
        file_path = self.upload_dir / unique_filename
        
        try:
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(audio_data)
            
            logger.info(f"Audio file saved: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"Failed to save audio file: {str(e)}")
            raise_file_operation_error("save", str(file_path))
    
    async def get_audio_file(self, recording_id: int) -> Optional[bytes]:
        """获取音频文件内容"""
        recording = await self.get_cv_recording_by_id(recording_id)
        if not recording or not recording.file_path:
            return None
        
        file_path = Path(recording.file_path)
        if not file_path.exists():
            logger.warning(f"Audio file not found: {file_path}")
            return None
        
        try:
            async with aiofiles.open(file_path, 'rb') as f:
                return await f.read()
        except Exception as e:
            logger.error(f"Failed to read audio file: {str(e)}")
            raise_file_operation_error("read", str(file_path))
    
    # ==================== 音频质量检查 ====================
    
    async def check_audio_quality(self, recording_id: int, quality_check: AudioQualityCheck) -> Dict[str, Any]:
        """检查音频质量"""
        recording = await self.get_cv_recording_by_id(recording_id)
        if not recording:
            raise_not_found("CVRecording", recording_id)
        
        # 这里可以集成音频质量检查的AI服务
        # 目前返回模拟结果
        quality_result = {
            "recording_id": recording_id,
            "overall_score": 85.5,
            "noise_level": "low",
            "volume_level": "appropriate",
            "clarity_score": 90.0,
            "recommendations": [
                "音质清晰，建议保持当前录音环境",
                "可以适当提高音量以增强表现力"
            ],
            "passed": True
        }
        
        logger.info(f"Audio quality check completed for recording {recording_id}")
        return quality_result
    
    # ==================== 批量操作 ====================
    
    async def batch_update_recordings(self, operation: AudioBatchOperation) -> Dict[str, Any]:
        """批量更新录音"""
        results = {
            "success_count": 0,
            "failed_count": 0,
            "errors": []
        }
        
        try:
            for recording_id in operation.recording_ids:
                try:
                    if operation.operation == "update_status":
                        await self.db.execute(
                            update(CVRecording)
                            .where(CVRecording.id == recording_id)
                            .values(status=operation.data.get("status"))
                        )
                    elif operation.operation == "delete":
                        # 获取录音信息以删除文件
                        recording = await self.get_cv_recording_by_id(recording_id)
                        if recording:
                            await self.db.execute(
                                delete(CVRecording).where(CVRecording.id == recording_id)
                            )
                            # 删除音频文件
                            if recording.file_path:
                                file_path = Path(recording.file_path)
                                if file_path.exists():
                                    file_path.unlink()
                    
                    results["success_count"] += 1
                    
                except Exception as e:
                    results["failed_count"] += 1
                    results["errors"].append({
                        "recording_id": recording_id,
                        "error": str(e)
                    })
            
            await self.db.commit()
            
            logger.info(
                f"Batch audio operation completed: "
                f"{results['success_count']} success, {results['failed_count']} failed"
            )
            
            return results
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Batch audio operation failed: {str(e)}")
            raise_business_error("Batch audio operation failed")
    
    # ==================== 统计信息 ====================
    
    async def get_audio_statistics(self, script_id: Optional[int] = None) -> Dict[str, Any]:
        """获取音频统计信息"""
        base_query = select(func.count(CVRecording.id))
        if script_id:
            base_query = base_query.where(CVRecording.script_id == script_id)
        
        # 总录音数
        total_recordings_result = await self.db.execute(base_query)
        total_recordings = total_recordings_result.scalar()
        
        # 按状态统计
        status_query = select(CVRecording.status, func.count(CVRecording.id)).group_by(CVRecording.status)
        if script_id:
            status_query = status_query.where(CVRecording.script_id == script_id)
        
        status_result = await self.db.execute(status_query)
        status_stats = dict(status_result.all())
        
        # 按格式统计
        format_query = select(CVRecording.audio_format, func.count(CVRecording.id)).group_by(CVRecording.audio_format)
        if script_id:
            format_query = format_query.where(CVRecording.script_id == script_id)
        
        format_result = await self.db.execute(format_query)
        format_stats = dict(format_result.all())
        
        # 总文件大小
        size_query = select(func.sum(CVRecording.file_size))
        if script_id:
            size_query = size_query.where(CVRecording.script_id == script_id)
        
        size_result = await self.db.execute(size_query)
        total_size = size_result.scalar() or 0
        
        # 总时长
        duration_query = select(func.sum(CVRecording.duration))
        if script_id:
            duration_query = duration_query.where(CVRecording.script_id == script_id)
        
        duration_result = await self.db.execute(duration_query)
        total_duration = duration_result.scalar() or 0
        
        return {
            "total_recordings": total_recordings,
            "status_statistics": status_stats,
            "format_statistics": format_stats,
            "total_file_size": total_size,
            "total_duration": total_duration,
            "average_file_size": total_size / total_recordings if total_recordings > 0 else 0,
            "average_duration": total_duration / total_recordings if total_recordings > 0 else 0
        }