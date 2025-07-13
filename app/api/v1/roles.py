from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, require_permission
from app.core.response import ResponseBuilder
from app.core.logger import logger, log_security_event
from app.models.user import User
from app.core.exceptions import (
    raise_business_error, raise_not_found_resource, raise_server_error, BaseCustomException, ValidationError
)
from ...schemas.role import (
    RoleCreate, RoleUpdate, RoleResponse, RoleListResponse,
    PermissionCreate, PermissionUpdate, PermissionResponse, PermissionListResponse,
    UserRoleAssignment, UserRoleRemoval, RoleAssignmentBatch,
    RoleSearchQuery, PermissionSearchQuery, RoleStatistics, PermissionSimple,
    RoleStatusUpdate, RolePermissionBatch, RolePermissionSync
)
from app.services.role import RoleService

router = APIRouter()


# ==================== 角色管理 ====================

@router.post("/add", response_model=RoleResponse, summary="创建角色")
async def create_role(
    role_input: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("role:create"))
):
    """创建新角色"""
    from app.core.exceptions import BaseCustomException
    from pydantic import ValidationError as PydanticValidationError

    try:
        # 在 Pydantic 验证失败时，先检查是否是重复名称问题
        role_service = RoleService(db)
        
        # 检查角色名是否已存在
        existing_role = await role_service.get_role_by_name(role_input.name)
        if existing_role:
            from app.core.exceptions import raise_duplicate
            raise_duplicate("Role", "name", role_input.name)
        
        role = await role_service.create_role(role_input)

        log_security_event(
            "role_created",
            user_id=current_user.id,
            details=f"role_name: {role.name}, role_id: {role.id}"
        )

        # 在数据库会话仍然活跃时获取角色数据，避免访问关系属性
        role_data = {
            'id': role.id,
            'name': role.name,
            'display_name': role.display_name,
            'description': role.description,
            'permissions': [],  # 暂时返回空数组，避免关系查询
            'is_system': bool(role.is_system),
            'is_active': bool(role.is_active),
            'sort_order': role.sort_order,
            'user_count': 0,  # 默认值，可以后续优化为实际查询
            'created_at': role.created_at.isoformat() if role.created_at else None,
            'updated_at': role.updated_at.isoformat() if role.updated_at else None,
        }
        
        # 如果有权限ID，手动查询权限名称
        if role_input.permission_ids:
            from sqlalchemy import select
            from app.models.role import Permission
            permission_result = await db.execute(
                select(Permission.name).where(Permission.id.in_(role_input.permission_ids))
            )
            role_data['permissions'] = [name for name, in permission_result.fetchall()]
        
        return ResponseBuilder.success(
            data=role_data,
            message="角色创建成功"
        )
    except ValidationError as e:
        # 捕获验证错误并返回具体的中文错误信息
        logger.error(f"Validation error in create role: {str(e)}")
        raise_business_error(str(e), 1001)
    except BaseCustomException:
        # 让自定义异常传播到全局异常处理器
        raise
    except Exception as e:
        logger.error(f"Failed to create role: {str(e)}")
        
        # 检查是否是特定类型的错误并返回更具体的中文错误信息
        error_msg = str(e)
        if "invalid keyword argument" in error_msg:
            # 提取无效字段名
            import re
            match = re.search(r"'(\w+)' is an invalid keyword argument", error_msg)
            if match:
                field_name = match.group(1)
                raise_business_error(f"无效的字段: {field_name}", 1002)
            else:
                raise_business_error("请求包含无效字段", 1002)
        elif "required" in error_msg.lower():
            raise_business_error("缺少必填字段", 1003)
        elif "constraint" in error_msg.lower() or "unique" in error_msg.lower():
            raise_business_error("数据约束违反，可能存在重复数据", 1004)
        elif "foreign key" in error_msg.lower():
            raise_business_error("关联数据不存在", 1005)
        else:
            raise_business_error("创建角色失败", 1000)


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
            raise_not_found_resource("角色")

        # 在数据库会话仍然活跃时获取角色数据，避免访问关系属性
        role_data = {
            'id': role.id,
            'name': role.name,
            'display_name': role.display_name,
            'description': role.description,
            'permissions': [],  # 暂时返回空数组，避免关系查询
            'is_system': bool(role.is_system),
            'is_active': bool(role.is_active),
            'sort_order': role.sort_order,
            'user_count': 0,  # 默认值，可以后续优化为实际查询
            'created_at': role.created_at.isoformat() if role.created_at else None,
            'updated_at': role.updated_at.isoformat() if role.updated_at else None,
        }
        
        # 手动查询权限信息并展开通配符权限
        from sqlalchemy import select
        from app.models.role import RolePermission, Permission, SYSTEM_PERMISSIONS
        
        # 查询角色的原始权限
        permission_query = (
            select(Permission.id, Permission.name, Permission.display_name)
            .join(RolePermission, Permission.id == RolePermission.permission_id)
            .where(RolePermission.role_id == role.id)
        )
        permission_result = await db.execute(permission_query)
        raw_permissions = permission_result.fetchall()
        
        # 查询所有权限记录，用于获取真实的权限ID
        all_permissions_query = select(Permission.id, Permission.name, Permission.display_name)
        all_permissions_result = await db.execute(all_permissions_query)
        all_permissions = {perm.name: {"id": perm.id, "display_name": perm.display_name} for perm in all_permissions_result.fetchall()}
        
        # 展开通配符权限
        expanded_permission_names = set()
        for perm in raw_permissions:
            permission_name = perm.name
            if permission_name == '*':
                # 全部权限
                expanded_permission_names.update(SYSTEM_PERMISSIONS.keys())
            elif permission_name.endswith(':*'):
                # 模块下的所有权限
                module = permission_name[:-2]
                for sys_perm in SYSTEM_PERMISSIONS.keys():
                    if sys_perm.startswith(f"{module}:"):
                        expanded_permission_names.add(sys_perm)
            elif permission_name.startswith('*:'):
                # 所有模块的特定操作
                action = permission_name[2:]
                for sys_perm in SYSTEM_PERMISSIONS.keys():
                    if sys_perm.endswith(f":{action}"):
                        expanded_permission_names.add(sys_perm)
            else:
                # 具体权限
                expanded_permission_names.add(permission_name)
        
        # 构建权限响应数据，使用数据库中的真实ID
        permissions_data = []
        for perm_name in sorted(expanded_permission_names):
            if perm_name in all_permissions:
                permissions_data.append({
                    "id": all_permissions[perm_name]["id"],  # 使用数据库中的真实ID
                    "name": perm_name,
                    "display_name": all_permissions[perm_name]["display_name"] or SYSTEM_PERMISSIONS.get(perm_name, perm_name)
                })
            elif perm_name in SYSTEM_PERMISSIONS:
                # 如果数据库中没有该权限记录，但在系统权限定义中存在，则跳过或记录警告
                logger.warning(f"Permission '{perm_name}' exists in SYSTEM_PERMISSIONS but not in database")
                continue
        
        role_data['permissions'] = permissions_data

        return ResponseBuilder.success(
            data=role_data,
            message="获取角色信息成功"
        )
    except BaseCustomException:
        raise
    except Exception as e:
        logger.error(f"Failed to get role: {str(e)}")
        raise_business_error("获取角色信息失败", 1000)


