from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
import os

from app.core.database import get_db
from app.core.auth import get_current_user, require_permission
from app.core.response import ResponseBuilder
from app.core.logger import logger
from app.core.config import settings
from app.models.user import User
from app.schemas.audio import (
    CVRecordingCreate, CVRecordingUpdate, CVRecordingResponse, CVRecordingDetailResponse,
    ReviewRecordCreate, ReviewRecordUpdate, ReviewRecordResponse,
    FeedbackRecordCreate, FeedbackRecordUpdate, FeedbackRecordResponse,
    AudioTemplateCreate, AudioTemplateUpdate, AudioTemplateResponse,
    AudioSearchQuery, ReviewSearchQuery, FeedbackSearchQuery,
    AudioStatistics, AudioBatchOperation, AudioQualityCheck, AudioQualityResult
)
from app.services.audio import AudioService

router = APIRouter(tags=["音频管理"])


# ==================== CV录音管理 ====================

@router.post("/recordings", response_model=CVRecordingResponse, summary="创建CV录音")
async def create_cv_recording(
    title: str = Form(...),
    description: Optional[str] = Form(None),
    script_id: Optional[int] = Form(None),
    chapter_id: Optional[int] = Form(None),
    character_name: Optional[str] = Form(None),
    audio_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audio:create"))
):
    """创建新的CV录音记录并上传音频文件"""
    try:
        # 验证音频文件
        if not audio_file.filename.lower().endswith(('.mp3', '.wav', '.m4a', '.aac', '.flac')):
            raise HTTPException(status_code=400, detail="不支持的音频格式")
        
        # 检查文件大小（例如限制为100MB）
        max_size = 100 * 1024 * 1024  # 100MB
        content = await audio_file.read()
        if len(content) > max_size:
            raise HTTPException(status_code=400, detail="音频文件过大，请上传小于100MB的文件")
        
        # 创建录音数据
        recording_data = CVRecordingCreate(
            title=title,
            description=description,
            script_id=script_id,
            chapter_id=chapter_id,
            character_name=character_name,
            file_name=audio_file.filename,
            file_size=len(content),
            duration=0  # 实际应用中需要解析音频文件获取时长
        )
        
        audio_service = AudioService(db)
        recording = await audio_service.create_cv_recording(recording_data, current_user.id)
        
        # 保存音频文件
        await audio_service.save_audio_file(recording.id, content, audio_file.filename)
        
        logger.info(
            f"CV recording created: {recording.title} by user {current_user.username}",
            extra={"user_id": current_user.id, "recording_id": recording.id}
        )
        
        return ResponseBuilder.created(
            data=recording,
            message="CV录音创建成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create CV recording: {str(e)}")
        raise HTTPException(status_code=500, detail="创建CV录音失败")


@router.get("/recordings/{recording_id}", response_model=CVRecordingDetailResponse, summary="获取CV录音详情")
async def get_cv_recording(
    recording_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audio:read"))
):
    """根据ID获取CV录音详细信息"""
    try:
        audio_service = AudioService(db)
        recording = await audio_service.get_cv_recording_by_id(recording_id)
        
        if not recording:
            raise HTTPException(status_code=404, detail="录音不存在")
        
        return ResponseBuilder.success(
            data=recording,
            message="获取录音信息成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get CV recording: {str(e)}")
        raise HTTPException(status_code=500, detail="获取录音信息失败")


@router.put("/recordings/{recording_id}", response_model=CVRecordingResponse, summary="更新CV录音信息")
async def update_cv_recording(
    recording_id: int,
    recording_data: CVRecordingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audio:update"))
):
    """更新CV录音信息"""
    try:
        audio_service = AudioService(db)
        updated_recording = await audio_service.update_cv_recording(recording_id, recording_data)
        
        logger.info(
            f"CV recording updated: {recording_id} by user {current_user.username}",
            extra={"user_id": current_user.id, "recording_id": recording_id}
        )
        
        return ResponseBuilder.success(
            data=updated_recording,
            message="录音信息更新成功"
        )
    except Exception as e:
        logger.error(f"Failed to update CV recording: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/recordings/{recording_id}", summary="删除CV录音")
async def delete_cv_recording(
    recording_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audio:delete"))
):
    """删除CV录音"""
    try:
        audio_service = AudioService(db)
        await audio_service.delete_cv_recording(recording_id)
        
        logger.info(
            f"CV recording deleted: {recording_id} by user {current_user.username}",
            extra={"user_id": current_user.id, "recording_id": recording_id}
        )
        
        return ResponseBuilder.success(
            message="录音删除成功"
        )
    except Exception as e:
        logger.error(f"Failed to delete CV recording: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/recordings", summary="获取CV录音列表")
