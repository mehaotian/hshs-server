from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, require_permission
from app.core.response import ResponseBuilder
from app.core.logger import logger
from app.models.user import User
from app.schemas.script import (
    DramaSocietyCreate, DramaSocietyUpdate, DramaSocietyResponse,
    ScriptCreate, ScriptUpdate, ScriptResponse, ScriptDetailResponse,
    ScriptChapterCreate, ScriptChapterUpdate, ScriptChapterResponse,
    ScriptAssignmentCreate, ScriptAssignmentUpdate, ScriptAssignmentResponse,
    ScriptSearchQuery, AssignmentSearchQuery, ScriptStatistics,
    ScriptBatchOperation, ScriptImportExport
)
from app.services.script import ScriptService

router = APIRouter()


# ==================== 剧社管理 ====================

@router.post("/societies", response_model=DramaSocietyResponse, summary="创建剧社")
async def create_drama_society(
    society_data: DramaSocietyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:create"))
):
    """创建新剧社"""
    try:
        script_service = ScriptService(db)
        society = await script_service.create_drama_society(society_data)
        
        logger.info(
            f"Drama society created: {society.name} by user {current_user.username}",
            extra={"user_id": current_user.id, "society_id": society.id}
        )
        
        return ResponseBuilder.created(
            data=society,
            message="剧社创建成功"
        )
    except Exception as e:
        logger.error(f"Failed to create drama society: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/societies/{society_id}", response_model=DramaSocietyResponse, summary="获取剧社信息")
async def get_drama_society(
    society_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:read"))
):
    """根据ID获取剧社信息"""
    try:
        script_service = ScriptService(db)
        society = await script_service.get_drama_society_by_id(society_id)
        
        if not society:
            raise HTTPException(status_code=404, detail="剧社不存在")
        
        return ResponseBuilder.success(
            data=society,
            message="获取剧社信息成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get drama society: {str(e)}")
        raise HTTPException(status_code=500, detail="获取剧社信息失败")


@router.put("/societies/{society_id}", response_model=DramaSocietyResponse, summary="更新剧社信息")
async def update_drama_society(
    society_id: int,
    society_data: DramaSocietyUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:update"))
):
    """更新剧社信息"""
    try:
        script_service = ScriptService(db)
        updated_society = await script_service.update_drama_society(society_id, society_data)
        
        logger.info(
            f"Drama society updated: {society_id} by user {current_user.username}",
            extra={"user_id": current_user.id, "society_id": society_id}
        )
        
        return ResponseBuilder.success(
            data=updated_society,
            message="剧社信息更新成功"
        )
    except Exception as e:
        logger.error(f"Failed to update drama society: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/societies/{society_id}", summary="删除剧社")
async def delete_drama_society(
    society_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:delete"))
):
    """删除剧社"""
    try:
        script_service = ScriptService(db)
        await script_service.delete_drama_society(society_id)
        
        logger.info(
            f"Drama society deleted: {society_id} by user {current_user.username}",
            extra={"user_id": current_user.id, "society_id": society_id}
        )
        
        return ResponseBuilder.success(
            message="剧社删除成功"
        )
    except Exception as e:
        logger.error(f"Failed to delete drama society: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/societies", summary="获取剧社列表")
async def get_drama_societies(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:read"))
):
    """获取剧社列表（支持搜索和分页）"""
    try:
        script_service = ScriptService(db)
        societies, total = await script_service.get_drama_societies(page, size, keyword, is_active)
        
        return ResponseBuilder.paginated(
            data=societies,
            total=total,
            page=page,
            size=size,
            message="获取剧社列表成功"
        )
    except Exception as e:
        logger.error(f"Failed to get drama societies: {str(e)}")
        raise HTTPException(status_code=500, detail="获取剧社列表失败")


# ==================== 剧本管理 ====================

@router.post("/", response_model=ScriptResponse, summary="创建剧本")
async def create_script(
    script_data: ScriptCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:create"))
):
    """创建新剧本"""
    try:
        script_service = ScriptService(db)
        script = await script_service.create_script(script_data, current_user.id)
        
        logger.info(
            f"Script created: {script.title} by user {current_user.username}",
            extra={"user_id": current_user.id, "script_id": script.id}
        )
        
        return ResponseBuilder.created(
            data=script,
            message="剧本创建成功"
        )
    except Exception as e:
        logger.error(f"Failed to create script: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{script_id}", response_model=ScriptDetailResponse, summary="获取剧本详情")