@router.put("/update/{role_id}", response_model=RoleResponse, summary="更新角色信息")
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("role:update"))
):
    """更新角色信息"""
    from app.core.exceptions import BaseCustomException

    try:
        role_service = RoleService(db)
        
        # 如果要更新名称，检查角色名是否重复
        if role_data.name:
            current_role = await role_service.get_role_by_id(role_id)
            if current_role and role_data.name != current_role.name:
                existing_role = await role_service.get_role_by_name(role_data.name)
                if existing_role:
                    from app.core.exceptions import raise_duplicate
                    raise_duplicate("Role", "name", role_data.name)
        
        updated_role = await role_service.update_role(role_id, role_data)

        log_security_event(
            "role_updated",
            user_id=current_user.id,
            details=f"role_id: {role_id}, updated_fields: {list(role_data.dict(exclude_unset=True).keys())}"
        )

        # 在数据库会话仍然活跃时获取角色数据，避免访问关系属性
        role_data = {
            'id': updated_role.id,
            'name': updated_role.name,
            'display_name': updated_role.display_name,
            'description': updated_role.description,
            'permissions': [],  # 暂时返回空数组，避免关系查询
            'is_system': bool(updated_role.is_system),
            'is_active': bool(updated_role.is_active),
            'sort_order': updated_role.sort_order,
            'user_count': 0,  # 默认值，可以后续优化为实际查询
            'created_at': updated_role.created_at.isoformat() if updated_role.created_at else None,
            'updated_at': updated_role.updated_at.isoformat() if updated_role.updated_at else None,
        }
        
        # 手动查询权限信息并展开通配符权限
        from sqlalchemy import select
        from app.models.role import RolePermission, Permission, SYSTEM_PERMISSIONS
        
        # 查询角色的原始权限
        permission_query = (
            select(Permission.id, Permission.name, Permission.display_name)
            .join(RolePermission, Permission.id == RolePermission.permission_id)
            .where(RolePermission.role_id == updated_role.id)
        )
        permission_result = await db.execute(permission_query)
        raw_permissions = permission_result.fetchall()
        
        # 查询所有权限记录，用于获取真实的权限ID
        all_permissions_query = select(Permission.id, Permission.name, Permission.display_name)
        all_permissions_result = await db.execute(all_permissions_query)
        all_permissions = {perm.name: {"id": perm.id, "display_name": perm.display_name} for perm in all_permissions_result.fetchall()}
        
        # 展开通配符权限
        expanded_permission_names = set()
        for perm in raw_permissions:
            permission_name = perm.name
            if permission_name == '*':
                # 全部权限
                expanded_permission_names.update(SYSTEM_PERMISSIONS.keys())
            elif permission_name.endswith(':*'):
                # 模块下的所有权限
                module = permission_name[:-2]
                for sys_perm in SYSTEM_PERMISSIONS.keys():
                    if sys_perm.startswith(f"{module}:"):
                        expanded_permission_names.add(sys_perm)
            elif permission_name.startswith('*:'):
                # 所有模块的特定操作
                action = permission_name[2:]
                for sys_perm in SYSTEM_PERMISSIONS.keys():
                    if sys_perm.endswith(f":{action}"):
                        expanded_permission_names.add(sys_perm)
            else:
                # 具体权限
                expanded_permission_names.add(permission_name)
        
        # 构建权限响应数据，使用数据库中的真实ID
        permissions_data = []
        for perm_name in sorted(expanded_permission_names):
            if perm_name in all_permissions:
                permissions_data.append({
                    "id": all_permissions[perm_name]["id"],  # 使用数据库中的真实ID
                    "name": perm_name,
                    "display_name": all_permissions[perm_name]["display_name"] or SYSTEM_PERMISSIONS.get(perm_name, perm_name)
                })
            elif perm_name in SYSTEM_PERMISSIONS:
                # 如果数据库中没有该权限记录，但在系统权限定义中存在，则跳过或记录警告
                logger.warning(f"Permission '{perm_name}' exists in SYSTEM_PERMISSIONS but not in database")
                continue
        
        role_data['permissions'] = permissions_data

        return ResponseBuilder.success(
            data=role_data,
            message="角色信息更新成功"
        )
    except BaseCustomException:
        # 让自定义异常传播到全局异常处理器
        raise
    except Exception as e:
        logger.error(f"Failed to update role: {str(e)}")
        raise_business_error("更新角色失败", 1000)


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

        log_security_event(
            "role_deleted",
            user_id=current_user.id,
            details=f"role_id: {role_id}"
        )

        return ResponseBuilder.success(
            message="角色删除成功"
        )
    except BaseCustomException:
        # 重新抛出自定义异常，保持原有的错误信息
        raise
    except Exception as e:
        logger.error(f"Failed to delete role: {str(e)}")
        raise_business_error("删除角色失败", 1000)


