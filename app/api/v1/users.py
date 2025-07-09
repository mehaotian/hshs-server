from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import (
    get_current_user, get_current_active_user, 
    require_permission, require_role
)
from app.core.response import ResponseBuilder
from app.core.logger import logger, log_security_event
from app.models.user import User, UserProfile
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserListResponse,
    UserProfileCreate, UserProfileUpdate, UserProfileResponse,
    UserPasswordUpdate, PasswordChange, UserSearchQuery, UserBatchOperation,
    UserStatistics
)
from app.services.user import UserService

router = APIRouter()


# 注意：现在直接使用模型的 to_dict 方法进行序列化
# User 模型使用 to_dict_sync() 方法
# UserProfile 模型使用 to_dict() 方法


@router.post("/add", response_model=UserResponse, summary="创建用户")
async def create_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:create"))
):
    """创建新用户"""
    try:
        user_service = UserService(db)
        user = await user_service.create_user(user_data)
        
        log_security_event(
            "user_created",
            user_id=current_user.id,
            details=f"target_user_id: {user.id}, username: {user.username}, email: {user.email}"
        )
        
        return ResponseBuilder.success(
            data=user.to_dict_sync(),
            message="用户创建成功"
        )
    except Exception as e:
        logger.error(f"Failed to create user: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/profile", response_model=UserResponse, summary="获取当前用户信息")
async def get_current_user(
    current_user: User = Depends(get_current_active_user)
):
    """获取当前登录用户的信息"""
    return ResponseBuilder.success(
        data=current_user.to_dict_sync(),
        message="获取用户信息成功"
    )


@router.put("/update-profile", response_model=UserResponse, summary="更新当前用户信息")
async def update_current_user(
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """更新当前登录用户的信息"""
    try:
        user_service = UserService(db)
        updated_user = await user_service.update_user(current_user.id, user_data)
        
        log_security_event(
            "user_updated",
            user_id=current_user.id,
            details=f"updated_fields: {list(user_data.dict(exclude_unset=True).keys())}"
        )
        
        return ResponseBuilder.success(
            data=updated_user.to_dict_sync(),
            message="用户信息更新成功"
        )
    except Exception as e:
        logger.error(f"Failed to update user: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/change-password", summary="修改当前用户密码")
async def change_password(
    password_data: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """修改当前登录用户的密码"""
    try:
        user_service = UserService(db)
        await user_service.update_password(current_user.id, password_data)
        
        log_security_event(
            "password_changed",
            user_id=current_user.id,
            details="changed_by_self: True"
        )
        
        return ResponseBuilder.success(
            message="密码修改成功"
        )
    except Exception as e:
        logger.error(f"Failed to change password: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/detail/{user_id}", response_model=UserResponse, summary="获取用户信息")
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:read"))
):
    """根据ID获取用户信息"""
    try:
        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        return ResponseBuilder.success(
            data=user.to_dict_sync(),
            message="获取用户信息成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户信息失败")


@router.put("/update/{user_id}", response_model=UserResponse, summary="更新用户信息")
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:update"))
):
    """更新指定用户的信息"""
    try:
        user_service = UserService(db)
        updated_user = await user_service.update_user(user_id, user_data)
        
        log_security_event(
            "user_updated",
            user_id=current_user.id,
            details=f"target_user_id: {user_id}, updated_fields: {list(user_data.dict(exclude_unset=True).keys())}"
        )
        
        return ResponseBuilder.success(
            data=updated_user.to_dict_sync(),
            message="用户信息更新成功"
        )
    except Exception as e:
        logger.error(f"Failed to update user: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/delete/{user_id}", summary="删除用户")
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:delete"))
):
    """删除指定用户"""
    try:
        user_service = UserService(db)
        await user_service.delete_user(user_id)
        
        log_security_event(
            "user_deleted",
            user_id=current_user.id,
            details=f"target_user_id: {user_id}"
        )
        
        return ResponseBuilder.success(
            message="用户删除成功"
        )
    except Exception as e:
        logger.error(f"Failed to delete user: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/list", response_model=UserListResponse, summary="获取用户列表")