async def get_cv_recordings(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    status: Optional[str] = Query(None, description="录音状态"),
    script_id: Optional[int] = Query(None, description="剧本ID"),
    cv_id: Optional[int] = Query(None, description="CV用户ID"),
    created_after: Optional[str] = Query(None, description="创建时间起始"),
    created_before: Optional[str] = Query(None, description="创建时间结束"),
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", description="排序方向"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audio:read"))
):
    """获取CV录音列表（支持搜索和分页）"""
    try:
        # 构建搜索查询
        search_query = AudioSearchQuery(
            keyword=keyword,
            status=status,
            script_id=script_id,
            cv_id=cv_id,
            created_after=created_after,
            created_before=created_before,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        audio_service = AudioService(db)
        recordings, total = await audio_service.get_cv_recordings(page, size, search_query)
        
        return ResponseBuilder.paginated(
            data=recordings,
            total=total,
            page=page,
            size=size,
            message="获取录音列表成功"
        )
    except Exception as e:
        logger.error(f"Failed to get CV recordings: {str(e)}")
        raise HTTPException(status_code=500, detail="获取录音列表失败")


@router.get("/recordings/{recording_id}/download", summary="下载音频文件")
async def download_audio_file(
    recording_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audio:read"))
):
    """下载音频文件"""
    try:
        audio_service = AudioService(db)
        recording = await audio_service.get_cv_recording_by_id(recording_id)
        
        if not recording:
            raise HTTPException(status_code=404, detail="录音不存在")
        
        file_path = await audio_service.get_audio_file_path(recording_id)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="音频文件不存在")
        
        logger.info(
            f"Audio file downloaded: {recording_id} by user {current_user.username}",
            extra={"user_id": current_user.id, "recording_id": recording_id}
        )
        
        return FileResponse(
            path=file_path,
            filename=recording.file_name,
            media_type='application/octet-stream'
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download audio file: {str(e)}")
        raise HTTPException(status_code=500, detail="下载音频文件失败")


# ==================== 审听记录管理 ====================

@router.post("/reviews", response_model=ReviewRecordResponse, summary="创建审听记录")
async def create_review_record(
    review_data: ReviewRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audio:review"))
):
    """创建新的审听记录"""
    try:
        audio_service = AudioService(db)
        review = await audio_service.create_review_record(review_data, current_user.id)
        
        logger.info(
            f"Review record created for recording {review_data.recording_id} by user {current_user.username}",
            extra={"user_id": current_user.id, "review_id": review.id}
        )
        
        return ResponseBuilder.created(
            data=review,
            message="审听记录创建成功"
        )
    except Exception as e:
        logger.error(f"Failed to create review record: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/reviews/{review_id}", response_model=ReviewRecordResponse, summary="获取审听记录")
async def get_review_record(
    review_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audio:read"))
):
    """根据ID获取审听记录"""
    try:
        audio_service = AudioService(db)
        review = await audio_service.get_review_record_by_id(review_id)
        
        if not review:
            raise HTTPException(status_code=404, detail="审听记录不存在")
        
        return ResponseBuilder.success(
            data=review,
            message="获取审听记录成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get review record: {str(e)}")
        raise HTTPException(status_code=500, detail="获取审听记录失败")


@router.put("/reviews/{review_id}", response_model=ReviewRecordResponse, summary="更新审听记录")
async def update_review_record(
    review_id: int,
    review_data: ReviewRecordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audio:review"))
):
    """更新审听记录"""
    try:
        audio_service = AudioService(db)
        updated_review = await audio_service.update_review_record(review_id, review_data)
        
        logger.info(
            f"Review record updated: {review_id} by user {current_user.username}",
            extra={"user_id": current_user.id, "review_id": review_id}
        )
        
        return ResponseBuilder.success(
            data=updated_review,
            message="审听记录更新成功"
        )
    except Exception as e:
        logger.error(f"Failed to update review record: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/recordings/{recording_id}/reviews", summary="获取录音的审听记录")
async def get_recording_reviews(
    recording_id: int,
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audio:read"))
):
    """获取指定录音的所有审听记录"""
    try:
        audio_service = AudioService(db)
        reviews, total = await audio_service.get_recording_reviews(recording_id, page, size)
        
        return ResponseBuilder.paginated(
            data=reviews,
            total=total,
            page=page,
            size=size,
            message="获取审听记录成功"
        )
    except Exception as e:
        logger.error(f"Failed to get recording reviews: {str(e)}")
        raise HTTPException(status_code=500, detail="获取审听记录失败")


# ==================== 反音记录管理 ====================

@router.post("/feedback", response_model=FeedbackRecordResponse, summary="创建反音记录")
async def create_feedback_record(
    feedback_data: FeedbackRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audio:feedback"))
):
    """创建新的反音记录"""
    try:
        audio_service = AudioService(db)
        feedback = await audio_service.create_feedback_record(feedback_data, current_user.id)
        
        logger.info(
            f"Feedback record created for recording {feedback_data.recording_id} by user {current_user.username}",
            extra={"user_id": current_user.id, "feedback_id": feedback.id}
        )
        
        return ResponseBuilder.created(
            data=feedback,
            message="反音记录创建成功"
        )
    except Exception as e:
        logger.error(f"Failed to create feedback record: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/feedback/{feedback_id}", response_model=FeedbackRecordResponse, summary="获取反音记录")
async def get_feedback_record(
    feedback_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audio:read"))
):
    """根据ID获取反音记录"""
    try:
        audio_service = AudioService(db)
        feedback = await audio_service.get_feedback_record_by_id(feedback_id)
        
        if not feedback:
            raise HTTPException(status_code=404, detail="反音记录不存在")
        
        return ResponseBuilder.success(
            data=feedback,
            message="获取反音记录成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get feedback record: {str(e)}")
        raise HTTPException(status_code=500, detail="获取反音记录失败")


@router.put("/feedback/{feedback_id}", response_model=FeedbackRecordResponse, summary="更新反音记录")
async def update_feedback_record(
    feedback_id: int,
    feedback_data: FeedbackRecordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audio:feedback"))
):
    """更新反音记录"""
    try:
        audio_service = AudioService(db)
        updated_feedback = await audio_service.update_feedback_record(feedback_id, feedback_data)
        
        logger.info(
            f"Feedback record updated: {feedback_id} by user {current_user.username}",
            extra={"user_id": current_user.id, "feedback_id": feedback_id}
        )
        
        return ResponseBuilder.success(
            data=updated_feedback,
            message="反音记录更新成功"
        )
    except Exception as e:
        logger.error(f"Failed to update feedback record: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/recordings/{recording_id}/feedback", summary="获取录音的反音记录")
async def get_recording_feedback(
    recording_id: int,
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audio:read"))
):
    """获取指定录音的所有反音记录"""
    try:
        audio_service = AudioService(db)
        feedback_records, total = await audio_service.get_recording_feedback(recording_id, page, size)
        
        return ResponseBuilder.paginated(
            data=feedback_records,
            total=total,
            page=page,
            size=size,
            message="获取反音记录成功"
        )
    except Exception as e:
        logger.error(f"Failed to get recording feedback: {str(e)}")
        raise HTTPException(status_code=500, detail="获取反音记录失败")


# ==================== 音频模板管理 ====================

@router.post("/templates", response_model=AudioTemplateResponse, summary="创建音频模板")
async def create_audio_template(
    template_data: AudioTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audio:template"))
):
    """创建新的音频模板"""
    try:
        audio_service = AudioService(db)
        template = await audio_service.create_audio_template(template_data, current_user.id)
        
        logger.info(
            f"Audio template created: {template.name} by user {current_user.username}",
            extra={"user_id": current_user.id, "template_id": template.id}
        )
        
        return ResponseBuilder.created(
            data=template,
            message="音频模板创建成功"
        )
    except Exception as e:
        logger.error(f"Failed to create audio template: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/templates/{template_id}", response_model=AudioTemplateResponse, summary="获取音频模板")
async def get_audio_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audio:read"))
):
    """根据ID获取音频模板"""
    try:
        audio_service = AudioService(db)
        template = await audio_service.get_audio_template_by_id(template_id)
        
        if not template:
            raise HTTPException(status_code=404, detail="音频模板不存在")
        
        return ResponseBuilder.success(
            data=template,
            message="获取音频模板成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get audio template: {str(e)}")
        raise HTTPException(status_code=500, detail="获取音频模板失败")