@router.get("/list", summary="获取角色列表")
async def get_roles(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    is_system: Optional[bool] = Query(None, description="是否系统角色"),
    has_users: Optional[bool] = Query(None, description="是否有用户"),
    permission: Optional[str] = Query(None, description="包含特定权限"),
    status: Optional[int] = Query(None, ge=-1, le=1, description="角色状态（-1=全部，0=禁用，1=激活）"),
    order_by: str = Query("sort_order", description="排序字段"),
    order_desc: bool = Query(True, description="是否降序"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("role:read"))
):
    """获取角色列表（支持搜索和分页）"""
    try:
        # 构建搜索查询
        search_query = RoleSearchQuery(
            keyword=keyword,
            is_system=is_system,
            has_users=has_users,
            permission=permission,
            status=status,
            page=page,
            page_size=size,
            order_by=order_by,
            order_desc=order_desc
        )

        role_service = RoleService(db)
        roles, total = await role_service.get_roles(page, size, search_query)

        # 批量获取用户数量统计，避免N+1查询问题
        role_ids = [role.id for role in roles]
        user_counts = {}

        if role_ids:
            from sqlalchemy import select, func
            from app.models.role import UserRole

            # 批量查询每个角色的用户数量
            user_count_query = (
                select(UserRole.role_id, func.count(
                    UserRole.user_id).label('user_count'))
                .where(UserRole.role_id.in_(role_ids))
                .group_by(UserRole.role_id)
            )
            user_count_result = await db.execute(user_count_query)
            user_counts = {
                row.role_id: row.user_count for row in user_count_result}

        # 转换为响应模型
        role_list = []
        for role in roles:
            # 从批量查询结果中获取用户数量
            user_count = user_counts.get(role.id, 0)
            # 修复权限计数逻辑 - 考虑通配符权限的展开
            permission_count = 0
            if hasattr(role, 'role_permissions') and role.role_permissions:
                # 获取角色的所有权限名称
                role_permissions = [rp.permission.name for rp in role.role_permissions if rp.permission]
                
                # 计算展开后的权限数量
                from app.models.role import SYSTEM_PERMISSIONS
                expanded_permissions = set()
                
                for permission in role_permissions:
                    if permission == '*' or permission == '*:*':
                        # 超级权限，添加所有系统权限
                        expanded_permissions.update(SYSTEM_PERMISSIONS.keys())
                    elif permission.endswith(':*'):
                        # 模块通配符权限，添加该模块的所有权限
                        module = permission[:-2]  # 移除 ':*'
                        for sys_perm in SYSTEM_PERMISSIONS.keys():
                            if sys_perm.startswith(f"{module}:"):
                                expanded_permissions.add(sys_perm)
                    elif permission.startswith('*:'):
                        # 操作通配符权限，添加所有模块的该操作权限
                        action = permission[2:]  # 移除 '*:'
                        for sys_perm in SYSTEM_PERMISSIONS.keys():
                            if sys_perm.endswith(f":{action}"):
                                expanded_permissions.add(sys_perm)
                    else:
                        # 具体权限，直接添加
                        expanded_permissions.add(permission)
                
                permission_count = len(expanded_permissions)

            role_data = {
                "id": role.id,
                "name": role.name,
                "display_name": role.display_name,
                "description": role.description,
                "is_system": role.is_system,
                "is_active": role.is_active,
                "user_count": user_count,
                "permission_count": permission_count,
                "created_at": role.created_at.isoformat() if role.created_at else None
            }
            role_list.append(role_data)

        return ResponseBuilder.paginated(
            data=role_list,
            total=total,
            page=page,
            size=size,
            message="获取角色列表成功"
        )
    except Exception as e:
        logger.error(f"Failed to get roles: {str(e)}")
        raise_business_error("获取角色列表失败", 1000)


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
        raise_business_error("获取角色统计信息失败", 1000)


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

        log_security_event(
            "permission_created",
            user_id=current_user.id,
            details=f"permission_name: {permission.name}, permission_id: {permission.id}"
        )

        # 手动构建权限数据，避免关系查询
        permission_data = {
            'id': permission.id,
            'name': permission.name,
            'display_name': permission.display_name,
            'description': permission.description,
            'module': permission.module,
            'action': permission.action,
            'resource': permission.resource,
            'is_system': bool(permission.is_system),
            'sort_order': permission.sort_order,
            'created_at': permission.created_at.isoformat() if permission.created_at else None,
            'updated_at': permission.updated_at.isoformat() if permission.updated_at else None,
        }

        return ResponseBuilder.success(
            data=permission_data,
            message="权限创建成功"
        )
    except BaseCustomException:
        # 重新抛出自定义异常，保持原有的错误信息
        raise
    except Exception as e:
        logger.error(f"Failed to create permission: {str(e)}")
        raise_business_error("创建权限失败", 1000)


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
            raise_not_found_resource("权限")

        # 手动构建权限数据，避免关系查询
        permission_data = {
            'id': permission.id,
            'name': permission.name,
            'display_name': permission.display_name,
            'description': permission.description,
            'module': permission.module,
            'action': permission.action,
            'resource': permission.resource,
            'is_system': bool(permission.is_system),
            'sort_order': permission.sort_order,
            'created_at': permission.created_at.isoformat() if permission.created_at else None,
            'updated_at': permission.updated_at.isoformat() if permission.updated_at else None,
        }

        return ResponseBuilder.success(
            data=permission_data,
            message="获取权限信息成功"
        )
    except BaseCustomException:
        raise
    except Exception as e:
        logger.error(f"Failed to get permission: {str(e)}")
        raise_business_error("获取权限信息失败", 1000)


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

        log_security_event(
            "permission_updated",
            user_id=current_user.id,
            details=f"permission_id: {permission_id}, updated_fields: {list(permission_data.dict(exclude_unset=True).keys())}"
        )

        # 手动构建权限数据，避免关系查询
        permission_data = {
            'id': updated_permission.id,
            'name': updated_permission.name,
            'display_name': updated_permission.display_name,
            'description': updated_permission.description,
            'module': updated_permission.module,
            'action': updated_permission.action,
            'resource': updated_permission.resource,
            'is_system': bool(updated_permission.is_system),
            'sort_order': updated_permission.sort_order,
            'created_at': updated_permission.created_at.isoformat() if updated_permission.created_at else None,
            'updated_at': updated_permission.updated_at.isoformat() if updated_permission.updated_at else None,
        }

        return ResponseBuilder.success(
            data=permission_data,
            message="权限信息更新成功"
        )
    except BaseCustomException:
        # 让自定义异常传播到全局异常处理器，这样可以返回精确的错误信息
        raise
    except Exception as e:
        logger.error(f"Failed to update permission: {str(e)}")
        raise_business_error("更新权限失败", 1000)


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

        log_security_event(
            "permission_deleted",
            user_id=current_user.id,
            details=f"permission_id: {permission_id}"
        )

        return ResponseBuilder.success(
            message="权限删除成功"
        )
    except BaseCustomException:
        # 让自定义异常传播到全局异常处理器，这样可以返回精确的错误信息
        raise
    except Exception as e:
        logger.error(f"Failed to delete permission: {str(e)}")
        raise_business_error("删除权限失败", 1000)


