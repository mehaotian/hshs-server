from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.auth import require_permission
from app.models.user import User
from app.models.department import Department
from app.services.department import DepartmentService
from app.schemas.department import (
    DepartmentCreate, DepartmentUpdate, DepartmentResponse,
    DepartmentTreeResponse, DepartmentQuery, DepartmentQueryExtended, DepartmentStatistics,
    DepartmentBatchOperation, DepartmentMove,
    DepartmentMemberCreate, DepartmentMemberUpdate, DepartmentMemberResponse,
    PositionChangeRequest, DepartmentManagerInfo, PositionStatistics, DepartmentTreeSimple
)
from app.core.response import ResponseBuilder
from app.core.logger import logger

router = APIRouter(prefix="/departments", tags=["部门管理"])


@router.post("/add", summary="创建部门")
async def create_department(
    department_data: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("department:create"))
):
    """创建部门"""

    try:
        service = DepartmentService(db)
        department = await service.create_department(department_data, current_user.id)

        # 转换为响应格式
        department_dict = await department.to_dict(db)

        return ResponseBuilder.success(
            data=department_dict,
            message="部门创建成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建部门失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建部门失败"
        )


@router.get("/list", summary="获取部门列表")
async def get_departments(
    name: Optional[str] = Query(None, description="部门名称（模糊搜索）"),
    parent_id: Optional[int] = Query(None, description="上级部门ID"),
    manager_id: Optional[int] = Query(None, description="负责人ID"),
    status: Optional[int] = Query(None, description="部门状态"),
    level: Optional[int] = Query(None, description="部门层级"),
    include_children: bool = Query(False, description="是否包含子部门"),
    include_members: bool = Query(False, description="是否包含成员信息"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("department:read"))
):
    """获取部门列表"""

    try:
        query_params = DepartmentQueryExtended(
            name=name,
            parent_id=parent_id,
            manager_id=manager_id,
            status=status,
            level=level,
            include_children=include_children,
            include_members=include_members,
            page=page,
            page_size=page_size
        )

        service = DepartmentService(db)
        departments, total = await service.get_departments(query_params)

        # 转换为响应格式
        department_list = []
        for dept in departments:
            dept_dict = await dept.to_dict(db, include_children, include_members)
            department_list.append(dept_dict)

        return ResponseBuilder.paginated(
            data=department_list,
            page=page,
            size=page_size,
            total=total,
            message="获取部门列表成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取部门列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取部门列表失败"
        )


async def convert_to_simple_tree(dept, db) -> DepartmentTreeSimple:
    """将部门对象转换为精简的树形结构"""
    # 获取成员数量
    member_count = await dept.get_member_count(db)
    
    # 获取子部门并递归转换
    from sqlalchemy import select
    from app.models.department import Department
    
    result = await db.execute(
        select(Department)
        .where(Department.parent_id == dept.id)
        .where(Department.status == Department.STATUS_ACTIVE)
        .order_by(Department.sort_order)
    )
    children_depts = result.scalars().all()
    
    children = []
    for child in children_depts:
        child_simple = await convert_to_simple_tree(child, db)
        children.append(child_simple)
    
    return DepartmentTreeSimple(
        id=dept.id,
        name=dept.name,
        parent_id=dept.parent_id if dept.parent_id is not None else 0,  # 根节点返回0而不是null
        level=dept.level,
        sort_order=dept.sort_order,
        member_count=member_count,
        children=children
    )


@router.get("/tree/list", summary="获取部门树形结构")
async def get_department_tree(
    root_id: Optional[int] = Query(None, description="根部门ID，不传则获取所有根部门"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """获取部门树（精简版，仅包含渲染必需字段）"""
    try:
        service = DepartmentService(db)
        departments = await service.get_department_tree(root_id)
        result = []
        for dept in departments:
            # 转换为精简的树形结构
            simple_tree = await convert_to_simple_tree(dept, db)
            result.append(simple_tree.model_dump())
        
        return ResponseBuilder.success(
            data=result,
            message="获取部门树成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取部门树失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取部门树失败"
        )


@router.get("/statistics/list", summary="获取部门统计信息")
async def get_department_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("department:read"))
):
    """获取部门统计信息"""

    try:
        service = DepartmentService(db)
        statistics = await service.get_department_statistics()

        return ResponseBuilder.success(
            data=statistics,
            message="获取部门统计信息成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取部门统计信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取部门统计信息失败"
        )