@router.put("/templates/{template_id}", response_model=AudioTemplateResponse, summary="更新音频模板")
async def update_audio_template(
    template_id: int,
    template_data: AudioTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audio:template"))
):
    """更新音频模板"""
    try:
        audio_service = AudioService(db)
        updated_template = await audio_service.update_audio_template(template_id, template_data)
        
        logger.info(
            f"Audio template updated: {template_id} by user {current_user.username}",
            extra={"user_id": current_user.id, "template_id": template_id}
        )
        
        return ResponseBuilder.success(
            data=updated_template,
            message="音频模板更新成功"
        )
    except Exception as e:
        logger.error(f"Failed to update audio template: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/templates", summary="获取音频模板列表")
async def get_audio_templates(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audio:read"))
):
    """获取音频模板列表"""
    try:
        audio_service = AudioService(db)
        templates, total = await audio_service.get_audio_templates(page, size, keyword, is_active)
        
        return ResponseBuilder.paginated(
            data=templates,
            total=total,
            page=page,
            size=size,
            message="获取音频模板列表成功"
        )
    except Exception as e:
        logger.error(f"Failed to get audio templates: {str(e)}")
        raise HTTPException(status_code=500, detail="获取音频模板列表失败")


# ==================== 音频质量检查 ====================

@router.post("/recordings/{recording_id}/quality-check", response_model=AudioQualityResult, summary="音频质量检查")
async def check_audio_quality(
    recording_id: int,
    check_params: AudioQualityCheck,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audio:quality_check"))
):
    """对音频进行质量检查"""
    try:
        audio_service = AudioService(db)
        result = await audio_service.check_audio_quality(recording_id, check_params)
        
        logger.info(
            f"Audio quality check performed on recording {recording_id} by user {current_user.username}",
            extra={"user_id": current_user.id, "recording_id": recording_id}
        )
        
        return ResponseBuilder.success(
            data=result,
            message="音频质量检查完成"
        )
    except Exception as e:
        logger.error(f"Failed to check audio quality: {str(e)}")
        raise HTTPException(status_code=500, detail="音频质量检查失败")


