from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta

from app.models.script import DramaSociety, Script, ScriptChapter, ScriptAssignment
from app.models.user import User
from app.schemas.script import (
    DramaSocietyCreate, DramaSocietyUpdate, ScriptCreate, ScriptUpdate,
    ScriptChapterCreate, ScriptChapterUpdate, ScriptAssignmentCreate,
    ScriptAssignmentUpdate, ScriptSearchQuery, AssignmentSearchQuery,
    ScriptBatchOperation
)
from app.core.exceptions import (
    raise_not_found, raise_duplicate, raise_validation_error,
    raise_business_error, raise_permission_error
)
from app.core.logger import logger
from app.core.database import DatabaseManager


class ScriptService:
    """剧本服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.db_manager = DatabaseManager()
    
    # ==================== 剧社管理 ====================
    
    async def create_drama_society(self, society_data: DramaSocietyCreate, creator_id: int) -> DramaSociety:
        """创建剧社"""
        # 检查剧社名是否已存在
        existing_society = await self.get_drama_society_by_name(society_data.name)
        if existing_society:
            raise_duplicate("DramaSociety", "name", society_data.name)
        
        # 创建剧社
        society_dict = society_data.dict()
        society_dict["creator_id"] = creator_id
        society = DramaSociety(**society_dict)
        
        try:
            self.db.add(society)
            await self.db.commit()
            await self.db.refresh(society)
            
            logger.info(f"Drama society created: {society.name} (ID: {society.id})")
            return society
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create drama society: {str(e)}")
            raise_business_error("Failed to create drama society")
    
    async def get_drama_society_by_id(self, society_id: int) -> Optional[DramaSociety]:
        """根据ID获取剧社"""
        result = await self.db.execute(
            select(DramaSociety)
            .options(selectinload(DramaSociety.creator))
            .where(DramaSociety.id == society_id)
        )
        return result.scalar_one_or_none()
    
    async def get_drama_society_by_name(self, name: str) -> Optional[DramaSociety]:
        """根据名称获取剧社"""
        result = await self.db.execute(
            select(DramaSociety).where(DramaSociety.name == name)
        )
        return result.scalar_one_or_none()
    
    async def update_drama_society(self, society_id: int, society_data: DramaSocietyUpdate) -> DramaSociety:
        """更新剧社"""
        society = await self.get_drama_society_by_id(society_id)
        if not society:
            raise_not_found("DramaSociety", society_id)
        
        # 检查剧社名是否重复（如果要更新名称）
        if society_data.name and society_data.name != society.name:
            existing_society = await self.get_drama_society_by_name(society_data.name)
            if existing_society:
                raise_duplicate("DramaSociety", "name", society_data.name)
        
        # 更新剧社信息
        update_data = society_data.dict(exclude_unset=True)
        
        try:
            await self.db.execute(
                update(DramaSociety)
                .where(DramaSociety.id == society_id)
                .values(**update_data)
            )
            await self.db.commit()
            
            # 重新获取更新后的剧社
            updated_society = await self.get_drama_society_by_id(society_id)
            
            logger.info(f"Drama society updated: {society.name} (ID: {society_id})")
            return updated_society
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update drama society {society_id}: {str(e)}")
            raise_business_error("Failed to update drama society")
    
    async def delete_drama_society(self, society_id: int) -> bool:
        """删除剧社"""
        society = await self.get_drama_society_by_id(society_id)
        if not society:
            raise_not_found("DramaSociety", society_id)
        
        # 检查是否有关联的剧本
        script_count_result = await self.db.execute(
            select(func.count(Script.id)).where(Script.drama_society_id == society_id)
        )
        script_count = script_count_result.scalar()
        
        if script_count > 0:
            raise_validation_error(f"Cannot delete drama society: {script_count} scripts are associated with it")
        
        try:
            await self.db.execute(
                delete(DramaSociety).where(DramaSociety.id == society_id)
            )
            await self.db.commit()
            
            logger.info(f"Drama society deleted: {society.name} (ID: {society_id})")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete drama society {society_id}: {str(e)}")
            raise_business_error("Failed to delete drama society")
    
    async def get_drama_societies(
        self, 
        page: int = 1, 
        size: int = 20,
        creator_id: Optional[int] = None
    ) -> Tuple[List[DramaSociety], int]:
        """获取剧社列表"""
        query = select(DramaSociety).options(selectinload(DramaSociety.creator))
        
        # 按创建者过滤
        if creator_id:
            query = query.where(DramaSociety.creator_id == creator_id)
        
        # 排序
        query = query.order_by(DramaSociety.created_at.desc())
        
        # 获取总数
        count_query = select(func.count(DramaSociety.id))
        if creator_id:
            count_query = count_query.where(DramaSociety.creator_id == creator_id)
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # 分页
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)
        
        result = await self.db.execute(query)
        societies = result.scalars().all()
        
        return list(societies), total
    
    # ==================== 剧本管理 ====================
    
    async def create_script(self, script_data: ScriptCreate, creator_id: int) -> Script:
        """创建剧本"""
        # 检查剧社是否存在
        society = await self.get_drama_society_by_id(script_data.drama_society_id)
        if not society:
            raise_not_found("DramaSociety", script_data.drama_society_id)
        
        # 检查剧本名是否在该剧社中已存在
        existing_script = await self.get_script_by_name_and_society(
            script_data.title, script_data.drama_society_id
        )
        if existing_script:
            raise_duplicate("Script", "title", script_data.title)
        
        # 创建剧本
        script_dict = script_data.dict()
        script_dict["creator_id"] = creator_id
        script = Script(**script_dict)
        
        try:
            self.db.add(script)
            await self.db.commit()
            await self.db.refresh(script)
            
            logger.info(f"Script created: {script.title} (ID: {script.id})")
            return script
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create script: {str(e)}")
            raise_business_error("Failed to create script")
    
    async def get_script_by_id(self, script_id: int) -> Optional[Script]:
        """根据ID获取剧本"""
        result = await self.db.execute(
            select(Script)
            .options(
                selectinload(Script.drama_society),
                selectinload(Script.creator),
                selectinload(Script.chapters),
                selectinload(Script.assignments)
            )
            .where(Script.id == script_id)
        )
        return result.scalar_one_or_none()
    
    async def get_script_by_name_and_society(self, title: str, society_id: int) -> Optional[Script]:
        """根据标题和剧社获取剧本"""
        result = await self.db.execute(
            select(Script).where(
                and_(
                    Script.title == title,
                    Script.drama_society_id == society_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def update_script(self, script_id: int, script_data: ScriptUpdate) -> Script:
        """更新剧本"""
        script = await self.get_script_by_id(script_id)
        if not script:
            raise_not_found("Script", script_id)
        
        # 检查剧本名是否重复（如果要更新标题）
        if script_data.title and script_data.title != script.title:
            existing_script = await self.get_script_by_name_and_society(
                script_data.title, script.drama_society_id
            )
            if existing_script:
                raise_duplicate("Script", "title", script_data.title)
        
        # 更新剧本信息
        update_data = script_data.dict(exclude_unset=True)
        
        try:
            await self.db.execute(
                update(Script)
                .where(Script.id == script_id)
                .values(**update_data)
            )
            await self.db.commit()
            
            # 重新获取更新后的剧本
            updated_script = await self.get_script_by_id(script_id)
            
            logger.info(f"Script updated: {script.title} (ID: {script_id})")
            return updated_script
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update script {script_id}: {str(e)}")
            raise_business_error("Failed to update script")
    
    async def delete_script(self, script_id: int) -> bool:
        """删除剧本"""
        script = await self.get_script_by_id(script_id)
        if not script:
            raise_not_found("Script", script_id)
        
        try:
            # 删除相关的章节和分配记录（级联删除）
            await self.db.execute(
                delete(Script).where(Script.id == script_id)
            )
            await self.db.commit()
            
            logger.info(f"Script deleted: {script.title} (ID: {script_id})")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete script {script_id}: {str(e)}")
            raise_business_error("Failed to delete script")
    
    async def get_scripts(
        self, 
        page: int = 1, 
        size: int = 20,
        search_query: Optional[ScriptSearchQuery] = None
    ) -> Tuple[List[Script], int]:
        """获取剧本列表"""
        query = select(Script).options(
            selectinload(Script.drama_society),
            selectinload(Script.creator)
        )
        
        # 构建搜索条件
        if search_query:
            conditions = []
            
            if search_query.keyword:
                keyword = f"%{search_query.keyword}%"
                conditions.append(
                    or_(
                        Script.title.ilike(keyword),
                        Script.description.ilike(keyword),
                        Script.tags.ilike(keyword)
                    )
                )
            
            if search_query.drama_society_id:
                conditions.append(Script.drama_society_id == search_query.drama_society_id)
            
            if search_query.creator_id:
                conditions.append(Script.creator_id == search_query.creator_id)
            
            if search_query.script_type:
                conditions.append(Script.script_type == search_query.script_type)
            
            if search_query.status:
                conditions.append(Script.status == search_query.status)
            
            if search_query.created_after:
                conditions.append(Script.created_at >= search_query.created_after)
            
            if search_query.created_before:
                conditions.append(Script.created_at <= search_query.created_before)
            
            if conditions:
                query = query.where(and_(*conditions))
        
        # 排序
        if search_query and search_query.sort_by:
            if search_query.sort_order == "desc":
                query = query.order_by(getattr(Script, search_query.sort_by).desc())
            else:
                query = query.order_by(getattr(Script, search_query.sort_by))
        else:
            query = query.order_by(Script.created_at.desc())
        
        # 获取总数
        count_query = select(func.count(Script.id))
        if search_query:
            conditions = []
            if search_query.keyword:
                keyword = f"%{search_query.keyword}%"
                conditions.append(
                    or_(
                        Script.title.ilike(keyword),
                        Script.description.ilike(keyword),
                        Script.tags.ilike(keyword)
                    )
                )
            if search_query.drama_society_id:
                conditions.append(Script.drama_society_id == search_query.drama_society_id)
            if search_query.creator_id:
                conditions.append(Script.creator_id == search_query.creator_id)
            if search_query.script_type:
                conditions.append(Script.script_type == search_query.script_type)
            if search_query.status:
                conditions.append(Script.status == search_query.status)
            if search_query.created_after:
                conditions.append(Script.created_at >= search_query.created_after)
            if search_query.created_before:
                conditions.append(Script.created_at <= search_query.created_before)
            
            if conditions:
                count_query = count_query.where(and_(*conditions))
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # 分页
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)
        
        result = await self.db.execute(query)
        scripts = result.scalars().all()
        
        return list(scripts), total
    
    # ==================== 章节管理 ====================
    
    async def create_chapter(self, chapter_data: ScriptChapterCreate) -> ScriptChapter:
        """创建章节"""
        # 检查剧本是否存在
        script = await self.get_script_by_id(chapter_data.script_id)
        if not script:
            raise_not_found("Script", chapter_data.script_id)
        
        # 检查章节标题是否在该剧本中已存在
        existing_chapter = await self.get_chapter_by_title_and_script(
            chapter_data.title, chapter_data.script_id
        )
        if existing_chapter:
            raise_duplicate("ScriptChapter", "title", chapter_data.title)
        
        # 创建章节
        chapter_dict = chapter_data.dict()
        chapter = ScriptChapter(**chapter_dict)
        
        try:
            self.db.add(chapter)
            await self.db.commit()
            await self.db.refresh(chapter)
            
            logger.info(f"Chapter created: {chapter.title} (ID: {chapter.id})")
            return chapter
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create chapter: {str(e)}")
            raise_business_error("Failed to create chapter")
    
    async def get_chapter_by_id(self, chapter_id: int) -> Optional[ScriptChapter]:
        """根据ID获取章节"""
        result = await self.db.execute(
            select(ScriptChapter)
            .options(selectinload(ScriptChapter.script))
            .where(ScriptChapter.id == chapter_id)
        )
        return result.scalar_one_or_none()
    
    async def get_chapter_by_title_and_script(self, title: str, script_id: int) -> Optional[ScriptChapter]:
        """根据标题和剧本获取章节"""
        result = await self.db.execute(
            select(ScriptChapter).where(
                and_(
                    ScriptChapter.title == title,
                    ScriptChapter.script_id == script_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def update_chapter(self, chapter_id: int, chapter_data: ScriptChapterUpdate) -> ScriptChapter:
        """更新章节"""
        chapter = await self.get_chapter_by_id(chapter_id)
        if not chapter:
            raise_not_found("ScriptChapter", chapter_id)
        
        # 检查章节标题是否重复（如果要更新标题）
        if chapter_data.title and chapter_data.title != chapter.title:
            existing_chapter = await self.get_chapter_by_title_and_script(
                chapter_data.title, chapter.script_id
            )
            if existing_chapter:
                raise_duplicate("ScriptChapter", "title", chapter_data.title)
        
        # 更新章节信息
        update_data = chapter_data.dict(exclude_unset=True)
        
        try:
            await self.db.execute(
                update(ScriptChapter)
                .where(ScriptChapter.id == chapter_id)
                .values(**update_data)
            )
            await self.db.commit()
            
            # 重新获取更新后的章节
            updated_chapter = await self.get_chapter_by_id(chapter_id)
            
            logger.info(f"Chapter updated: {chapter.title} (ID: {chapter_id})")
            return updated_chapter
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update chapter {chapter_id}: {str(e)}")
            raise_business_error("Failed to update chapter")
    
    async def delete_chapter(self, chapter_id: int) -> bool:
        """删除章节"""
        chapter = await self.get_chapter_by_id(chapter_id)
        if not chapter:
            raise_not_found("ScriptChapter", chapter_id)
        
        try:
            await self.db.execute(
                delete(ScriptChapter).where(ScriptChapter.id == chapter_id)
            )
            await self.db.commit()
            
            logger.info(f"Chapter deleted: {chapter.title} (ID: {chapter_id})")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete chapter {chapter_id}: {str(e)}")
            raise_business_error("Failed to delete chapter")
    
    async def get_script_chapters(self, script_id: int) -> List[ScriptChapter]:
        """获取剧本的所有章节"""
        result = await self.db.execute(
            select(ScriptChapter)
            .where(ScriptChapter.script_id == script_id)
            .order_by(ScriptChapter.chapter_number)
        )
        return list(result.scalars().all())
    
    # ==================== 人员分配管理 ====================
    
    async def create_assignment(self, assignment_data: ScriptAssignmentCreate) -> ScriptAssignment:
        """创建人员分配"""
        # 检查剧本是否存在
        script = await self.get_script_by_id(assignment_data.script_id)
        if not script:
            raise_not_found("Script", assignment_data.script_id)
        
        # 检查用户是否存在
        user_result = await self.db.execute(
            select(User).where(User.id == assignment_data.user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise_not_found("User", assignment_data.user_id)
        
        # 检查是否已分配相同角色
        existing_assignment = await self.db.execute(
            select(ScriptAssignment).where(
                and_(
                    ScriptAssignment.script_id == assignment_data.script_id,
                    ScriptAssignment.user_id == assignment_data.user_id,
                    ScriptAssignment.role_name == assignment_data.role_name
                )
            )
        )
        if existing_assignment.scalar_one_or_none():
            raise_duplicate(
                "ScriptAssignment", 
                "assignment", 
                f"{assignment_data.user_id}-{assignment_data.role_name}"
            )
        
        # 创建分配
        assignment_dict = assignment_data.dict()
        assignment = ScriptAssignment(**assignment_dict)
        
        try:
            self.db.add(assignment)
            await self.db.commit()
            await self.db.refresh(assignment)
            
            logger.info(
                f"Assignment created: {assignment.role_name} for user {assignment.user_id} "
                f"in script {assignment.script_id}"
            )
            return assignment
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create assignment: {str(e)}")
            raise_business_error("Failed to create assignment")
    
    async def get_assignment_by_id(self, assignment_id: int) -> Optional[ScriptAssignment]:
        """根据ID获取分配"""
        result = await self.db.execute(
            select(ScriptAssignment)
            .options(
                selectinload(ScriptAssignment.script),
                selectinload(ScriptAssignment.user),
                selectinload(ScriptAssignment.assigned_by_user)
            )
            .where(ScriptAssignment.id == assignment_id)
        )
        return result.scalar_one_or_none()
    
    async def update_assignment(self, assignment_id: int, assignment_data: ScriptAssignmentUpdate) -> ScriptAssignment:
        """更新分配"""
        assignment = await self.get_assignment_by_id(assignment_id)
        if not assignment:
            raise_not_found("ScriptAssignment", assignment_id)
        
        # 更新分配信息
        update_data = assignment_data.dict(exclude_unset=True)
        
        try:
            await self.db.execute(
                update(ScriptAssignment)
                .where(ScriptAssignment.id == assignment_id)
                .values(**update_data)
            )
            await self.db.commit()
            
            # 重新获取更新后的分配
            updated_assignment = await self.get_assignment_by_id(assignment_id)
            
            logger.info(f"Assignment updated: ID {assignment_id}")
            return updated_assignment
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update assignment {assignment_id}: {str(e)}")
            raise_business_error("Failed to update assignment")
    
    async def delete_assignment(self, assignment_id: int) -> bool:
        """删除分配"""
        assignment = await self.get_assignment_by_id(assignment_id)
        if not assignment:
            raise_not_found("ScriptAssignment", assignment_id)
        
        try:
            await self.db.execute(
                delete(ScriptAssignment).where(ScriptAssignment.id == assignment_id)
            )
            await self.db.commit()
            
            logger.info(f"Assignment deleted: ID {assignment_id}")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete assignment {assignment_id}: {str(e)}")
            raise_business_error("Failed to delete assignment")
    
    async def get_script_assignments(self, script_id: int) -> List[ScriptAssignment]:
        """获取剧本的所有分配"""
        result = await self.db.execute(
            select(ScriptAssignment)
            .options(
                selectinload(ScriptAssignment.user),
                selectinload(ScriptAssignment.assigned_by_user)
            )
            .where(ScriptAssignment.script_id == script_id)
            .order_by(ScriptAssignment.created_at)
        )
        return list(result.scalars().all())
    
    async def get_user_assignments(
        self, 
        user_id: int,
        search_query: Optional[AssignmentSearchQuery] = None
    ) -> List[ScriptAssignment]:
        """获取用户的所有分配"""
        query = select(ScriptAssignment).options(
            selectinload(ScriptAssignment.script),
            selectinload(ScriptAssignment.assigned_by_user)
        ).where(ScriptAssignment.user_id == user_id)
        
        # 构建搜索条件
        if search_query:
            conditions = [ScriptAssignment.user_id == user_id]
            
            if search_query.script_id:
                conditions.append(ScriptAssignment.script_id == search_query.script_id)
            
            if search_query.role_name:
                conditions.append(ScriptAssignment.role_name.ilike(f"%{search_query.role_name}%"))
            
            if search_query.status:
                conditions.append(ScriptAssignment.status == search_query.status)
            
            if conditions:
                query = query.where(and_(*conditions))
        
        # 排序
        query = query.order_by(ScriptAssignment.created_at.desc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    # ==================== 批量操作 ====================
    
    async def batch_update_scripts(self, operation: ScriptBatchOperation) -> Dict[str, Any]:
        """批量更新剧本"""
        results = {
            "success_count": 0,
            "failed_count": 0,
            "errors": []
        }
        
        try:
            for script_id in operation.script_ids:
                try:
                    if operation.operation == "update_status":
                        await self.db.execute(
                            update(Script)
                            .where(Script.id == script_id)
                            .values(status=operation.data.get("status"))
                        )
                    elif operation.operation == "delete":
                        await self.db.execute(
                            delete(Script).where(Script.id == script_id)
                        )
                    
                    results["success_count"] += 1
                    
                except Exception as e:
                    results["failed_count"] += 1
                    results["errors"].append({
                        "script_id": script_id,
                        "error": str(e)
                    })
            
            await self.db.commit()
            
            logger.info(
                f"Batch script operation completed: "
                f"{results['success_count']} success, {results['failed_count']} failed"
            )
            
            return results
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Batch script operation failed: {str(e)}")
            raise_business_error("Batch script operation failed")
    
    # ==================== 统计信息 ====================
    
    async def get_script_statistics(self, society_id: Optional[int] = None) -> Dict[str, Any]:
        """获取剧本统计信息"""
        base_query = select(func.count(Script.id))
        if society_id:
            base_query = base_query.where(Script.drama_society_id == society_id)
        
        # 总剧本数
        total_scripts_result = await self.db.execute(base_query)
        total_scripts = total_scripts_result.scalar()
        
        # 按状态统计
        status_query = select(Script.status, func.count(Script.id)).group_by(Script.status)
        if society_id:
            status_query = status_query.where(Script.drama_society_id == society_id)
        
        status_result = await self.db.execute(status_query)
        status_stats = dict(status_result.all())
        
        # 按类型统计
        type_query = select(Script.script_type, func.count(Script.id)).group_by(Script.script_type)
        if society_id:
            type_query = type_query.where(Script.drama_society_id == society_id)
        
        type_result = await self.db.execute(type_query)
        type_stats = dict(type_result.all())
        
        # 最近创建的剧本
        recent_query = select(Script).order_by(Script.created_at.desc()).limit(5)
        if society_id:
            recent_query = recent_query.where(Script.drama_society_id == society_id)
        
        recent_result = await self.db.execute(recent_query)
        recent_scripts = list(recent_result.scalars().all())
        
        return {
            "total_scripts": total_scripts,
            "status_statistics": status_stats,
            "type_statistics": type_stats,
            "recent_scripts": [
                {
                    "id": script.id,
                    "title": script.title,
                    "created_at": script.created_at
                }
                for script in recent_scripts
            ]
        }