@router.get("/detail/{department_id}", summary="获取部门详情")
async def get_department(
    department_id: int,
    include_children: bool = Query(False, description="是否包含子部门"),
    include_members: bool = Query(False, description="是否包含成员信息"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("department:read"))
):
    """获取指定部门详情"""

    try:
        service = DepartmentService(db)
        department = await service.get_department_by_id(
            department_id,
            include_children=include_children,
            include_members=include_members
        )

        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="部门不存在"
            )

        # 转换为响应格式
        department_dict = await department.to_dict(db, include_children, include_members)

        return ResponseBuilder.success(
            data=department_dict,
            message="获取部门详情成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取部门详情失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取部门详情失败"
        )


@router.put("/update/{department_id}", summary="更新部门信息")
async def update_department(
    department_id: int,
    update_data: DepartmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("department:update"))
):
    """更新部门信息"""

    try:
        service = DepartmentService(db)
        department = await service.update_department(department_id, update_data)

        # 转换为响应格式
        department_dict = await department.to_dict(db)

        return ResponseBuilder.success(
            data=department_dict,
            message="部门更新成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新部门失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新部门失败"
        )


@router.delete("/delete/{department_id}", summary="删除部门")
async def delete_department(
    department_id: int,
    force: bool = Query(False, description="是否强制删除（包括子部门和成员）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("department:delete"))
):
    """删除部门"""

    try:
        service = DepartmentService(db)
        success = await service.delete_department(department_id, force)

        return ResponseBuilder.success(
            message="部门删除成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除部门失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除部门失败"
        )


@router.post("/batch/operation", summary="批量操作部门")
async def batch_operation_departments(
    operation_data: DepartmentBatchOperation,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """批量操作部门"""
    # 检查权限
    from app.core.auth import AuthManager
    permission_map = {
        'activate': 'department:update',
        'deactivate': 'department:update',
        'delete': 'department:delete'
    }

    required_permission = permission_map.get(operation_data.operation)
    if required_permission:
        await AuthManager.check_permission(current_user, required_permission, db)

    try:
        service = DepartmentService(db)
        results = await service.batch_operation(operation_data)

        return ResponseBuilder.success(
            data=results,
            message="批量操作完成"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量操作失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="批量操作失败"
        )


@router.post("/move/{department_id}", summary="移动部门")
async def move_department(
    department_id: int,
    move_data: DepartmentMove,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("department:update"))
):
    """移动部门"""

    try:
        service = DepartmentService(db)
        department = await service.move_department(department_id, move_data)

        # 转换为响应格式
        department_dict = await department.to_dict(db)

        return ResponseBuilder.success(
            data=department_dict,
            message="部门移动成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"移动部门失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="移动部门失败"
        )


# 部门成员管理接口
@router.post("/members/add/{department_id}", summary="添加部门成员")
async def add_department_member(
    department_id: int,
    member_data: DepartmentMemberCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("department:update"))
):
    """添加部门成员"""

    try:
        service = DepartmentService(db)
        member = await service.add_department_member(department_id, member_data)
        
        # 转换为响应格式
        member_dict = {
            'id': member.id,
            'department_id': member.department_id,
            'user_id': member.user_id,
            'position': member.position,
            'is_manager': member.is_manager,
            'position_type': member.position_type if hasattr(member, 'position_type') else None,
            'position_display': member.get_position_display() if hasattr(member, 'get_position_display') else None,
            'status': member.status,
            'joined_at': member.joined_at,
            'left_at': member.left_at,
            'remarks': member.remarks,
            'created_at': member.created_at,
            'updated_at': member.updated_at,
            'is_active': member.is_active
        }

        return ResponseBuilder.success(
            data=member_dict,
            message="部门成员添加成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加部门成员失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="添加部门成员失败"
        )