async def get_script(
    script_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:read"))
):
    """根据ID获取剧本详细信息"""
    try:
        script_service = ScriptService(db)
        script = await script_service.get_script_by_id(script_id)
        
        if not script:
            raise HTTPException(status_code=404, detail="剧本不存在")
        
        return ResponseBuilder.success(
            data=script,
            message="获取剧本信息成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get script: {str(e)}")
        raise HTTPException(status_code=500, detail="获取剧本信息失败")


@router.put("/{script_id}", response_model=ScriptResponse, summary="更新剧本信息")
async def update_script(
    script_id: int,
    script_data: ScriptUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:update"))
):
    """更新剧本信息"""
    try:
        script_service = ScriptService(db)
        updated_script = await script_service.update_script(script_id, script_data)
        
        logger.info(
            f"Script updated: {script_id} by user {current_user.username}",
            extra={"user_id": current_user.id, "script_id": script_id}
        )
        
        return ResponseBuilder.success(
            data=updated_script,
            message="剧本信息更新成功"
        )
    except Exception as e:
        logger.error(f"Failed to update script: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{script_id}", summary="删除剧本")
async def delete_script(
    script_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:delete"))
):
    """删除剧本"""
    try:
        script_service = ScriptService(db)
        await script_service.delete_script(script_id)
        
        logger.info(
            f"Script deleted: {script_id} by user {current_user.username}",
            extra={"user_id": current_user.id, "script_id": script_id}
        )
        
        return ResponseBuilder.success(
            message="剧本删除成功"
        )
    except Exception as e:
        logger.error(f"Failed to delete script: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/", summary="获取剧本列表")