@router.get("/permissions/list", response_model=PermissionListResponse, summary="获取权限列表")
async def get_permissions(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页数量"),
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    module: Optional[str] = Query(None, description="所属模块"),
    action: Optional[str] = Query(None, description="操作类型"),
    resource: Optional[str] = Query(None, description="资源类型"),
    is_system: Optional[bool] = Query(None, description="是否系统权限"),
    order_by: Optional[str] = Query("sort_order", description="排序字段"),
    order_desc: Optional[bool] = Query(False, description="是否降序"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("permission:read"))
):
    """获取权限列表（支持搜索和分页）"""
    try:
        # 构建搜索查询
        search_query = PermissionSearchQuery(
            keyword=keyword,
            module=module,
            action=action,
            resource=resource,
            is_system=is_system,
            page=page,
            page_size=size,
            order_by=order_by,
            order_desc=order_desc
        )

        role_service = RoleService(db)
        permissions, total = await role_service.get_permissions(page, size, search_query)

        # 手动构建权限数据列表，避免关系查询
        permissions_data = []
        for permission in permissions:
            permission_data = {
                'id': permission.id,
                'name': permission.name,
                'display_name': permission.display_name,
                'description': permission.description,
                'module': permission.module,
                'action': permission.action,
                'resource': permission.resource,
                'is_system': bool(permission.is_system),
                'sort_order': permission.sort_order,
                'created_at': permission.created_at.isoformat() if permission.created_at else None,
                'updated_at': permission.updated_at.isoformat() if permission.updated_at else None,
            }
            permissions_data.append(permission_data)

        return ResponseBuilder.paginated(
            data=permissions_data,
            total=total,
            page=page,
            size=size,
            message="获取权限列表成功"
        )
    except ValueError as e:
        # 处理 Pydantic 验证错误，提供更友好的错误信息
        error_msg = str(e)
        logger.warning(f"Permission query validation error: {error_msg}")

        # 解析并转换为更友好的中文错误信息
        if "操作类型必须是以下值之一" in error_msg:
            friendly_msg = "操作类型参数无效，请使用以下值之一：create（创建）、read（查看）、update（更新）、delete（删除）、assign（分配）、execute（执行）"
        elif "资源类型必须是以下值之一" in error_msg:
            friendly_msg = "资源类型参数无效，请使用以下值之一：user（用户）、role（角色）、script（剧本）、audio（音频）、review（审核）、society（社团）、system（系统）"
        elif "validation error" in error_msg.lower():
            # 通用参数验证错误
            if "action" in error_msg:
                friendly_msg = "操作类型参数格式错误，请检查参数值是否正确"
            elif "resource" in error_msg:
                friendly_msg = "资源类型参数格式错误，请检查参数值是否正确"
            elif "page" in error_msg:
                friendly_msg = "页码参数必须是大于0的整数"
            elif "page_size" in error_msg or "size" in error_msg:
                friendly_msg = "每页数量参数必须是1-100之间的整数"
            else:
                friendly_msg = "请求参数格式错误，请检查参数类型和取值范围"
        else:
            friendly_msg = "请求参数验证失败，请检查参数格式和取值是否正确"

        raise_business_error(friendly_msg, 1001)
    except Exception as e:
        logger.error(f"Failed to get permissions: {str(e)}")
        raise_business_error("获取权限列表失败", 1000)