@router.get("/members/list/{department_id}", summary="获取部门成员列表")
async def get_department_members(
    department_id: int,
    status: Optional[int] = Query(None, description="成员状态"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("department:read"))
):
    """获取部门成员列表"""

    try:
        service = DepartmentService(db)
        department = await service.get_department_by_id(department_id, include_members=True)

        if not department:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="部门不存在"
            )

        # 过滤成员
        members = department.members
        if status is not None:
            members = [m for m in members if m.status == status]

        # 转换为响应格式
        member_list = []
        for member in members:
            member_dict = {
                'id': member.id,
                'department_id': member.department_id,
                'user_id': member.user_id,
                'position': member.position,
                'is_manager': member.is_manager,
                'position_type': member.position_type if hasattr(member, 'position_type') else None,
                'position_display': member.get_position_display() if hasattr(member, 'get_position_display') else None,
                'status': member.status,
                'joined_at': member.joined_at,
                'left_at': member.left_at,
                'remarks': member.remarks,
                'created_at': member.created_at,
                'updated_at': member.updated_at,
                'is_active': member.is_active
            }

            # 添加用户信息
            if member.user:
                member_dict['user'] = {
                    'id': member.user.id,
                    'username': member.user.username,
                    'real_name': member.user.real_name,
                    'display_name': member.user.display_name,
                    'avatar_url': member.user.avatar_url
                }

            member_list.append(member_dict)
        
        # 按职位类型排序：部长 > 副部长 > 普通成员
        from app.models.department import PositionType
        def sort_key(member):
            pos_type = member.get('position_type')
            if pos_type == PositionType.MANAGER:
                return 0
            elif pos_type == PositionType.DEPUTY_MANAGER:
                return 1
            else:
                return 2
        
        member_list.sort(key=sort_key)

        return ResponseBuilder.success(
            data=member_list,
            message="获取部门成员列表成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取部门成员列表失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取部门成员列表失败"
        )


@router.put("/members/update/{department_id}/{member_id}", summary="更新部门成员信息")
async def update_department_member(
    department_id: int,
    member_id: int,
    update_data: DepartmentMemberUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("department:update"))
):
    """更新部门成员信息"""

    try:
        # 获取成员记录
        from sqlalchemy import select, and_
        from app.models.department import DepartmentMember

        result = await db.execute(
            select(DepartmentMember).where(
                and_(
                    DepartmentMember.id == member_id,
                    DepartmentMember.department_id == department_id
                )
            )
        )
        member = result.scalar_one_or_none()

        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="部门成员不存在"
            )

        # 更新字段
        update_dict = update_data.dict(exclude_unset=True)
        for field, value in update_dict.items():
            setattr(member, field, value)
        
        # 如果更新了position_type，需要同步更新is_manager字段
        if hasattr(member, 'position_type') and hasattr(member, 'update_is_manager_field'):
            member.update_is_manager_field()

        await db.commit()
        await db.refresh(member)

        # 转换为响应格式
        member_dict = {
            'id': member.id,
            'department_id': member.department_id,
            'user_id': member.user_id,
            'position': member.position,
            'is_manager': member.is_manager,
            'position_type': member.position_type if hasattr(member, 'position_type') else None,
            'position_display': member.get_position_display() if hasattr(member, 'get_position_display') else None,
            'status': member.status,
            'joined_at': member.joined_at,
            'left_at': member.left_at,
            'remarks': member.remarks,
            'created_at': member.created_at,
            'updated_at': member.updated_at,
            'is_active': member.is_active
        }

        return ResponseBuilder.success(
            data=member_dict,
            message="部门成员更新成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"更新部门成员失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新部门成员失败"
        )


@router.delete("/members/remove/{department_id}/{member_id}", summary="移除部门成员")
async def remove_department_member(
    department_id: int,
    member_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("department:update"))
):
    """移除部门成员"""

    try:
        # 获取成员记录
        from sqlalchemy import select, and_
        from app.models.department import DepartmentMember

        result = await db.execute(
            select(DepartmentMember).where(
                and_(
                    DepartmentMember.id == member_id,
                    DepartmentMember.department_id == department_id
                )
            )
        )
        member = result.scalar_one_or_none()

        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="部门成员不存在"
            )

        # 软删除（设置为非活跃状态）
        member.status = DepartmentMember.STATUS_INACTIVE
        member.left_at = datetime.utcnow()

        await db.commit()

        return ResponseBuilder.success(
            data={'success': True},
            message="部门成员移除成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"移除部门成员失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="移除部门成员失败"
        )


