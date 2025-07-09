from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, require_permission
from app.core.response import ResponseBuilder
from app.core.logger import logger
from app.models.user import User
from app.schemas.role import (
    RoleCreate, RoleUpdate, RoleResponse, RoleListResponse,
    PermissionCreate, PermissionUpdate, PermissionResponse, PermissionListResponse,
    UserRoleAssignment, UserRoleBatchOperation, RoleSearchQuery,
    PermissionSearchQuery, RoleStatistics
)
from app.services.role import RoleService

router = APIRouter()


# ==================== 角色管理 ====================

@router.post("/add", response_model=RoleResponse, summary="创建角色")
async def create_role(
    role_data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("role:create"))
):
    """创建新角色"""
    try:
        role_service = RoleService(db)
        role = await role_service.create_role(role_data)
        
        logger.log_security_event(
            "role_created",
            user_id=current_user.id,
            details={"role_name": role.name, "role_id": role.id}
        )
        
        return ResponseBuilder.success(
            data=role,
            message="角色创建成功"
        )
    except Exception as e:
        logger.error(f"Failed to create role: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/detail/{role_id}", response_model=RoleResponse, summary="获取角色信息")
async def get_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("role:read"))
):
    """根据ID获取角色信息"""
    try:
        role_service = RoleService(db)
        role = await role_service.get_role_by_id(role_id)
        
        if not role:
            raise HTTPException(status_code=404, detail="角色不存在")
        
        return ResponseBuilder.success(
            data=role,
            message="获取角色信息成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get role: {str(e)}")
        raise HTTPException(status_code=500, detail="获取角色信息失败")


@router.put("/update/{role_id}", response_model=RoleResponse, summary="更新角色信息")
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("role:update"))
):
    """更新角色信息"""
    try:
        role_service = RoleService(db)
        updated_role = await role_service.update_role(role_id, role_data)
        
        logger.log_security_event(
            "role_updated",
            user_id=current_user.id,
            details={
                "role_id": role_id,
                "updated_fields": list(role_data.dict(exclude_unset=True).keys())
            }
        )
        
        return ResponseBuilder.success(
            data=updated_role,
            message="角色信息更新成功"
        )
    except Exception as e:
        logger.error(f"Failed to update role: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/delete/{role_id}", summary="删除角色")
async def delete_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("role:delete"))
):
    """删除角色"""
    try:
        role_service = RoleService(db)
        await role_service.delete_role(role_id)
        
        logger.log_security_event(
            "role_deleted",
            user_id=current_user.id,
            details={"role_id": role_id}
        )
        
        return ResponseBuilder.success(
            message="角色删除成功"
        )
    except Exception as e:
        logger.error(f"Failed to delete role: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/list", response_model=RoleListResponse, summary="获取角色列表")
async def get_roles(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    is_active: Optional[bool] = Query(None, description="是否激活"),
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", description="排序方向"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("role:read"))
):
    """获取角色列表（支持搜索和分页）"""
    try:
        # 构建搜索查询
        search_query = RoleSearchQuery(
            keyword=keyword,
            is_active=is_active,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        role_service = RoleService(db)
        roles, total = await role_service.get_roles(page, size, search_query)
        
        return ResponseBuilder.paginated(
            data=roles,
            total=total,
            page=page,
            size=size,
            message="获取角色列表成功"
        )
    except Exception as e:
        logger.error(f"Failed to get roles: {str(e)}")
        raise HTTPException(status_code=500, detail="获取角色列表失败")


@router.get("/stat/overview", response_model=RoleStatistics, summary="获取角色统计信息")
async def get_role_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("role:read"))
):
    """获取角色统计信息"""
    try:
        role_service = RoleService(db)
        statistics = await role_service.get_role_statistics()
        
        return ResponseBuilder.success(
            data=statistics,
            message="获取角色统计信息成功"
        )
    except Exception as e:
        logger.error(f"Failed to get role statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="获取角色统计信息失败")


# ==================== 权限管理 ====================

@router.post("/permissions/add", response_model=PermissionResponse, summary="创建权限")
async def create_permission(
    permission_data: PermissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("permission:create"))
):
    """创建新权限"""
    try:
        role_service = RoleService(db)
        permission = await role_service.create_permission(permission_data)
        
        logger.log_security_event(
            "permission_created",
            user_id=current_user.id,
            details={"permission_name": permission.name, "permission_id": permission.id}
        )
        
        return ResponseBuilder.success(
            data=permission,
            message="权限创建成功"
        )
    except Exception as e:
        logger.error(f"Failed to create permission: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/permissions/detail/{permission_id}", response_model=PermissionResponse, summary="获取权限信息")