# ==================== 用户角色分配 ====================

@router.post("/user/roles", summary="分配角色给用户")
async def assign_roles_to_user(
    assignment: UserRoleAssignment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("role:assign"))
):
    """分配角色给用户（支持单个或多个角色）"""
    try:
        role_service = RoleService(db)
        result = await role_service.assign_roles_to_user(
            user_id=assignment.user_id,
            role_ids=assignment.role_ids,
            assigned_by=current_user.id,
            expires_at=getattr(assignment, 'expires_at', None)
        )

        log_security_event(
            "roles_assigned",
            user_id=current_user.id,
            details=f"target_user_id: {assignment.user_id}, role_ids: {assignment.role_ids}, success: {result['success_count']}, failed: {result['failed_count']}"
        )

        return ResponseBuilder.success(
            data=result,
            message=f"批量分配角色完成：成功 {result['success_count']} 个，失败 {result['failed_count']} 个"
        )
    except BaseCustomException:
        # 让自定义异常传播到全局异常处理器，这样可以返回精确的错误信息
        raise
    except Exception as e:
        logger.error(f"Failed to assign roles: {str(e)}")
        raise_business_error("批量分配角色失败", 1000)


@router.delete("/user/roles", summary="移除用户角色")
async def remove_roles_from_user(
    removal: UserRoleRemoval,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("role:assign"))
):
    """移除用户角色（支持单个或多个角色）"""
    try:
        role_service = RoleService(db)
        result = await role_service.remove_roles_from_user(
            user_id=removal.user_id,
            role_ids=removal.role_ids
        )

        log_security_event(
            "roles_removed",
            user_id=current_user.id,
            details=f"target_user_id: {removal.user_id}, role_ids: {removal.role_ids}, success: {result['success_count']}, failed: {result['failed_count']}"
        )

        return ResponseBuilder.success(
            data=result,
            message=f"角色移除完成：成功 {result['success_count']} 个，失败 {result['failed_count']} 个"
        )
    except Exception as e:
        logger.error(f"Failed to remove role: {str(e)}")
        raise_business_error("移除角色失败", 1000)