async def get_users(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    status: Optional[str] = Query(None, description="用户状态"),
    role_id: Optional[int] = Query(None, description="角色ID"),
    created_after: Optional[str] = Query(None, description="创建时间起始"),
    created_before: Optional[str] = Query(None, description="创建时间结束"),
    sort_by: Optional[str] = Query("created_at", description="排序字段"),
    sort_order: Optional[str] = Query("desc", description="排序方向"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:read"))
):
    """获取用户列表（支持搜索和分页）"""
    try:
        # 构建搜索查询
        search_query = UserSearchQuery(
            keyword=keyword,
            status=status,
            created_after=created_after,
            created_before=created_before,
            order_by=sort_by or "created_at",
            order_desc=sort_order == "desc"
        )
        
        user_service = UserService(db)
        users, total = await user_service.get_users(page, size, search_query)
        
        return ResponseBuilder.paginated(
            data=users,
            total=total,
            page=page,
            size=size,
            message="获取用户列表成功"
        )
    except Exception as e:
        logger.error(f"Failed to get users: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户列表失败")


@router.post("/batch-operation", summary="批量操作用户")
async def batch_operation_users(
    operation: UserBatchOperation,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:update"))
):
    """批量操作用户（激活、禁用、删除）"""
    try:
        user_service = UserService(db)
        result = await user_service.batch_operation(operation)
        
        log_security_event(
            "user_batch_operation",
            user_id=current_user.id,
            details=f"operation: {operation.operation}, user_count: {len(operation.user_ids)}, success_count: {result['success_count']}, failed_count: {result['failed_count']}"
        )
        
        return ResponseBuilder.success(
            data=result,
            message=f"批量操作完成：成功 {result['success_count']} 个，失败 {result['failed_count']} 个"
        )
    except Exception as e:
        logger.error(f"Failed to batch operation users: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/stats", response_model=UserStatistics, summary="获取用户统计信息")
async def get_user_statistics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:read"))
):
    """获取用户统计信息"""
    try:
        user_service = UserService(db)
        statistics = await user_service.get_user_statistics()
        
        return ResponseBuilder.success(
            data=statistics,
            message="获取用户统计信息成功"
        )
    except Exception as e:
        logger.error(f"Failed to get user statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户统计信息失败")


# ==================== 用户档案相关接口 ====================

@router.post("/me/profile", response_model=UserProfileResponse, summary="创建用户档案")
async def create_user_profile(
    profile_data: UserProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """为当前用户创建档案"""
    try:
        user_service = UserService(db)
        profile = await user_service.create_user_profile(current_user.id, profile_data)
        
        return ResponseBuilder.success(
            data=profile.to_dict(),
            message="用户档案创建成功"
        )
    except Exception as e:
        logger.error(f"Failed to create user profile: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/me/profile", response_model=UserProfileResponse, summary="获取用户档案")
async def get_user_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取当前用户的档案"""
    try:
        user_service = UserService(db)
        profile = await user_service.get_user_profile(current_user.id)
        
        if not profile:
            raise HTTPException(status_code=404, detail="用户档案不存在")
        
        return ResponseBuilder.success(
            data=profile.to_dict(),
            message="获取用户档案成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user profile: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户档案失败")


@router.put("/me/profile", response_model=UserProfileResponse, summary="更新用户档案")
async def update_user_profile(
    profile_data: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """更新当前用户的档案"""
    try:
        user_service = UserService(db)
        updated_profile = await user_service.update_user_profile(current_user.id, profile_data)
        
        return ResponseBuilder.success(
            data=updated_profile.to_dict(),
            message="用户档案更新成功"
        )
    except Exception as e:
        logger.error(f"Failed to update user profile: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{user_id}/profile", response_model=UserProfileResponse, summary="获取指定用户档案")
async def get_user_profile_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:read"))
):
    """获取指定用户的档案"""
    try:
        user_service = UserService(db)
        profile = await user_service.get_user_profile(user_id)
        
        if not profile:
            raise HTTPException(status_code=404, detail="用户档案不存在")
        
        return ResponseBuilder.success(
            data=profile.to_dict(),
            message="获取用户档案成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get user profile: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户档案失败")


# ==================== 用户角色和权限查询 ====================

@router.get("/me/roles", summary="获取当前用户角色")
async def get_current_user_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取当前用户的所有角色"""
    try:
        user_service = UserService(db)
        roles = await user_service.get_user_roles(current_user.id)
        
        return ResponseBuilder.success(
            data=roles,
            message="获取用户角色成功"
        )
    except Exception as e:
        logger.error(f"Failed to get user roles: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户角色失败")


@router.get("/me/permissions", summary="获取当前用户权限")
async def get_current_user_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """获取当前用户的所有权限"""
    try:
        user_service = UserService(db)
        permissions = await user_service.get_user_permissions(current_user.id)
        
        return ResponseBuilder.success(
            data=permissions,
            message="获取用户权限成功"
        )
    except Exception as e:
        logger.error(f"Failed to get user permissions: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户权限失败")


@router.get("/{user_id}/roles", summary="获取指定用户角色")
async def get_user_roles_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("user:read"))
):
    """获取指定用户的所有角色"""
    try:
        user_service = UserService(db)
        roles = await user_service.get_user_roles(user_id)
        
        return ResponseBuilder.success(
            data=roles,
            message="获取用户角色成功"
        )
    except Exception as e:
        logger.error(f"Failed to get user roles: {str(e)}")
        raise HTTPException(status_code=500, detail="获取用户角色失败")