async def get_permission(
    permission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("permission:read"))
):
    """根据ID获取权限信息"""
    try:
        role_service = RoleService(db)
        permission = await role_service.get_permission_by_id(permission_id)
        
        if not permission:
            raise HTTPException(status_code=404, detail="权限不存在")
        
        return ResponseBuilder.success(
            data=permission,
            message="获取权限信息成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get permission: {str(e)}")
        raise HTTPException(status_code=500, detail="获取权限信息失败")


@router.put("/permissions/update/{permission_id}", response_model=PermissionResponse, summary="更新权限信息")
async def update_permission(
    permission_id: int,
    permission_data: PermissionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("permission:update"))
):
    """更新权限信息"""
    try:
        role_service = RoleService(db)
        updated_permission = await role_service.update_permission(permission_id, permission_data)
        
        logger.log_security_event(
            "permission_updated",
            user_id=current_user.id,
            details={
                "permission_id": permission_id,
                "updated_fields": list(permission_data.dict(exclude_unset=True).keys())
            }
        )
        
        return ResponseBuilder.success(
            data=updated_permission,
            message="权限信息更新成功"
        )
    except Exception as e:
        logger.error(f"Failed to update permission: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/permissions/delete/{permission_id}", summary="删除权限")
async def delete_permission(
    permission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("permission:delete"))
):
    """删除权限"""
    try:
        role_service = RoleService(db)
        await role_service.delete_permission(permission_id)
        
        logger.log_security_event(
            "permission_deleted",
            user_id=current_user.id,
            details={"permission_id": permission_id}
        )
        
        return ResponseBuilder.success(
            message="权限删除成功"
        )
    except Exception as e:
        logger.error(f"Failed to delete permission: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/permissions/list", response_model=PermissionListResponse, summary="获取权限列表")
async def get_permissions(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    category: Optional[str] = Query(None, description="权限分类"),
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", description="排序方向"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("permission:read"))
):
    """获取权限列表（支持搜索和分页）"""
    try:
        # 构建搜索查询
        search_query = PermissionSearchQuery(
            keyword=keyword,
            category=category,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        role_service = RoleService(db)
        permissions, total = await role_service.get_permissions(page, size, search_query)
        
        return ResponseBuilder.paginated(
            data=permissions,
            total=total,
            page=page,
            size=size,
            message="获取权限列表成功"
        )
    except Exception as e:
        logger.error(f"Failed to get permissions: {str(e)}")
        raise HTTPException(status_code=500, detail="获取权限列表失败")


# ==================== 用户角色分配 ====================

@router.post("/user/assign", summary="分配角色给用户")
async def assign_role_to_user(
    assignment: UserRoleAssignment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("role:assign"))
):
    """为用户分配角色"""
    try:
        role_service = RoleService(db)
        await role_service.assign_role_to_user(assignment.user_id, assignment.role_id)
        
        logger.log_security_event(
            "role_assigned",
            user_id=current_user.id,
            target_user_id=assignment.user_id,
            details={"role_id": assignment.role_id}
        )
        
        return ResponseBuilder.success(
            message="角色分配成功"
        )
    except Exception as e:
        logger.error(f"Failed to assign role: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/user/unassign", summary="移除用户角色")
