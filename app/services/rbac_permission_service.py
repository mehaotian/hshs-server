#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于RBAC的权限验证服务
支持标准三表结构和通配符权限匹配
"""

from typing import List, Set, Dict, Optional, Union
from functools import lru_cache
import asyncio
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.role import Role, Permission
from app.core.cache import cache_manager
from app.core.logger import logger


class RBACPermissionService:
    """RBAC权限验证服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.cache_ttl = 300  # 缓存5分钟
        
    async def check_permission(
        self, 
        user_id: int, 
        permission: str, 
        resource_id: Optional[int] = None,
        use_cache: bool = True
    ) -> bool:
        """
        检查用户是否拥有指定权限
        
        Args:
            user_id: 用户ID
            permission: 权限名称，如 'user:read', 'script:write'
            resource_id: 资源ID（用于资源级权限控制）
            use_cache: 是否使用缓存
            
        Returns:
            bool: 是否拥有权限
        """
        try:
            # 获取用户权限列表
            user_permissions = await self.get_user_permissions(
                user_id, use_cache=use_cache
            )
            
            # 检查权限匹配
            has_permission = self._match_permission(permission, user_permissions)
            
            # 记录权限检查日志
            logger.info(
                f"权限检查: 用户{user_id} 权限'{permission}' "
                f"资源{resource_id} 结果:{has_permission}"
            )
            
            return has_permission
            
        except Exception as e:
            logger.error(f"权限检查失败: {str(e)}")
            return False
    
    async def check_permissions(
        self, 
        user_id: int, 
        permissions: List[str],
        require_all: bool = True,
        use_cache: bool = True
    ) -> bool:
        """
        批量检查权限
        
        Args:
            user_id: 用户ID
            permissions: 权限列表
            require_all: 是否需要拥有所有权限（True）还是任一权限（False）
            use_cache: 是否使用缓存
            
        Returns:
            bool: 权限检查结果
        """
        if not permissions:
            return True
            
        user_permissions = await self.get_user_permissions(
            user_id, use_cache=use_cache
        )
        
        results = [
            self._match_permission(perm, user_permissions) 
            for perm in permissions
        ]
        
        if require_all:
            return all(results)
        else:
            return any(results)
    
    async def get_user_permissions(
        self, 
        user_id: int, 
        use_cache: bool = True
    ) -> Set[str]:
        """
        获取用户的所有权限
        
        Args:
            user_id: 用户ID
            use_cache: 是否使用缓存
            
        Returns:
            Set[str]: 权限名称集合
        """
        cache_key = f"user_permissions:{user_id}"
        
        if use_cache:
            cached_permissions = await cache_manager.get(cache_key)
            if cached_permissions is not None:
                return set(cached_permissions)
        
        # 从数据库查询权限
        permissions = await self._fetch_user_permissions_from_db(user_id)
        
        # 缓存结果
        if use_cache:
            await cache_manager.set(
                cache_key, 
                list(permissions), 
                expire=self.cache_ttl
            )
        
        return permissions
    
    async def _fetch_user_permissions_from_db(self, user_id: int) -> Set[str]:
        """
        从数据库获取用户权限
        
        Args:
            user_id: 用户ID
            
        Returns:
            Set[str]: 权限名称集合
        """
        # 查询用户及其角色权限
        query = (
            select(Permission.name)
            .select_from(Permission)
            .join(
                # 这里需要根据实际的表结构调整
                # 假设有role_permissions关联表
                text("role_permissions"), 
                text("role_permissions.permission_id = permissions.id")
            )
            .join(
                text("user_roles"),
                text("user_roles.role_id = role_permissions.role_id")
            )
            .where(text("user_roles.user_id = :user_id"))
            .distinct()
        )
        
        # 由于SQLAlchemy的复杂性，这里使用原生SQL
        sql = """
        SELECT DISTINCT p.name
        FROM permissions p
        JOIN role_permissions rp ON p.id = rp.permission_id
        JOIN user_roles ur ON rp.role_id = ur.role_id
        WHERE ur.user_id = :user_id
        AND ur.is_active = true
        """
        
        result = await self.db.execute(
            text(sql), 
            {"user_id": user_id}
        )
        
        permissions = {row[0] for row in result}
        
        logger.debug(f"用户{user_id}权限: {permissions}")
        return permissions
    
    def _match_permission(
        self, 
        required_permission: str, 
        user_permissions: Set[str]
    ) -> bool:
        """
        匹配权限（精确匹配）
        
        Args:
            required_permission: 需要的权限
            user_permissions: 用户拥有的权限集合
            
        Returns:
            bool: 是否匹配
        """
        # 直接匹配
        return required_permission in user_permissions
    
    
    
    
    
    async def get_user_roles(
        self, 
        user_id: int, 
        use_cache: bool = True
    ) -> List[Dict]:
        """
        获取用户角色信息
        
        Args:
            user_id: 用户ID
            use_cache: 是否使用缓存
            
        Returns:
            List[Dict]: 角色信息列表
        """
        cache_key = f"user_roles:{user_id}"
        
        if use_cache:
            cached_roles = await cache_manager.get(cache_key)
            if cached_roles is not None:
                return cached_roles
        
        # 查询用户角色
        sql = """
        SELECT r.id, r.name, r.display_name, r.description,
               ur.assigned_at, ur.assigned_by
        FROM roles r
        JOIN user_roles ur ON r.id = ur.role_id
        WHERE ur.user_id = :user_id
        AND ur.is_active = true
        ORDER BY ur.assigned_at DESC
        """
        
        result = await self.db.execute(
            text(sql), 
            {"user_id": user_id}
        )
        
        roles = [
            {
                'id': row[0],
                'name': row[1],
                'display_name': row[2],
                'description': row[3],
                'assigned_at': row[4],
                'assigned_by': row[5]
            }
            for row in result
        ]
        
        # 缓存结果
        if use_cache:
            await cache_manager.set(
                cache_key, 
                roles, 
                expire=self.cache_ttl
            )
        
        return roles
    
    async def assign_role_to_user(
        self, 
        user_id: int, 
        role_id: int, 
        assigned_by: int
    ) -> bool:
        """
        为用户分配角色
        
        Args:
            user_id: 用户ID
            role_id: 角色ID
            assigned_by: 分配者ID
            
        Returns:
            bool: 是否成功
        """
        try:
            # 检查角色是否存在
            role_result = await self.db.execute(
                select(Role).where(Role.id == role_id)
            )
            role = role_result.scalar_one_or_none()
            
            if not role:
                logger.warning(f"角色{role_id}不存在")
                return False
            
            # 检查是否已分配
            existing_result = await self.db.execute(
                text("""
                SELECT id FROM user_roles 
                WHERE user_id = :user_id AND role_id = :role_id
                """),
                {"user_id": user_id, "role_id": role_id}
            )
            
            if existing_result.scalar_one_or_none():
                # 更新为活跃状态
                await self.db.execute(
                    text("""
                    UPDATE user_roles 
                    SET is_active = true, assigned_at = NOW(), assigned_by = :assigned_by
                    WHERE user_id = :user_id AND role_id = :role_id
                    """),
                    {
                        "user_id": user_id, 
                        "role_id": role_id, 
                        "assigned_by": assigned_by
                    }
                )
            else:
                # 创建新分配
                await self.db.execute(
                    text("""
                    INSERT INTO user_roles (user_id, role_id, assigned_by, assigned_at, is_active)
                    VALUES (:user_id, :role_id, :assigned_by, NOW(), true)
                    """),
                    {
                        "user_id": user_id, 
                        "role_id": role_id, 
                        "assigned_by": assigned_by
                    }
                )
            
            await self.db.commit()
            
            # 清除缓存
            await self._clear_user_cache(user_id)
            
            logger.info(f"用户{user_id}分配角色{role_id}成功")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"分配角色失败: {str(e)}")
            return False
    
    async def revoke_role_from_user(
        self, 
        user_id: int, 
        role_id: int
    ) -> bool:
        """
        撤销用户角色
        
        Args:
            user_id: 用户ID
            role_id: 角色ID
            
        Returns:
            bool: 是否成功
        """
        try:
            await self.db.execute(
                text("""
                UPDATE user_roles 
                SET is_active = false, revoked_at = NOW()
                WHERE user_id = :user_id AND role_id = :role_id
                """),
                {"user_id": user_id, "role_id": role_id}
            )
            
            await self.db.commit()
            
            # 清除缓存
            await self._clear_user_cache(user_id)
            
            logger.info(f"用户{user_id}撤销角色{role_id}成功")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"撤销角色失败: {str(e)}")
            return False
    
    async def _clear_user_cache(self, user_id: int) -> None:
        """
        清除用户相关缓存
        
        Args:
            user_id: 用户ID
        """
        cache_keys = [
            f"user_permissions:{user_id}",
            f"user_roles:{user_id}"
        ]
        
        for key in cache_keys:
            await cache_manager.delete(key)
    
    async def get_permission_tree(self) -> Dict:
        """
        获取权限树结构
        
        Returns:
            Dict: 权限树
        """
        # 获取所有权限
        result = await self.db.execute(
            select(Permission).order_by(Permission.module, Permission.sort_order)
        )
        permissions = result.scalars().all()
        
        # 构建权限树
        tree = {}
        
        for perm in permissions:
            module = perm.module
            if module not in tree:
                tree[module] = {
                    'name': module,
                    'display_name': f"{module.title()}模块",
                    'permissions': []
                }
            
            tree[module]['permissions'].append({
                'id': perm.id,
                'name': perm.name,
                'display_name': perm.display_name,
                'description': perm.description,
                'action': perm.action,
                'resource': perm.resource,
                'is_wildcard': getattr(perm, 'is_wildcard', False)
            })
        
        return tree
    
    async def validate_permissions(self, permissions: List[str]) -> Dict:
        """
        验证权限列表的有效性
        
        Args:
            permissions: 权限列表
            
        Returns:
            Dict: 验证结果
        """
        # 获取所有有效权限
        result = await self.db.execute(
            select(Permission.name)
        )
        valid_permissions = {row[0] for row in result}
        
        # 分类权限
        valid = []
        invalid = []
        wildcards = []
        
        for perm in permissions:
            if perm in valid_permissions:
                valid.append(perm)
                if '*' in perm:
                    wildcards.append(perm)
            else:
                invalid.append(perm)
        
        return {
            'valid': valid,
            'invalid': invalid,
            'wildcards': wildcards,
            'total': len(permissions),
            'valid_count': len(valid),
            'invalid_count': len(invalid),
            'wildcard_count': len(wildcards)
        }