# 删除重复的 /user/remove 接口，功能已由 /user/unassign 提供


@router.post("/users/batch/roles", summary="批量分配角色给多个用户")
async def batch_assign_roles(
    batch_assignment: RoleAssignmentBatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("role:assign"))
):
    """批量为多个用户分配角色"""
    try:
        role_service = RoleService(db)
        result = await role_service.batch_assign_roles_to_users(
            user_ids=batch_assignment.user_ids,
            role_ids=batch_assignment.role_ids,
            assigned_by=current_user.id,
            expires_at=batch_assignment.expires_at
        )

        log_security_event(
            "batch_roles_assigned",
            user_id=current_user.id,
            details=f"user_count: {len(batch_assignment.user_ids)}, role_count: {len(batch_assignment.role_ids)}, success_count: {result['success_count']}, failed_count: {result['failed_count']}"
        )

        return ResponseBuilder.success(
            data=result,
            message=f"批量分配角色完成：成功 {result['success_count']} 个，失败 {result['failed_count']} 个"
        )
    except BaseCustomException:
        raise
    except Exception as e:
        logger.error(f"Failed to batch assign roles: {str(e)}")
        raise_business_error("批量分配角色失败", 1000)


@router.delete("/users/batch/roles", summary="批量移除多个用户的角色")
async def batch_remove_roles(
    batch_removal: RoleAssignmentBatch,  # 复用相同的模型结构
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("role:assign"))
):
    """批量移除多个用户的角色"""
    try:
        role_service = RoleService(db)
        result = await role_service.batch_remove_roles_from_users(
            user_ids=batch_removal.user_ids,
            role_ids=batch_removal.role_ids,
            removed_by=current_user.id
        )

        log_security_event(
            "batch_roles_removed",
            user_id=current_user.id,
            details=f"user_count: {len(batch_removal.user_ids)}, role_count: {len(batch_removal.role_ids)}, success_count: {result['success_count']}, failed_count: {result['failed_count']}"
        )

        return ResponseBuilder.success(
            data=result,
            message=f"批量移除角色完成：成功 {result['success_count']} 个，失败 {result['failed_count']} 个"
        )
    except BaseCustomException:
        raise
    except Exception as e:
        logger.error(f"Failed to batch remove roles: {str(e)}")
        raise_business_error("批量移除角色失败", 1000)