# ==================== 批量操作和统计 ====================

@router.post("/batch", summary="批量操作音频")
async def batch_operation_audios(
    operation: AudioBatchOperation,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audio:update"))
):
    """批量操作音频（更新状态、删除等）"""
    try:
        audio_service = AudioService(db)
        result = await audio_service.batch_operation(operation)
        
        logger.info(
            f"Audio batch operation: {operation.operation} on {len(operation.recording_ids)} recordings by user {current_user.username}",
            extra={
                "user_id": current_user.id,
                "operation": operation.operation,
                "recording_count": len(operation.recording_ids)
            }
        )
        
        return ResponseBuilder.success(
            data=result,
            message=f"批量操作完成：成功 {result['success_count']} 个，失败 {result['failed_count']} 个"
        )
    except Exception as e:
        logger.error(f"Failed to batch operation audios: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/statistics/overview", response_model=AudioStatistics, summary="获取音频统计信息")
async def get_audio_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audio:read"))
):
    """获取音频统计信息"""
    try:
        audio_service = AudioService(db)
        statistics = await audio_service.get_audio_statistics()
        
        return ResponseBuilder.success(
            data=statistics,
            message="获取音频统计信息成功"
        )
    except Exception as e:
        logger.error(f"Failed to get audio statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="获取音频统计信息失败")


# ==================== 搜索接口 ====================

@router.get("/search/reviews", summary="搜索审听记录")
async def search_reviews(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    review_type: Optional[str] = Query(None, description="审听类型"),
    result: Optional[str] = Query(None, description="审听结果"),
    reviewer_id: Optional[int] = Query(None, description="审听员ID"),
    created_after: Optional[str] = Query(None, description="创建时间起始"),
    created_before: Optional[str] = Query(None, description="创建时间结束"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audio:read"))
):
    """搜索审听记录"""
    try:
        # 构建搜索查询
        search_query = ReviewSearchQuery(
            keyword=keyword,
            review_type=review_type,
            result=result,
            reviewer_id=reviewer_id,
            created_after=created_after,
            created_before=created_before
        )
        
        audio_service = AudioService(db)
        reviews, total = await audio_service.search_reviews(page, size, search_query)
        
        return ResponseBuilder.paginated(
            data=reviews,
            total=total,
            page=page,
            size=size,
            message="搜索审听记录成功"
        )
    except Exception as e:
        logger.error(f"Failed to search reviews: {str(e)}")
        raise HTTPException(status_code=500, detail="搜索审听记录失败")


@router.get("/search/feedback", summary="搜索反音记录")
async def search_feedback(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    feedback_type: Optional[str] = Query(None, description="反音类型"),
    status: Optional[str] = Query(None, description="反音状态"),
    provider_id: Optional[int] = Query(None, description="反音员ID"),
    created_after: Optional[str] = Query(None, description="创建时间起始"),
    created_before: Optional[str] = Query(None, description="创建时间结束"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("audio:read"))
):
    """搜索反音记录"""
    try:
        # 构建搜索查询
        search_query = FeedbackSearchQuery(
            keyword=keyword,
            feedback_type=feedback_type,
            status=status,
            provider_id=provider_id,
            created_after=created_after,
            created_before=created_before
        )
        
        audio_service = AudioService(db)
        feedback_records, total = await audio_service.search_feedback(page, size, search_query)
        
        return ResponseBuilder.paginated(
            data=feedback_records,
            total=total,
            page=page,
            size=size,
            message="搜索反音记录成功"
        )
    except Exception as e:
        logger.error(f"Failed to search feedback: {str(e)}")
        raise HTTPException(status_code=500, detail="搜索反音记录失败")