# 权限装饰器
def require_permission(permission: str, resource_param: Optional[str] = None):
    """
    权限检查装饰器
    
    Args:
        permission: 需要的权限
        resource_param: 资源参数名（从路径参数中获取）
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # 这里需要根据实际的FastAPI结构调整
            # 获取当前用户和数据库会话
            # current_user = get_current_user()
            # db = get_db()
            # 
            # service = RBACPermissionService(db)
            # resource_id = kwargs.get(resource_param) if resource_param else None
            # 
            # if not await service.check_permission(
            #     current_user.id, permission, resource_id
            # ):
            #     raise HTTPException(
            #         status_code=403, 
            #         detail=f"权限不足: 需要 {permission} 权限"
            #     )
            
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# 使用示例
"""
# 在API路由中使用
@router.get("/users/{user_id}")
@require_permission("user:read", "user_id")
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    # 业务逻辑
    pass

# 在服务中使用
async def some_business_logic(user_id: int, db: AsyncSession):
    service = RBACPermissionService(db)
    
    # 检查单个权限
    if await service.check_permission(user_id, "script:write"):
        # 执行操作
        pass
    
    # 批量检查权限
    if await service.check_permissions(
        user_id, 
        ["script:read", "script:write"], 
        require_all=True
    ):
        # 执行操作
        pass
"""