async def get_scripts(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    status: Optional[str] = Query(None, description="剧本状态"),
    script_type: Optional[str] = Query(None, description="剧本类型"),
    society_id: Optional[int] = Query(None, description="剧社ID"),
    author_id: Optional[int] = Query(None, description="作者ID"),
    created_after: Optional[str] = Query(None, description="创建时间起始"),
    created_before: Optional[str] = Query(None, description="创建时间结束"),
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", description="排序方向"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:read"))
):
    """获取剧本列表（支持搜索和分页）"""
    try:
        # 构建搜索查询
        search_query = ScriptSearchQuery(
            keyword=keyword,
            status=status,
            script_type=script_type,
            society_id=society_id,
            author_id=author_id,
            created_after=created_after,
            created_before=created_before,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        script_service = ScriptService(db)
        scripts, total = await script_service.get_scripts(page, size, search_query)
        
        return ResponseBuilder.paginated(
            data=scripts,
            total=total,
            page=page,
            size=size,
            message="获取剧本列表成功"
        )
    except Exception as e:
        logger.error(f"Failed to get scripts: {str(e)}")
        raise HTTPException(status_code=500, detail="获取剧本列表失败")


# ==================== 章节管理 ====================

@router.post("/{script_id}/chapters", response_model=ScriptChapterResponse, summary="创建章节")
async def create_script_chapter(
    script_id: int,
    chapter_data: ScriptChapterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:create"))
):
    """为剧本创建新章节"""
    try:
        script_service = ScriptService(db)
        chapter = await script_service.create_script_chapter(script_id, chapter_data)
        
        logger.info(
            f"Script chapter created: {chapter.title} for script {script_id} by user {current_user.username}",
            extra={"user_id": current_user.id, "script_id": script_id, "chapter_id": chapter.id}
        )
        
        return ResponseBuilder.created(
            data=chapter,
            message="章节创建成功"
        )
    except Exception as e:
        logger.error(f"Failed to create script chapter: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{script_id}/chapters/{chapter_id}", response_model=ScriptChapterResponse, summary="获取章节信息")
async def get_script_chapter(
    script_id: int,
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:read"))
):
    """获取章节详细信息"""
    try:
        script_service = ScriptService(db)
        chapter = await script_service.get_script_chapter_by_id(chapter_id)
        
        if not chapter or chapter.script_id != script_id:
            raise HTTPException(status_code=404, detail="章节不存在")
        
        return ResponseBuilder.success(
            data=chapter,
            message="获取章节信息成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get script chapter: {str(e)}")
        raise HTTPException(status_code=500, detail="获取章节信息失败")


@router.put("/{script_id}/chapters/{chapter_id}", response_model=ScriptChapterResponse, summary="更新章节信息")
async def update_script_chapter(
    script_id: int,
    chapter_id: int,
    chapter_data: ScriptChapterUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:update"))
):
    """更新章节信息"""
    try:
        script_service = ScriptService(db)
        updated_chapter = await script_service.update_script_chapter(chapter_id, chapter_data)
        
        logger.info(
            f"Script chapter updated: {chapter_id} by user {current_user.username}",
            extra={"user_id": current_user.id, "script_id": script_id, "chapter_id": chapter_id}
        )
        
        return ResponseBuilder.success(
            data=updated_chapter,
            message="章节信息更新成功"
        )
    except Exception as e:
        logger.error(f"Failed to update script chapter: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{script_id}/chapters/{chapter_id}", summary="删除章节")
async def delete_script_chapter(
    script_id: int,
    chapter_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:delete"))
):
    """删除章节"""
    try:
        script_service = ScriptService(db)
        await script_service.delete_script_chapter(chapter_id)
        
        logger.info(
            f"Script chapter deleted: {chapter_id} by user {current_user.username}",
            extra={"user_id": current_user.id, "script_id": script_id, "chapter_id": chapter_id}
        )
        
        return ResponseBuilder.success(
            message="章节删除成功"
        )
    except Exception as e:
        logger.error(f"Failed to delete script chapter: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{script_id}/chapters", summary="获取剧本章节列表")
async def get_script_chapters(
    script_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:read"))
):
    """获取指定剧本的所有章节"""
    try:
        script_service = ScriptService(db)
        chapters = await script_service.get_script_chapters(script_id)
        
        return ResponseBuilder.success(
            data=chapters,
            message="获取章节列表成功"
        )
    except Exception as e:
        logger.error(f"Failed to get script chapters: {str(e)}")
        raise HTTPException(status_code=500, detail="获取章节列表失败")


# ==================== 人员分配管理 ====================

@router.post("/assignments", response_model=ScriptAssignmentResponse, summary="创建人员分配")
async def create_script_assignment(
    assignment_data: ScriptAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:assign"))
):
    """创建剧本人员分配"""
    try:
        script_service = ScriptService(db)
        assignment = await script_service.create_script_assignment(assignment_data)
        
        logger.info(
            f"Script assignment created: user {assignment_data.user_id} assigned to script {assignment_data.script_id} by user {current_user.username}",
            extra={"user_id": current_user.id, "assignment_id": assignment.id}
        )
        
        return ResponseBuilder.created(
            data=assignment,
            message="人员分配成功"
        )
    except Exception as e:
        logger.error(f"Failed to create script assignment: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/assignments/{assignment_id}", response_model=ScriptAssignmentResponse, summary="获取分配信息")
async def get_script_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:read"))
):
    """获取人员分配详细信息"""
    try:
        script_service = ScriptService(db)
        assignment = await script_service.get_script_assignment_by_id(assignment_id)
        
        if not assignment:
            raise HTTPException(status_code=404, detail="分配记录不存在")
        
        return ResponseBuilder.success(
            data=assignment,
            message="获取分配信息成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get script assignment: {str(e)}")
        raise HTTPException(status_code=500, detail="获取分配信息失败")


@router.put("/assignments/{assignment_id}", response_model=ScriptAssignmentResponse, summary="更新分配信息")
async def update_script_assignment(
    assignment_id: int,
    assignment_data: ScriptAssignmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:assign"))
):
    """更新人员分配信息"""
    try:
        script_service = ScriptService(db)
        updated_assignment = await script_service.update_script_assignment(assignment_id, assignment_data)
        
        logger.info(
            f"Script assignment updated: {assignment_id} by user {current_user.username}",
            extra={"user_id": current_user.id, "assignment_id": assignment_id}
        )
        
        return ResponseBuilder.success(
            data=updated_assignment,
            message="分配信息更新成功"
        )
    except Exception as e:
        logger.error(f"Failed to update script assignment: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/assignments/{assignment_id}", summary="删除分配")
async def delete_script_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:assign"))
):
    """删除人员分配"""
    try:
        script_service = ScriptService(db)
        await script_service.delete_script_assignment(assignment_id)
        
        logger.info(
            f"Script assignment deleted: {assignment_id} by user {current_user.username}",
            extra={"user_id": current_user.id, "assignment_id": assignment_id}
        )
        
        return ResponseBuilder.success(
            message="分配删除成功"
        )
    except Exception as e:
        logger.error(f"Failed to delete script assignment: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{script_id}/assignments", summary="获取剧本分配列表")
