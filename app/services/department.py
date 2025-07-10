from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, asc, update, delete
from sqlalchemy.orm import selectinload, joinedload
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status

from app.models.department import Department, DepartmentMember
from app.models.user import User
from app.schemas.department import (
    DepartmentCreate, DepartmentUpdate, DepartmentQuery, DepartmentQueryExtended,
    DepartmentMemberCreate, DepartmentMemberUpdate,
    DepartmentBatchOperation, DepartmentMove
)
from app.core.logger import logger


class DepartmentService:
    """部门服务类"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_department(self, department_data: DepartmentCreate, creator_id: int) -> Department:
        """创建部门"""
        try:
            # 检查部门名称是否重复（同级别下）
            existing_dept = await self._check_duplicate_name(
                department_data.name, 
                department_data.parent_id
            )
            if existing_dept:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="同级别下已存在相同名称的部门"
                )
            
            # 处理 parent_id：将 0 转换为 None（根部门）
            if department_data.parent_id == 0:
                department_data.parent_id = None
            
            # 验证父部门是否存在
            parent_dept = None
            if department_data.parent_id:
                parent_dept = await self.get_department_by_id(department_data.parent_id)
                if not parent_dept:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="父部门不存在"
                    )
                if not parent_dept.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="父部门未激活，无法在其下创建子部门"
                    )
            
            # 验证负责人是否存在
            if department_data.manager_id:
                manager = await self._get_user_by_id(department_data.manager_id)
                if not manager:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="指定的负责人不存在"
                    )
                if not manager.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="指定的负责人未激活"
                    )
            
            # 创建部门
            department = Department(**department_data.dict())
            self.db.add(department)
            await self.db.flush()  # 获取ID
            
            # 更新路径和层级
            await department.update_path(self.db)
            await self.db.commit()
            await self.db.refresh(department)
            
            logger.info(f"部门创建成功: {department.name} (ID: {department.id})")
            return department
            
        except HTTPException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"创建部门失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="创建部门失败"
            )
    
    async def get_department_by_id(self, department_id: int, include_children: bool = False, include_members: bool = False) -> Optional[Department]:
        """根据ID获取部门"""
        try:
            query = select(Department).where(Department.id == department_id)
            
            # 预加载关联数据
            if include_children:
                query = query.options(selectinload(Department.children))
            if include_members:
                query = query.options(selectinload(Department.members).selectinload(DepartmentMember.user))
            
            # 总是加载管理员信息
            query = query.options(selectinload(Department.manager))
            
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"获取部门失败: {str(e)}")
            return None
    
    async def get_departments(self, query_params: DepartmentQueryExtended) -> Tuple[List[Department], int]:
        """获取部门列表"""
        try:
            # 构建查询条件
            conditions = [Department.status != Department.STATUS_DELETED]
            
            if query_params.name:
                conditions.append(Department.name.ilike(f"%{query_params.name}%"))
            
            if query_params.parent_id is not None:
                conditions.append(Department.parent_id == query_params.parent_id)
            
            if query_params.manager_id:
                conditions.append(Department.manager_id == query_params.manager_id)
            
            if query_params.status is not None:
                conditions.append(Department.status == query_params.status)
            
            if query_params.level:
                conditions.append(Department.level == query_params.level)
            
            # 构建查询
            base_query = select(Department).where(and_(*conditions))
            
            # 预加载关联数据
            if query_params.include_children:
                base_query = base_query.options(selectinload(Department.children))
            if query_params.include_members:
                base_query = base_query.options(selectinload(Department.members).selectinload(DepartmentMember.user))
            
            # 总是加载管理员信息
            base_query = base_query.options(selectinload(Department.manager))
            
            # 获取总数
            count_query = select(func.count(Department.id)).where(and_(*conditions))
            total_result = await self.db.execute(count_query)
            total = total_result.scalar()
            
            # 分页和排序
            query = base_query.order_by(
                Department.level.asc(),
                Department.sort_order.asc(),
                Department.created_at.desc()
            )
            
            if query_params.page and query_params.page_size:
                offset = (query_params.page - 1) * query_params.page_size
                query = query.offset(offset).limit(query_params.page_size)
            
            result = await self.db.execute(query)
            departments = result.scalars().all()
            
            return departments, total
            
        except Exception as e:
            logger.error(f"获取部门列表失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="获取部门列表失败"
            )
    
    async def get_department_tree(self, root_id: Optional[int] = None) -> List[Department]:
        """获取部门树形结构"""
        try:
            # 获取所有活跃部门
            query = select(Department).where(
                Department.status == Department.STATUS_ACTIVE
            ).options(
                selectinload(Department.manager),
                selectinload(Department.children)
            ).order_by(
                Department.level.asc(),
                Department.sort_order.asc()
            )
            
            if root_id:
                # 获取指定根部门及其子部门
                root_dept = await self.get_department_by_id(root_id)
                if not root_dept:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="指定的根部门不存在"
                    )
                query = query.where(Department.path.like(f"{root_dept.path}%"))
            else:
                # 获取所有根部门
                query = query.where(Department.parent_id.is_(None))
            
            result = await self.db.execute(query)
            departments = result.scalars().all()
            
            return departments
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取部门树失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="获取部门树失败"
            )
    
    async def update_department(self, department_id: int, update_data: DepartmentUpdate) -> Department:
        """更新部门"""
        try:
            department = await self.get_department_by_id(department_id)
            if not department:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="部门不存在"
                )
            
            # 检查名称重复（如果更新了名称）
            if update_data.name and update_data.name != department.name:
                existing_dept = await self._check_duplicate_name(
                    update_data.name,
                    update_data.parent_id if update_data.parent_id is not None else department.parent_id
                )
                if existing_dept and existing_dept.id != department_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="同级别下已存在相同名称的部门"
                    )
            
            # 处理 parent_id：将 0 转换为 None（根部门）
            if update_data.parent_id == 0:
                update_data.parent_id = None
            
            # 检查父部门变更
            if update_data.parent_id is not None and update_data.parent_id != department.parent_id:
                # 不能将部门设置为自己的子部门
                if update_data.parent_id == department_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="不能将部门设置为自己的父部门"
                    )
                
                # 检查是否会形成循环引用
                if await self._would_create_cycle(department_id, update_data.parent_id):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="不能将部门移动到其子部门下"
                    )
                
                # 验证新父部门
                if update_data.parent_id:
                    parent_dept = await self.get_department_by_id(update_data.parent_id)
                    if not parent_dept or not parent_dept.is_active:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="指定的父部门不存在或未激活"
                        )
            
            # 验证负责人
            if update_data.manager_id:
                manager = await self._get_user_by_id(update_data.manager_id)
                if not manager or not manager.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="指定的负责人不存在或未激活"
                    )
            
            # 更新字段
            update_dict = update_data.dict(exclude_unset=True)
            for field, value in update_dict.items():
                setattr(department, field, value)
            
            # 如果父部门发生变化，需要更新路径和层级
            if update_data.parent_id is not None and update_data.parent_id != department.parent_id:
                await self._update_department_hierarchy(department)
            
            await self.db.commit()
            await self.db.refresh(department)
            
            logger.info(f"部门更新成功: {department.name} (ID: {department.id})")
            return department
            
        except HTTPException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"更新部门失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="更新部门失败"
            )
    
    async def delete_department(self, department_id: int, force: bool = False) -> bool:
        """删除部门"""
        try:
            department = await self.get_department_by_id(department_id, include_children=True, include_members=True)
            if not department:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="部门不存在"
                )
            
            # 检查是否有子部门
            active_children = [child for child in department.children if child.is_active]
            if active_children and not force:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="部门下还有子部门，无法删除。请先删除或移动子部门，或使用强制删除"
                )
            
            # 检查是否有成员
            active_members = [member for member in department.members if member.is_active]
            if active_members and not force:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="部门下还有成员，无法删除。请先移除成员，或使用强制删除"
                )
            
            if force:
                # 强制删除：递归删除所有子部门和成员关系
                await self._force_delete_department_recursive(department)
            else:
                # 软删除
                department.status = Department.STATUS_DELETED
            
            await self.db.commit()
            
            logger.info(f"部门删除成功: {department.name} (ID: {department.id}, force: {force})")
            return True
            
        except HTTPException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"删除部门失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="删除部门失败"
            )
    
    async def batch_operation(self, operation_data: DepartmentBatchOperation) -> Dict[str, Any]:
        """批量操作部门"""
        try:
            results = {
                'success_count': 0,
                'failed_count': 0,
                'failed_items': []
            }
            
            for dept_id in operation_data.department_ids:
                try:
                    department = await self.get_department_by_id(dept_id)
                    if not department:
                        results['failed_count'] += 1
                        results['failed_items'].append({
                            'id': dept_id,
                            'error': '部门不存在'
                        })
                        continue
                    
                    if operation_data.operation == 'activate':
                        department.status = Department.STATUS_ACTIVE
                    elif operation_data.operation == 'deactivate':
                        department.status = Department.STATUS_INACTIVE
                    elif operation_data.operation == 'delete':
                        department.status = Department.STATUS_DELETED
                    
                    results['success_count'] += 1
                    
                except Exception as e:
                    results['failed_count'] += 1
                    results['failed_items'].append({
                        'id': dept_id,
                        'error': str(e)
                    })
            
            await self.db.commit()
            
            logger.info(f"批量操作完成: {operation_data.operation}, 成功: {results['success_count']}, 失败: {results['failed_count']}")
            return results
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"批量操作失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="批量操作失败"
            )
    
    async def move_department(self, department_id: int, move_data: DepartmentMove) -> Department:
        """移动部门"""
        try:
            department = await self.get_department_by_id(department_id)
            if not department:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="部门不存在"
                )
            
            # 处理 target_parent_id：将 0 转换为 None（根部门）
            if move_data.target_parent_id == 0:
                move_data.target_parent_id = None
            
            # 检查目标父部门
            if move_data.target_parent_id:
                if move_data.target_parent_id == department_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="不能将部门移动到自己下面"
                    )
                
                # 检查循环引用
                if await self._would_create_cycle(department_id, move_data.target_parent_id):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="不能将部门移动到其子部门下"
                    )
                
                target_parent = await self.get_department_by_id(move_data.target_parent_id)
                if not target_parent or not target_parent.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="目标父部门不存在或未激活"
                    )
            
            # 更新父部门
            department.parent_id = move_data.target_parent_id
            
            # 更新排序
            if move_data.sort_order is not None:
                department.sort_order = move_data.sort_order
            
            # 更新层级结构
            await self._update_department_hierarchy(department)
            
            await self.db.commit()
            await self.db.refresh(department)
            
            logger.info(f"部门移动成功: {department.name} (ID: {department.id})")
            return department
            
        except HTTPException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"移动部门失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="移动部门失败"
            )
    
    # 部门成员管理方法
    async def add_department_member(self, department_id: int, member_data: DepartmentMemberCreate) -> DepartmentMember:
        """添加部门成员"""
        try:
            # 检查部门是否存在
            department = await self.get_department_by_id(department_id)
            if not department or not department.is_active:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="部门不存在或未激活"
                )
            
            # 检查用户是否存在
            user = await self._get_user_by_id(member_data.user_id)
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="用户不存在或未激活"
                )
            
            # 检查是否已经是部门成员
            existing_member = await self._get_department_member(department_id, member_data.user_id)
            if existing_member and existing_member.is_active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="用户已经是该部门成员"
                )
            
            # 创建成员关系
            member = DepartmentMember(
                department_id=department_id,
                **member_data.dict()
            )
            self.db.add(member)
            await self.db.commit()
            await self.db.refresh(member)
            
            logger.info(f"部门成员添加成功: 部门{department_id}, 用户{member_data.user_id}")
            return member
            
        except HTTPException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"添加部门成员失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="添加部门成员失败"
            )
    
    async def get_department_statistics(self) -> Dict[str, Any]:
        """获取部门统计信息"""
        try:
            # 总部门数
            total_result = await self.db.execute(
                select(func.count(Department.id))
                .where(Department.status != Department.STATUS_DELETED)
            )
            total_departments = total_result.scalar()
            
            # 活跃部门数
            active_result = await self.db.execute(
                select(func.count(Department.id))
                .where(Department.status == Department.STATUS_ACTIVE)
            )
            active_departments = active_result.scalar()
            
            # 非活跃部门数
            inactive_departments = total_departments - active_departments
            
            # 根部门数
            root_result = await self.db.execute(
                select(func.count(Department.id))
                .where(and_(
                    Department.parent_id.is_(None),
                    Department.status != Department.STATUS_DELETED
                ))
            )
            root_departments = root_result.scalar()
            
            # 总成员数
            members_result = await self.db.execute(
                select(func.count(DepartmentMember.id))
                .where(DepartmentMember.status == DepartmentMember.STATUS_ACTIVE)
            )
            total_members = members_result.scalar()
            
            # 按层级统计部门数
            level_result = await self.db.execute(
                select(Department.level, func.count(Department.id))
                .where(Department.status == Department.STATUS_ACTIVE)
                .group_by(Department.level)
                .order_by(Department.level)
            )
            departments_by_level = {level: count for level, count in level_result.fetchall()}
            
            # 成员数最多的部门（前10）
            top_departments_result = await self.db.execute(
                select(
                    Department.id,
                    Department.name,
                    func.count(DepartmentMember.id).label('member_count')
                )
                .join(DepartmentMember, Department.id == DepartmentMember.department_id, isouter=True)
                .where(and_(
                    Department.status == Department.STATUS_ACTIVE,
                    or_(
                        DepartmentMember.status == DepartmentMember.STATUS_ACTIVE,
                        DepartmentMember.id.is_(None)
                    )
                ))
                .group_by(Department.id, Department.name)
                .order_by(desc('member_count'))
                .limit(10)
            )
            
            top_departments_by_members = [
                {
                    'id': dept_id,
                    'name': dept_name,
                    'member_count': member_count
                }
                for dept_id, dept_name, member_count in top_departments_result.fetchall()
            ]
            
            return {
                'total_departments': total_departments,
                'active_departments': active_departments,
                'inactive_departments': inactive_departments,
                'root_departments': root_departments,
                'total_members': total_members,
                'departments_by_level': departments_by_level,
                'top_departments_by_members': top_departments_by_members
            }
            
        except Exception as e:
            logger.error(f"获取部门统计信息失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="获取部门统计信息失败"
            )
    
    # 私有辅助方法
    async def _check_duplicate_name(self, name: str, parent_id: Optional[int]) -> Optional[Department]:
        """检查同级别下是否有重名部门"""
        query = select(Department).where(
            and_(
                Department.name == name,
                Department.parent_id == parent_id,
                Department.status != Department.STATUS_DELETED
            )
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def _get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_department_member(self, department_id: int, user_id: int) -> Optional[DepartmentMember]:
        """获取部门成员关系"""
        result = await self.db.execute(
            select(DepartmentMember).where(
                and_(
                    DepartmentMember.department_id == department_id,
                    DepartmentMember.user_id == user_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def _would_create_cycle(self, department_id: int, target_parent_id: int) -> bool:
        """检查是否会创建循环引用"""
        # 获取目标父部门的路径
        target_parent = await self.get_department_by_id(target_parent_id)
        if not target_parent:
            return False
        
        # 检查目标父部门的路径中是否包含当前部门ID
        if target_parent.path:
            path_ids = [int(id_str) for id_str in target_parent.path.split('/') if id_str.isdigit()]
            return department_id in path_ids
        
        return False
    
    async def _update_department_hierarchy(self, department: Department) -> None:
        """更新部门层级结构"""
        # 更新当前部门的路径和层级
        await department.update_path(self.db)
        
        # 递归更新所有子部门的路径和层级
        descendants = await department.get_descendants(self.db, include_self=False)
        for desc in descendants:
            await desc.update_path(self.db)
    
    async def _force_delete_department_recursive(self, department: Department) -> None:
        """递归强制删除部门及其子部门"""
        # 删除所有成员关系
        await self.db.execute(
            update(DepartmentMember)
            .where(DepartmentMember.department_id == department.id)
            .values(status=DepartmentMember.STATUS_INACTIVE)
        )
        
        # 递归删除子部门
        for child in department.children:
            if child.is_active:
                await self._force_delete_department_recursive(child)
        
        # 删除当前部门
        department.status = Department.STATUS_DELETED
    
    # 职位管理方法
    async def set_member_position(self, department_id: int, user_id: int, position_type: str, current_user_id: int) -> DepartmentMember:
        """设置成员职位"""
        try:
            from app.models.department import PositionType
            
            # 验证职位类型
            if position_type not in [pos.value for pos in PositionType]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="无效的职位类型"
                )
            
            # 检查部门是否存在
            department = await self.get_department_by_id(department_id)
            if not department:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="部门不存在"
                )
            
            # 检查成员是否存在
            member = await self._get_department_member(department_id, user_id)
            if not member or not member.is_active:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="成员不存在或已离职"
                )
            
            # 检查权限（只有部门负责人或系统管理员可以设置职位）
            current_member = await self._get_department_member(department_id, current_user_id)
            if not (current_member and current_member.is_manager):
                # 这里可以添加系统管理员权限检查
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="无权限设置成员职位"
                )
            
            # 如果设置为部长，检查是否已有部长
            if position_type == PositionType.MANAGER.value:
                existing_manager = await self.db.execute(
                    select(DepartmentMember).where(
                        and_(
                            DepartmentMember.department_id == department_id,
                            DepartmentMember.position_type == PositionType.MANAGER,
                            DepartmentMember.status == DepartmentMember.STATUS_ACTIVE,
                            DepartmentMember.user_id != user_id
                        )
                    )
                )
                if existing_manager.scalar_one_or_none():
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="该部门已有部长，请先移除现有部长"
                    )
            
            # 更新职位
            member.position_type = PositionType(position_type)
            member.update_is_manager_field()
            
            # 如果设置为部长，同步更新部门的manager_id
            if position_type == PositionType.MANAGER.value:
                department.manager_id = user_id
                # 获取用户信息更新manager_name
                user = await self._get_user_by_id(user_id)
                if user:
                    department.manager_name = user.real_name or user.username
            
            await self.db.commit()
            await self.db.refresh(member)
            
            logger.info(f"成员职位设置成功: 部门{department_id}, 用户{user_id}, 职位{position_type}")
            return member
            
        except HTTPException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.error(f"设置成员职位失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="设置成员职位失败"
            )
    
    async def get_department_management(self, department_id: int) -> Dict[str, Any]:
        """获取部门管理层信息"""
        try:
            from app.models.department import PositionType
            
            # 检查部门是否存在
            department = await self.get_department_by_id(department_id)
            if not department:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="部门不存在"
                )
            
            # 获取管理层成员
            result = await self.db.execute(
                select(DepartmentMember, User)
                .join(User, DepartmentMember.user_id == User.id)
                .where(
                    and_(
                        DepartmentMember.department_id == department_id,
                        DepartmentMember.position_type.in_([PositionType.MANAGER, PositionType.DEPUTY_MANAGER]),
                        DepartmentMember.status == DepartmentMember.STATUS_ACTIVE
                    )
                )
                .order_by(DepartmentMember.position_type.desc(), DepartmentMember.joined_at)
            )
            
            management_members = []
            manager = None
            deputy_managers = []
            
            for member, user in result.fetchall():
                member_info = {
                    'id': member.id,
                    'user_id': user.id,
                    'username': user.username,
                    'real_name': user.real_name,
                    'display_name': user.real_name or user.username,
                    'avatar_url': user.avatar_url,
                    'position': member.position,
                    'position_type': member.position_type,
                    'position_display': member.get_position_display(),
                    'joined_at': member.joined_at
                }
                
                if member.position_type == PositionType.MANAGER:
                    manager = member_info
                elif member.position_type == PositionType.DEPUTY_MANAGER:
                    deputy_managers.append(member_info)
                
                management_members.append(member_info)
            
            return {
                'department_id': department_id,
                'department_name': department.name,
                'manager': manager,
                'deputy_managers': deputy_managers,
                'all_management': management_members,
                'statistics': {
                    'manager_count': 1 if manager else 0,
                    'deputy_manager_count': len(deputy_managers),
                    'total_management_count': len(management_members)
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取部门管理层信息失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="获取部门管理层信息失败"
            )
    
    async def get_position_statistics(self, department_id: int, include_children: bool = False) -> Dict[str, Any]:
        """获取职位统计信息"""
        try:
            from app.models.department import PositionType
            
            # 检查部门是否存在
            department = await self.get_department_by_id(department_id)
            if not department:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="部门不存在"
                )
            
            # 构建查询条件
            if include_children:
                # 包含子部门：获取所有后代部门ID
                descendants = await department.get_descendants(self.db, include_self=True)
                department_ids = [dept.id for dept in descendants]
                query_condition = DepartmentMember.department_id.in_(department_ids)
            else:
                # 仅当前部门
                query_condition = DepartmentMember.department_id == department_id
            
            # 按职位类型统计
            result = await self.db.execute(
                select(
                    DepartmentMember.position_type,
                    func.count(DepartmentMember.id).label('count')
                )
                .where(
                    and_(
                        query_condition,
                        DepartmentMember.status == DepartmentMember.STATUS_ACTIVE
                    )
                )
                .group_by(DepartmentMember.position_type)
            )
            
            position_counts = {pos_type: count for pos_type, count in result.fetchall()}
            
            # 计算各职位数量
            manager_count = position_counts.get(PositionType.MANAGER, 0)
            deputy_manager_count = position_counts.get(PositionType.DEPUTY_MANAGER, 0)
            regular_member_count = position_counts.get(PositionType.MEMBER, 0)
            total_members = sum(position_counts.values())
            
            return {
                'department_id': department_id,
                'department_name': department.name,
                'include_children': include_children,
                'total_members': total_members,
                'manager_count': manager_count,
                'deputy_manager_count': deputy_manager_count,
                'regular_member_count': regular_member_count,
                'position_distribution': {
                    'manager_percentage': round(manager_count / total_members * 100, 2) if total_members > 0 else 0,
                    'deputy_manager_percentage': round(deputy_manager_count / total_members * 100, 2) if total_members > 0 else 0,
                    'regular_member_percentage': round(regular_member_count / total_members * 100, 2) if total_members > 0 else 0
                }
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"获取职位统计信息失败: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="获取职位统计信息失败"
            )