async def remove_role_from_user(
    assignment: UserRoleAssignment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("role:assign"))
):
    """移除用户的角色"""
    try:
        role_service = RoleService(db)
        await role_service.remove_role_from_user(assignment.user_id, assignment.role_id)
        
        logger.log_security_event(
            "role_removed",
            user_id=current_user.id,
            target_user_id=assignment.user_id,
            details={"role_id": assignment.role_id}
        )
        
        return ResponseBuilder.success(
            message="角色移除成功"
        )
    except Exception as e:
        logger.error(f"Failed to remove role: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/user/batch-assign", summary="批量分配角色")
async def batch_assign_roles(
    operation: UserRoleBatchOperation,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("role:assign"))
):
    """批量为用户分配或移除角色"""
    try:
        role_service = RoleService(db)
        result = await role_service.batch_assign_roles(operation)
        
        logger.log_security_event(
            "role_batch_operation",
            user_id=current_user.id,
            details={
                "operation": operation.operation,
                "user_count": len(operation.user_ids),
                "role_count": len(operation.role_ids),
                "success_count": result["success_count"],
                "failed_count": result["failed_count"]
            }
        )
        
        return ResponseBuilder.success(
            data=result,
            message=f"批量操作完成：成功 {result['success_count']} 个，失败 {result['failed_count']} 个"
        )
    except Exception as e:
        logger.error(f"Failed to batch assign roles: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/user/{user_id}/roles", summary="获取用户角色")
async def get_user_roles(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("role:read"))
):
    """获取指定用户的所有角色"""
    try:
        role_service = RoleService(db)
        roles = await role_service.get_user_roles(user_id)
        
        return ResponseBuilder.success(
            data=roles,
            message="获取用户角色成功"
        )
    except Exception as e:
        logger.error(f"Failed to get user roles: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户角色失败")


@router.get("/users/{role_id}", summary="获取拥有角色的用户")
async def get_role_users(
    role_id: int,
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("role:read"))
):
    """获取拥有指定角色的所有用户"""
    try:
        role_service = RoleService(db)
        users, total = await role_service.get_role_users(role_id, page, size)
        
        return ResponseBuilder.paginated(
            data=users,
            total=total,
            page=page,
            size=size,
            message="获取角色用户成功"
        )
    except Exception as e:
        logger.error(f"Failed to get role users: {str(e)}")
        raise HTTPException(status_code=500, detail="获取角色用户失败")


# ==================== 权限检查 ====================

@router.get("/user/{user_id}/permissions", summary="获取用户权限")
async def get_user_permissions(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("permission:read"))
):
    """获取指定用户的所有权限"""
    try:
        role_service = RoleService(db)
        permissions = await role_service.get_user_permissions(user_id)
        
        return ResponseBuilder.success(
            data=permissions,
            message="获取用户权限成功"
        )
    except Exception as e:
        logger.error(f"Failed to get user permissions: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户权限失败")


@router.post("/permission/check", summary="检查用户权限")
async def check_user_permission(
    user_id: int = Query(..., description="用户ID"),
    permission: str = Query(..., description="权限名称"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("permission:read"))
):
    """检查用户是否拥有指定权限"""
    try:
        role_service = RoleService(db)
        has_permission = await role_service.check_user_permission(user_id, permission)
        
        return ResponseBuilder.success(
            data={"has_permission": has_permission},
            message="权限检查完成"
        )
    except Exception as e:
        logger.error(f"Failed to check user permission: {str(e)}")
        raise HTTPException(status_code=500, detail="权限检查失败")


# ==================== 系统初始化 ====================

@router.post("/system/init", summary="初始化系统角色和权限")
async def init_system_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("system:init"))
):
    """初始化系统默认角色和权限"""
    try:
        role_service = RoleService(db)
        result = await role_service.init_system_roles()
        
        logger.log_security_event(
            "system_roles_initialized",
            user_id=current_user.id,
            details=result
        )
        
        return ResponseBuilder.success(
            data=result,
            message="系统角色和权限初始化成功"
        )
    except Exception as e:
        logger.error(f"Failed to init system roles: {str(e)}")
        raise HTTPException(status_code=500, detail="系统初始化失败")