async def get_script_assignments(
    script_id: int,
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="分配状态"),
    role: Optional[str] = Query(None, description="角色"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:read"))
):
    """获取指定剧本的人员分配列表"""
    try:
        # 构建搜索查询
        search_query = AssignmentSearchQuery(
            script_id=script_id,
            status=status,
            role=role
        )
        
        script_service = ScriptService(db)
        assignments, total = await script_service.get_script_assignments(page, size, search_query)
        
        return ResponseBuilder.paginated(
            data=assignments,
            total=total,
            page=page,
            size=size,
            message="获取分配列表成功"
        )
    except Exception as e:
        logger.error(f"Failed to get script assignments: {str(e)}")
        raise HTTPException(status_code=500, detail="获取分配列表失败")


@router.get("/users/{user_id}/assignments", summary="获取用户分配列表")
async def get_user_assignments(
    user_id: int,
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="分配状态"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:read"))
):
    """获取指定用户的分配列表"""
    try:
        # 构建搜索查询
        search_query = AssignmentSearchQuery(
            user_id=user_id,
            status=status
        )
        
        script_service = ScriptService(db)
        assignments, total = await script_service.get_user_assignments(page, size, search_query)
        
        return ResponseBuilder.paginated(
            data=assignments,
            total=total,
            page=page,
            size=size,
            message="获取用户分配列表成功"
        )
    except Exception as e:
        logger.error(f"Failed to get user assignments: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户分配列表失败")


# ==================== 批量操作和统计 ====================

@router.post("/batch", summary="批量操作剧本")
async def batch_operation_scripts(
    operation: ScriptBatchOperation,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:update"))
):
    """批量操作剧本（更新状态、删除等）"""
    try:
        script_service = ScriptService(db)
        result = await script_service.batch_operation(operation)
        
        logger.info(
            f"Script batch operation: {operation.operation} on {len(operation.script_ids)} scripts by user {current_user.username}",
            extra={
                "user_id": current_user.id,
                "operation": operation.operation,
                "script_count": len(operation.script_ids)
            }
        )
        
        return ResponseBuilder.success(
            data=result,
            message=f"批量操作完成：成功 {result['success_count']} 个，失败 {result['failed_count']} 个"
        )
    except Exception as e:
        logger.error(f"Failed to batch operation scripts: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/statistics/overview", response_model=ScriptStatistics, summary="获取剧本统计信息")
async def get_script_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:read"))
):
    """获取剧本统计信息"""
    try:
        script_service = ScriptService(db)
        statistics = await script_service.get_script_statistics()
        
        return ResponseBuilder.success(
            data=statistics,
            message="获取剧本统计信息成功"
        )
    except Exception as e:
        logger.error(f"Failed to get script statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="获取剧本统计信息失败")


# ==================== 导入导出 ====================

@router.post("/import", summary="导入剧本")
async def import_scripts(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:create"))
):
    """从文件导入剧本数据"""
    try:
        # 验证文件类型
        if not file.filename.endswith(('.json', '.csv', '.xlsx')):
            raise HTTPException(status_code=400, detail="不支持的文件格式")
        
        # 读取文件内容
        content = await file.read()
        
        script_service = ScriptService(db)
        result = await script_service.import_scripts(content, file.filename, current_user.id)
        
        logger.info(
            f"Scripts imported: {result['success_count']} successful, {result['failed_count']} failed by user {current_user.username}",
            extra={"user_id": current_user.id, "filename": file.filename}
        )
        
        return ResponseBuilder.success(
            data=result,
            message=f"导入完成：成功 {result['success_count']} 个，失败 {result['failed_count']} 个"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to import scripts: {str(e)}")
        raise HTTPException(status_code=500, detail="导入失败")


@router.get("/export", summary="导出剧本")
async def export_scripts(
    format: str = Query("json", description="导出格式 (json, csv, xlsx)"),
    script_ids: Optional[str] = Query(None, description="剧本ID列表，逗号分隔"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("script:read"))
):
    """导出剧本数据"""
    try:
        if format not in ['json', 'csv', 'xlsx']:
            raise HTTPException(status_code=400, detail="不支持的导出格式")
        
        # 解析剧本ID列表
        ids = [int(id.strip()) for id in script_ids.split(',')] if script_ids else None
        
        script_service = ScriptService(db)
        export_data = await script_service.export_scripts(ids, format)
        
        logger.info(
            f"Scripts exported: format={format}, count={len(ids) if ids else 'all'} by user {current_user.username}",
            extra={"user_id": current_user.id, "format": format}
        )
        
        return ResponseBuilder.success(
            data=export_data,
            message="导出成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to export scripts: {str(e)}")
        raise HTTPException(status_code=500, detail="导出失败")