@router.get("/user/{user_id}", summary="获取用户角色")
async def get_user_roles(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("role:read"))
):
    """获取指定用户的所有角色"""
    try:
        role_service = RoleService(db)
        roles = await role_service.get_user_roles(user_id)

        # 将Role对象转换为字典格式
        roles_data = [role.to_dict() for role in roles]

        return ResponseBuilder.success(
            data=roles_data,
            message="获取用户角色成功"
        )
    except Exception as e:
        logger.error(f"Failed to get user roles: {str(e)}")
        raise_business_error("获取用户角色失败", 1000)


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

        # 将User对象转换为字典格式
        users_data = [user.to_dict_sync() for user in users]

        return ResponseBuilder.paginated(
            data=users_data,
            total=total,
            page=page,
            size=size,
            message="获取角色用户成功"
        )
    except Exception as e:
        logger.error(f"Failed to get role users: {str(e)}")
        raise_business_error("获取角色用户失败", 1000)


# ==================== 权限检查 ====================

@router.get("/user/permissions/{user_id}", summary="获取用户权限")
async def get_user_permissions(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("permission:read"))
):
    """获取指定用户的所有权限（包括通配符权限）"""
    try:
        role_service = RoleService(db)
        permissions = await role_service.get_user_permissions(user_id)

        return ResponseBuilder.success(
            data=permissions,
            message="获取用户权限成功"
        )
    except Exception as e:
        logger.error(f"Failed to get user permissions: {str(e)}")
        raise_business_error("获取用户权限失败", 1000)


@router.get("/user/permissions/expanded/{user_id}", summary="获取用户展开权限")
async def get_user_expanded_permissions(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("permission:read"))
):
    """获取指定用户的展开权限列表（将通配符权限展开为具体权限）"""
    try:
        role_service = RoleService(db)
        expanded_permissions = await role_service.get_user_expanded_permissions(user_id)

        return ResponseBuilder.success(
            data=expanded_permissions,
            message="获取用户展开权限成功"
        )
    except Exception as e:
        logger.error(f"Failed to get user expanded permissions: {str(e)}")
        raise_business_error("获取用户展开权限失败", 1000)


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
        raise_business_error("权限检查失败", 1000)