# 职位管理相关接口
@router.put("/members/position/{department_id}/{user_id}", summary="设置成员职位")
async def set_member_position(
    department_id: int,
    user_id: int,
    position_request: PositionChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("department:update"))
):
    """设置成员职位（部长/副部长/普通成员）"""
    
    try:
        service = DepartmentService(db)
        member = await service.set_member_position(
            department_id=department_id,
            user_id=user_id,
            position_type=position_request.position_type.value,
            current_user_id=current_user.id
        )
        
        # 转换为响应格式
        member_dict = {
            'id': member.id,
            'department_id': member.department_id,
            'user_id': member.user_id,
            'position': member.position,
            'is_manager': member.is_manager,
            'position_type': member.position_type,
            'position_display': member.get_position_display(),
            'status': member.status,
            'joined_at': member.joined_at,
            'updated_at': member.updated_at
        }
        
        return ResponseBuilder.success(
            data=member_dict,
            message=f"成员职位设置成功：{member.get_position_display()}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置成员职位失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="设置成员职位失败"
        )


@router.get("/management/{department_id}", summary="获取部门管理层信息")
async def get_department_management(
    department_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("department:read"))
):
    """获取部门管理层信息（部长和副部长）"""
    
    try:
        service = DepartmentService(db)
        management_info = await service.get_department_management(department_id)
        
        return ResponseBuilder.success(
            data=management_info,
            message="获取部门管理层信息成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取部门管理层信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取部门管理层信息失败"
        )


@router.get("/position-statistics/{department_id}", summary="获取职位统计信息")
async def get_position_statistics(
    department_id: int,
    include_children: bool = Query(False, description="是否包含子部门"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("department:read"))
):
    """获取部门职位统计信息"""
    
    try:
        service = DepartmentService(db)
        statistics = await service.get_position_statistics(
            department_id=department_id,
            include_children=include_children
        )
        
        return ResponseBuilder.success(
            data=statistics,
            message="获取职位统计信息成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取职位统计信息失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取职位统计信息失败"
        )


@router.post("/set-manager/{department_id}/{user_id}", summary="设置部长")
async def set_department_manager(
    department_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("department:update"))
):
    """设置部门部长（快捷接口）"""
    
    try:
        from app.models.department import PositionType
        
        service = DepartmentService(db)
        member = await service.set_member_position(
            department_id=department_id,
            user_id=user_id,
            position_type=PositionType.MANAGER.value,
            current_user_id=current_user.id
        )
        
        return ResponseBuilder.success(
            data={'success': True, 'manager_id': user_id},
            message="部长设置成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"设置部长失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="设置部长失败"
        )


@router.post("/add-deputy-manager/{department_id}/{user_id}", summary="添加副部长")
async def add_deputy_manager(
    department_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("department:update"))
):
    """添加副部长（快捷接口）"""
    
    try:
        from app.models.department import PositionType
        
        service = DepartmentService(db)
        member = await service.set_member_position(
            department_id=department_id,
            user_id=user_id,
            position_type=PositionType.DEPUTY_MANAGER.value,
            current_user_id=current_user.id
        )
        
        return ResponseBuilder.success(
            data={'success': True, 'deputy_manager_id': user_id},
            message="副部长添加成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加副部长失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="添加副部长失败"
        )


@router.delete("/remove-deputy-manager/{department_id}/{user_id}", summary="移除副部长")
async def remove_deputy_manager(
    department_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("department:update"))
):
    """移除副部长（设置为普通成员）"""
    
    try:
        from app.models.department import PositionType
        
        service = DepartmentService(db)
        member = await service.set_member_position(
            department_id=department_id,
            user_id=user_id,
            position_type=PositionType.MEMBER.value,
            current_user_id=current_user.id
        )
        
        return ResponseBuilder.success(
            data={'success': True},
            message="副部长移除成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"移除副部长失败: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="移除副部长失败"
        )
