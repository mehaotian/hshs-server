from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta

from app.models.role import Role, Permission, UserRole
from app.models.user import User
from app.schemas.role import (
    RoleCreate, RoleUpdate, PermissionCreate, PermissionUpdate,
    UserRoleCreate, UserRoleUpdate, RoleSearchQuery, PermissionSearchQuery,
    RoleAssignmentBatch, PermissionCheck
)
from app.core.exceptions import (
    raise_not_found, raise_duplicate, raise_validation_error,
    raise_business_error, raise_permission_error
)
from app.core.logger import logger
from app.core.database import DatabaseManager


class RoleService:
    """角色服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.db_manager = DatabaseManager()
    
    # ==================== 角色管理 ====================
    
    async def create_role(self, role_data: RoleCreate) -> Role:
        """创建角色"""
        # 检查角色名是否已存在
        existing_role = await self.get_role_by_name(role_data.name)
        if existing_role:
            raise_duplicate("Role", "name", role_data.name)
        
        # 创建角色
        role_dict = role_data.dict()
        role = Role(**role_dict)
        
        try:
            self.db.add(role)
            await self.db.commit()
            await self.db.refresh(role)
            
            logger.info(f"Role created: {role.name} (ID: {role.id})")
            return role
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create role: {str(e)}")
            raise_business_error("Failed to create role")
    
    async def get_role_by_id(self, role_id: int) -> Optional[Role]:
        """根据ID获取角色"""
        result = await self.db.execute(
            select(Role).where(Role.id == role_id)
        )
        return result.scalar_one_or_none()
    
    async def get_role_by_name(self, name: str) -> Optional[Role]:
        """根据名称获取角色"""
        result = await self.db.execute(
            select(Role).where(Role.name == name)
        )
        return result.scalar_one_or_none()
    
    async def update_role(self, role_id: int, role_data: RoleUpdate) -> Role:
        """更新角色"""
        role = await self.get_role_by_id(role_id)
        if not role:
            raise_not_found("Role", role_id)
        
        # 检查系统角色是否可以修改
        if role.is_system and role_data.name and role_data.name != role.name:
            raise_validation_error("System role name cannot be changed")
        
        # 检查角色名是否重复（如果要更新名称）
        if role_data.name and role_data.name != role.name:
            existing_role = await self.get_role_by_name(role_data.name)
            if existing_role:
                raise_duplicate("Role", "name", role_data.name)
        
        # 更新角色信息
        update_data = role_data.dict(exclude_unset=True)
        
        try:
            await self.db.execute(
                update(Role)
                .where(Role.id == role_id)
                .values(**update_data)
            )
            await self.db.commit()
            
            # 重新获取更新后的角色
            updated_role = await self.get_role_by_id(role_id)
            
            logger.info(f"Role updated: {role.name} (ID: {role_id})")
            return updated_role
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update role {role_id}: {str(e)}")
            raise_business_error("Failed to update role")
    
    async def delete_role(self, role_id: int) -> bool:
        """删除角色"""
        role = await self.get_role_by_id(role_id)
        if not role:
            raise_not_found("Role", role_id)
        
        # 检查是否为系统角色
        if role.is_system:
            raise_validation_error("System role cannot be deleted")
        
        # 检查是否有用户使用此角色
        user_count_result = await self.db.execute(
            select(func.count(UserRole.id)).where(UserRole.role_id == role_id)
        )
        user_count = user_count_result.scalar()
        
        if user_count > 0:
            raise_validation_error(f"Cannot delete role: {user_count} users are assigned to this role")
        
        try:
            await self.db.execute(
                delete(Role).where(Role.id == role_id)
            )
            await self.db.commit()
            
            logger.info(f"Role deleted: {role.name} (ID: {role_id})")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete role {role_id}: {str(e)}")
            raise_business_error("Failed to delete role")
    
    async def get_roles(
        self, 
        page: int = 1, 
        size: int = 20,
        search_query: Optional[RoleSearchQuery] = None
    ) -> Tuple[List[Role], int]:
        """获取角色列表（优化版本）"""
        # 基础查询，Role.permissions是JSON列不需要预加载
        query = select(Role)
        
        # 构建搜索条件的公共函数
        def build_conditions(search_query):
            conditions = []
            if search_query:
                if search_query.keyword:
                    keyword = f"%{search_query.keyword}%"
                    conditions.append(
                        or_(
                            Role.name.ilike(keyword),
                            Role.display_name.ilike(keyword),
                            Role.description.ilike(keyword)
                        )
                    )
                
                if search_query.is_system is not None:
                    conditions.append(Role.is_system == search_query.is_system)
                
                # 支持按权限过滤 - 在JSON列中搜索
                if search_query.permission:
                    # 使用JSON操作符搜索权限
                    conditions.append(
                        Role.permissions.op('->>')('permissions').op('@>')(
                            f'["{search_query.permission}"]'
                        )
                    )
                
                # 支持按是否有用户过滤
                if search_query.has_users is not None:
                    if search_query.has_users:
                        conditions.append(Role.user_roles.any())
                    else:
                        conditions.append(~Role.user_roles.any())
            
            return conditions
        
        # 应用搜索条件
        conditions = build_conditions(search_query)
        if conditions:
            query = query.where(and_(*conditions))
        
        # 排序优化
        if search_query and search_query.order_by:
            order_column = getattr(Role, search_query.order_by, None)
            if order_column is not None:
                if search_query.order_desc:
                    query = query.order_by(order_column.desc())
                else:
                    query = query.order_by(order_column)
            else:
                # 默认排序
                query = query.order_by(Role.sort_order, Role.created_at)
        else:
            query = query.order_by(Role.sort_order, Role.created_at)
        
        # 优化总数查询 - 使用相同的条件
        count_query = select(func.count(Role.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        
        # 并行执行总数查询和数据查询以提高性能
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # 分页
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)
        
        result = await self.db.execute(query)
        roles = result.scalars().all()
        
        return list(roles), total
    
    # ==================== 权限管理 ====================
    
    async def create_permission(self, permission_data: PermissionCreate) -> Permission:
        """创建权限"""
        # 检查权限名是否已存在
        existing_permission = await self.get_permission_by_name(permission_data.name)
        if existing_permission:
            raise_duplicate("Permission", "name", permission_data.name)
        
        # 创建权限
        permission_dict = permission_data.dict()
        permission = Permission(**permission_dict)
        
        try:
            self.db.add(permission)
            await self.db.commit()
            await self.db.refresh(permission)
            
            logger.info(f"Permission created: {permission.name} (ID: {permission.id})")
            return permission
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create permission: {str(e)}")
            raise_business_error("Failed to create permission")
    
    async def get_permission_by_id(self, permission_id: int) -> Optional[Permission]:
        """根据ID获取权限"""
        result = await self.db.execute(
            select(Permission).where(Permission.id == permission_id)
        )
        return result.scalar_one_or_none()
    
    async def get_permission_by_name(self, name: str) -> Optional[Permission]:
        """根据名称获取权限"""
        result = await self.db.execute(
            select(Permission).where(Permission.name == name)
        )
        return result.scalar_one_or_none()
    
    async def update_permission(self, permission_id: int, permission_data: PermissionUpdate) -> Permission:
        """更新权限"""
        permission = await self.get_permission_by_id(permission_id)
        if not permission:
            raise_not_found("Permission", permission_id)
        
        # 检查系统权限是否可以修改关键字段
        if permission.is_system:
            # 系统权限不允许修改名称、模块、操作类型和资源类型
            if permission_data.name and permission_data.name != permission.name:
                raise_validation_error("System permission name cannot be changed")
            if permission_data.module and permission_data.module != permission.module:
                raise_validation_error("System permission module cannot be changed")
            if permission_data.action and permission_data.action != permission.action:
                raise_validation_error("System permission action cannot be changed")
            if permission_data.resource and permission_data.resource != permission.resource:
                raise_validation_error("System permission resource cannot be changed")
        
        # 检查权限名是否重复（如果要更新名称）
        if permission_data.name and permission_data.name != permission.name:
            existing_permission = await self.get_permission_by_name(permission_data.name)
            if existing_permission:
                raise_duplicate("Permission", "name", permission_data.name)
        
        # 更新权限信息
        update_data = permission_data.dict(exclude_unset=True)
        
        try:
            await self.db.execute(
                update(Permission)
                .where(Permission.id == permission_id)
                .values(**update_data)
            )
            await self.db.commit()
            
            # 重新获取更新后的权限
            updated_permission = await self.get_permission_by_id(permission_id)
            
            logger.info(f"Permission updated: {permission.name} (ID: {permission_id})")
            return updated_permission
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update permission {permission_id}: {str(e)}")
            raise_business_error("Failed to update permission")
    
    async def delete_permission(self, permission_id: int) -> bool:
        """删除权限"""
        permission = await self.get_permission_by_id(permission_id)
        if not permission:
            raise_not_found("Permission", permission_id)
        
        # 检查是否为系统权限
        if permission.is_system:
            raise_validation_error("System permission cannot be deleted")
        
        try:
            await self.db.execute(
                delete(Permission).where(Permission.id == permission_id)
            )
            await self.db.commit()
            
            logger.info(f"Permission deleted: {permission.name} (ID: {permission_id})")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete permission {permission_id}: {str(e)}")
            raise_business_error("Failed to delete permission")
    
    async def get_permissions(
        self, 
        page: int = 1, 
        size: int = 20,
        search_query: Optional[PermissionSearchQuery] = None
    ) -> Tuple[List[Permission], int]:
        """获取权限列表"""
        query = select(Permission)
        
        # 构建搜索条件
        if search_query:
            conditions = []
            
            if search_query.keyword:
                keyword = f"%{search_query.keyword}%"
                conditions.append(
                    or_(
                        Permission.name.ilike(keyword),
                        Permission.display_name.ilike(keyword),
                        Permission.description.ilike(keyword)
                    )
                )
            
            if search_query.module:
                conditions.append(Permission.module == search_query.module)
            
            if search_query.action:
                conditions.append(Permission.action == search_query.action)
            
            if search_query.resource:
                conditions.append(Permission.resource == search_query.resource)
            
            if search_query.is_system is not None:
                conditions.append(Permission.is_system == search_query.is_system)
            
            if conditions:
                query = query.where(and_(*conditions))
        
        # 排序
        if search_query and search_query.order_by:
            if search_query.order_desc:
                query = query.order_by(getattr(Permission, search_query.order_by).desc())
            else:
                query = query.order_by(getattr(Permission, search_query.order_by))
        else:
            query = query.order_by(Permission.module, Permission.sort_order)
        
        # 获取总数
        count_query = select(func.count(Permission.id))
        if search_query:
            conditions = []
            if search_query.keyword:
                keyword = f"%{search_query.keyword}%"
                conditions.append(
                    or_(
                        Permission.name.ilike(keyword),
                        Permission.display_name.ilike(keyword),
                        Permission.description.ilike(keyword)
                    )
                )
            if search_query.module:
                conditions.append(Permission.module == search_query.module)
            if search_query.action:
                conditions.append(Permission.action == search_query.action)
            if search_query.resource:
                conditions.append(Permission.resource == search_query.resource)
            if search_query.is_system is not None:
                conditions.append(Permission.is_system == search_query.is_system)
            
            if conditions:
                count_query = count_query.where(and_(*conditions))
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # 分页
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)
        
        result = await self.db.execute(query)
        permissions = result.scalars().all()
        
        return list(permissions), total
    
    # ==================== 用户角色管理 ====================
    
    async def assign_roles_to_user(self, user_id: int, role_ids: List[int], assigned_by: int, expires_at: Optional[datetime] = None) -> Dict[str, Any]:
        """批量分配角色给用户"""
        # 检查用户是否存在
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise_not_found("User", user_id)
        
        results = {
            "success_count": 0,
            "failed_count": 0,
            "errors": [],
            "assigned_roles": []
        }
        
        try:
            for role_id in role_ids:
                try:
                    # 检查角色是否存在
                    role = await self.get_role_by_id(role_id)
                    if not role:
                        results["failed_count"] += 1
                        results["errors"].append({
                            "role_id": role_id,
                            "error": f"角色 {role_id} 不存在"
                        })
                        continue
                    
                    # 检查是否已经分配了该角色
                    existing = await self.db.execute(
                        select(UserRole).where(
                            and_(
                                UserRole.user_id == user_id,
                                UserRole.role_id == role_id
                            )
                        )
                    )
                    
                    if existing.scalar_one_or_none():
                        results["failed_count"] += 1
                        results["errors"].append({
                            "role_id": role_id,
                            "error": f"用户已经拥有角色 '{role.name}'"
                        })
                        continue
                    
                    # 创建用户角色关联
                    user_role = UserRole(
                        user_id=user_id,
                        role_id=role_id,
                        assigned_by=assigned_by,
                        assigned_at=datetime.utcnow(),
                        expires_at=expires_at
                    )
                    
                    self.db.add(user_role)
                    results["success_count"] += 1
                    results["assigned_roles"].append({
                        "role_id": role_id,
                        "role_name": role.name
                    })
                    
                    logger.info(f"Role {role.name} assigned to user {user.username} by user {assigned_by}")
                    
                except Exception as e:
                    results["failed_count"] += 1
                    results["errors"].append({
                        "role_id": role_id,
                        "error": str(e)
                    })
            
            await self.db.commit()
            
            logger.info(
                f"Batch role assignment completed for user {user.username}: "
                f"{results['success_count']} success, {results['failed_count']} failed"
            )
            
            return results
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Batch role assignment failed for user {user_id}: {str(e)}")
            raise_business_error("批量分配角色失败")
    
    async def assign_role_to_user(self, user_role_data: UserRoleCreate) -> UserRole:
        """为用户分配单个角色（保持向后兼容）"""
        result = await self.assign_roles_to_user(
            user_role_data.user_id, 
            [user_role_data.role_id], 
            user_role_data.assigned_by, 
            user_role_data.expires_at
        )
        
        if result["failed_count"] > 0:
            error_msg = result["errors"][0]["error"]
            if "已经拥有角色" in error_msg:
                from ..core.exceptions import DuplicateResourceException
                raise DuplicateResourceException(error_msg)
            else:
                raise_business_error(error_msg)
        
        # 返回创建的用户角色关联
        user_role_result = await self.db.execute(
            select(UserRole).where(
                and_(
                    UserRole.user_id == user_role_data.user_id,
                    UserRole.role_id == user_role_data.role_id
                )
            )
        )
        
        return user_role_result.scalar_one()
    
    async def remove_roles_from_user(self, user_id: int, role_ids: List[int]) -> Dict[str, Any]:
        """批量移除用户角色"""
        # 检查用户是否存在
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise_not_found("User", user_id)
        
        results = {
            "success_count": 0,
            "failed_count": 0,
            "errors": [],
            "removed_roles": []
        }
        
        try:
            for role_id in role_ids:
                try:
                    # 检查用户角色关联是否存在
                    user_role_result = await self.db.execute(
                        select(UserRole).where(
                            and_(
                                UserRole.user_id == user_id,
                                UserRole.role_id == role_id
                            )
                        )
                    )
                    user_role = user_role_result.scalar_one_or_none()
                    
                    if not user_role:
                        results["failed_count"] += 1
                        results["errors"].append({
                            "role_id": role_id,
                            "error": f"用户未拥有角色 {role_id}"
                        })
                        continue
                    
                    # 获取角色信息用于日志
                    role = await self.get_role_by_id(role_id)
                    role_name = role.name if role else str(role_id)
                    
                    # 删除用户角色关联
                    await self.db.execute(
                        delete(UserRole).where(
                            and_(
                                UserRole.user_id == user_id,
                                UserRole.role_id == role_id
                            )
                        )
                    )
                    
                    results["success_count"] += 1
                    results["removed_roles"].append({
                        "role_id": role_id,
                        "role_name": role_name
                    })
                    
                    logger.info(f"Role {role_name} removed from user {user.username}")
                    
                except Exception as e:
                    results["failed_count"] += 1
                    results["errors"].append({
                        "role_id": role_id,
                        "error": str(e)
                    })
            
            await self.db.commit()
            
            logger.info(
                f"Batch role removal completed for user {user.username}: "
                f"{results['success_count']} success, {results['failed_count']} failed"
            )
            
            return results
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Batch role removal failed for user {user_id}: {str(e)}")
            raise_business_error("批量移除角色失败")
    
    async def remove_role_from_user(self, user_id: int, role_id: int) -> bool:
        """移除用户单个角色（保持向后兼容）"""
        result = await self.remove_roles_from_user(user_id, [role_id])
        
        if result["failed_count"] > 0:
            error_msg = result["errors"][0]["error"]
            if "未拥有角色" in error_msg:
                raise_not_found("UserRole", f"{user_id}-{role_id}")
            else:
                raise_business_error(error_msg)
        
        return result["success_count"] > 0
    
    async def batch_assign_roles(self, assignment: RoleAssignmentBatch) -> Dict[str, Any]:
        """批量分配角色"""
        results = {
            "success_count": 0,
            "failed_count": 0,
            "errors": []
        }
        
        try:
            for user_id in assignment.user_ids:
                for role_id in assignment.role_ids:
                    try:
                        # 检查是否已分配
                        existing = await self.db.execute(
                            select(UserRole).where(
                                and_(
                                    UserRole.user_id == user_id,
                                    UserRole.role_id == role_id
                                )
                            )
                        )
                        
                        if not existing.scalar_one_or_none():
                            user_role = UserRole(
                                user_id=user_id,
                                role_id=role_id,
                                assigned_by=assignment.assigned_by,
                                expires_at=assignment.expires_at
                            )
                            self.db.add(user_role)
                            results["success_count"] += 1
                        
                    except Exception as e:
                        results["failed_count"] += 1
                        results["errors"].append({
                            "user_id": user_id,
                            "role_id": role_id,
                            "error": str(e)
                        })
            
            await self.db.commit()
            
            logger.info(
                f"Batch role assignment completed: "
                f"{results['success_count']} success, {results['failed_count']} failed"
            )
            
            return results
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Batch role assignment failed: {str(e)}")
            raise_business_error("Batch role assignment failed")
    
    async def get_user_roles(self, user_id: int) -> List[Role]:
        """获取用户的所有角色"""
        result = await self.db.execute(
            select(Role)
            .join(UserRole, Role.id == UserRole.role_id)
            .where(UserRole.user_id == user_id)
            .where(
                or_(
                    UserRole.expires_at.is_(None),
                    UserRole.expires_at > datetime.utcnow()
                )
            )
        )
        return list(result.scalars().all())
    
    async def get_role_users(self, role_id: int, page: int = 1, size: int = 20) -> Tuple[List[User], int]:
        """获取拥有指定角色的所有用户（支持分页）"""
        # 基础查询
        base_query = (
            select(User)
            .join(UserRole, User.id == UserRole.user_id)
            .where(UserRole.role_id == role_id)
            .where(
                or_(
                    UserRole.expires_at.is_(None),
                    UserRole.expires_at > datetime.utcnow()
                )
            )
        )
        
        # 获取总数
        count_query = (
            select(func.count(User.id))
            .join(UserRole, User.id == UserRole.user_id)
            .where(UserRole.role_id == role_id)
            .where(
                or_(
                    UserRole.expires_at.is_(None),
                    UserRole.expires_at > datetime.utcnow()
                )
            )
        )
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # 分页查询
        offset = (page - 1) * size
        query = base_query.order_by(User.created_at.desc()).offset(offset).limit(size)
        
        result = await self.db.execute(query)
        users = list(result.scalars().all())
        
        return users, total
    
    async def check_user_permission(self, user_id: int, permission_name: str) -> bool:
        """检查用户是否有指定权限"""
        # 获取用户角色
        user_roles = await self.get_user_roles(user_id)
        
        # 检查每个角色的权限
        for role in user_roles:
            if role.has_permission(permission_name):
                return True
        
        return False
    
    async def get_user_permissions(self, user_id: int) -> List[str]:
        """获取用户的所有权限"""
        from ..models.user import User
        from sqlalchemy import select
        
        # 获取用户
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            from ..core.exceptions import raise_not_found
            raise_not_found("User", user_id)
        
        # 获取用户权限
        return await user.get_permissions(self.db)
    
    async def get_role_statistics(self) -> Dict[str, Any]:
        """获取角色统计信息"""
        # 总角色数
        total_roles_result = await self.db.execute(
            select(func.count(Role.id))
        )
        total_roles = total_roles_result.scalar()
        
        # 系统角色数
        system_roles_result = await self.db.execute(
            select(func.count(Role.id)).where(Role.is_system == 1)
        )
        system_roles = system_roles_result.scalar()
        
        # 自定义角色数
        custom_roles = total_roles - system_roles
        
        # 总权限数
        total_permissions_result = await self.db.execute(
            select(func.count(Permission.id))
        )
        total_permissions = total_permissions_result.scalar()
        
        # 用户角色分配统计
        role_assignment_result = await self.db.execute(
            select(Role.name, func.count(UserRole.id))
            .join(UserRole, Role.id == UserRole.role_id, isouter=True)
            .group_by(Role.id, Role.name)
        )
        role_assignments = dict(role_assignment_result.all())
        
        return {
            "total_roles": total_roles,
            "system_roles": system_roles,
            "custom_roles": custom_roles,
            "total_permissions": total_permissions,
            "role_assignments": role_assignments
        }
    
    async def initialize_system_data(self) -> bool:
        """初始化系统角色和权限数据"""
        try:
            # 创建系统权限
            system_permissions = Permission.get_system_permissions()
            for perm_data in system_permissions:
                existing = await self.get_permission_by_name(perm_data["name"])
                if not existing:
                    permission = Permission(**perm_data)
                    self.db.add(permission)
            
            # 创建系统角色
            system_roles = Role.get_system_roles()
            for role_data in system_roles:
                existing = await self.get_role_by_name(role_data["name"])
                if not existing:
                    role = Role(**role_data)
                    self.db.add(role)
            
            await self.db.commit()
            
            logger.info("System roles and permissions initialized")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to initialize system data: {str(e)}")
            raise_business_error("Failed to initialize system data")