# ==================== 系统初始化 ====================

@router.post("/system/init", summary="初始化系统角色和权限")
async def init_system_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("system:init"))
):
    """初始化系统默认角色和权限"""
    try:
        role_service = RoleService(db)
        result = await role_service.initialize_system_data()

        log_security_event(
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
        raise_business_error("系统初始化失败", 1000)


# ==================== 角色状态管理 ====================

@router.patch("/status/{role_id}", summary="更新角色状态")
async def update_role_status(
    role_id: int,
    status_data: RoleStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("role:update"))
):
    """更新角色状态"""
    try:
        role_service = RoleService(db)
        role = await role_service.update_role_status(role_id, status_data.is_active)
        
        log_security_event(
            "role_status_updated",
            user_id=current_user.id,
            details=f"role_id: {role_id}, new_status: {status_data.is_active}"
        )
        
        return ResponseBuilder.success(
            data={
                "id": role.id,
                "name": role.name,
                "is_active": bool(role.is_active)
            },
            message="角色状态更新成功"
        )
    except Exception as e:
        logger.error(f"Failed to update role status: {str(e)}")
        raise_server_error("更新角色状态失败")


@router.post("/permissions/batch", summary="批量分配权限给角色（增量模式）")
async def batch_assign_permissions_to_role(
    permission_batch: RolePermissionBatch,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("role:update"))
):
    """批量分配权限给角色（增量模式，只添加不删除）"""
    try:
        role_service = RoleService(db)
        
        # 调用服务层方法进行批量分配
        result = await role_service.batch_assign_permissions_to_role(
            role_id=permission_batch.role_id,
            permission_ids=permission_batch.permission_ids
        )
        
        # 记录安全事件
        log_security_event(
            "role_permissions_batch_assigned",
            user_id=current_user.id,
            details=f"role_id: {permission_batch.role_id}, "
                   f"total_permissions: {result['total_permissions']}, "
                   f"success_count: {result['success_count']}, "
                   f"failed_count: {result['failed_count']}"
        )
        
        # 构建响应消息
        if result['failed_count'] == 0:
            if result['success_count'] == 0:
                message = "所有权限已存在，无需重复分配"
            else:
                message = f"成功分配 {result['success_count']} 个权限给角色"
        else:
            message = (f"批量分配完成：成功 {result['success_count']} 个，"
                      f"跳过 {result['skipped_count']} 个，"
                      f"失败 {result['failed_count']} 个")
        
        return ResponseBuilder.success(
            data=result,
            message=message
        )
        
    except BaseCustomException:
        raise
    except Exception as e:
        logger.error(f"Failed to batch assign permissions to role: {str(e)}")
        raise_business_error("批量分配权限给角色失败", 1000)


@router.post("/permissions/sync", summary="同步角色权限")
async def sync_role_permissions(
    permission_sync: RolePermissionSync,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("role:update"))
):
    """同步角色权限（完全替换角色的权限列表）"""
    try:
        role_service = RoleService(db)
        
        # 调用服务层方法进行权限同步
        result = await role_service.sync_role_permissions(
            role_id=permission_sync.role_id,
            permission_ids=permission_sync.permission_ids
        )
        
        # 记录安全事件
        log_security_event(
            "role_permissions_synced",
            user_id=current_user.id,
            details=f"role_id: {permission_sync.role_id}, "
                   f"new_permission_count: {len(permission_sync.permission_ids)}, "
                   f"added_count: {result['added_count']}, "
                   f"removed_count: {result['removed_count']}"
        )
        
        # 构建响应消息
        if result['added_count'] == 0 and result['removed_count'] == 0:
            message = "权限同步完成，无变更"
        else:
            message = f"权限同步完成：新增 {result['added_count']} 个，移除 {result['removed_count']} 个"
        
        return ResponseBuilder.success(
            data=result,
            message=message
        )
        
    except BaseCustomException:
        raise
    except Exception as e:
        logger.error(f"Failed to sync role permissions: {str(e)}")
        raise_business_error("同步角色权限失败", 1000)
