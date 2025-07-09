from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta

from app.models.user import User, UserProfile
from app.models.role import UserRole, Role
from app.schemas.user import (
    UserCreate, UserUpdate, UserPasswordUpdate, UserSearchQuery,
    UserProfileCreate, UserProfileUpdate, UserBatchOperation
)
from app.core.auth import AuthManager
from app.core.exceptions import (
    raise_not_found, raise_duplicate, raise_validation_error,
    raise_auth_error, raise_business_error
)
from app.core.logger import logger, log_database_query
from app.core.database import DatabaseManager


class UserService:
    """用户服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.db_manager = DatabaseManager()
    
    async def create_user(self, user_data: UserCreate) -> User:
        """创建用户"""
        # 检查用户名是否已存在
        existing_user = await self.get_user_by_username(user_data.username)
        if existing_user:
            raise_duplicate("User", "username", user_data.username)
        
        # 检查邮箱是否已存在
        existing_email = await self.get_user_by_email(user_data.email)
        if existing_email:
            raise_duplicate("User", "email", user_data.email)
        
        # 创建用户
        user_dict = user_data.model_dump(exclude={"password", "confirm_password"})
        user_dict["password_hash"] = AuthManager.get_password_hash(user_data.password)
        
        user = User(**user_dict)
        
        try:
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            
            logger.info(f"User created: {user.username} (ID: {user.id})")
            return user
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create user: {str(e)}")
            raise_business_error("Failed to create user")
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """根据ID获取用户"""
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.profile))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        result = await self.db.execute(
            select(User).where(User.username == username)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """根据邮箱获取用户"""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def update_user(self, user_id: int, user_data: UserUpdate) -> User:
        """更新用户信息"""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise_not_found("User", user_id)
        
        # 检查用户名是否重复（如果要更新用户名）
        if user_data.username and user_data.username != user.username:
            existing_user = await self.get_user_by_username(user_data.username)
            if existing_user:
                raise_duplicate("User", "username", user_data.username)
        
        # 检查邮箱是否重复（如果要更新邮箱）
        if user_data.email and user_data.email != user.email:
            existing_email = await self.get_user_by_email(user_data.email)
            if existing_email:
                raise_duplicate("User", "email", user_data.email)
        
        # 更新用户信息
        update_data = user_data.model_dump(exclude_unset=True)
        
        try:
            await self.db.execute(
                update(User)
                .where(User.id == user_id)
                .values(**update_data)
            )
            await self.db.commit()
            
            # 重新获取更新后的用户
            updated_user = await self.get_user_by_id(user_id)
            
            logger.info(f"User updated: {user.username} (ID: {user_id})")
            return updated_user
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update user {user_id}: {str(e)}")
            raise_business_error("Failed to update user")
    
    async def update_password(self, user_id: int, password_data: UserPasswordUpdate) -> bool:
        """更新用户密码"""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise_not_found("User", user_id)
        
        # 验证当前密码
        if not AuthManager.verify_password(password_data.current_password, user.password_hash):
            raise_auth_error("Current password is incorrect")
        
        # 更新密码
        new_password_hash = AuthManager.get_password_hash(password_data.new_password)
        
        try:
            await self.db.execute(
                update(User)
                .where(User.id == user_id)
                .values(password_hash=new_password_hash)
            )
            await self.db.commit()
            
            logger.info(f"Password updated for user: {user.username} (ID: {user_id})")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update password for user {user_id}: {str(e)}")
            raise_business_error("Failed to update password")
    
    async def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise_not_found("User", user_id)
        
        try:
            await self.db.execute(
                delete(User).where(User.id == user_id)
            )
            await self.db.commit()
            
            logger.info(f"User deleted: {user.username} (ID: {user_id})")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete user {user_id}: {str(e)}")
            raise_business_error("Failed to delete user")
    
    async def get_users(
        self, 
        page: int = 1, 
        size: int = 20,
        search_query: Optional[UserSearchQuery] = None
    ) -> Tuple[List[User], int]:
        """获取用户列表"""
        query = select(User).options(selectinload(User.profile))
        
        # 构建搜索条件
        if search_query:
            conditions = []
            
            if search_query.keyword:
                keyword = f"%{search_query.keyword}%"
                conditions.append(
                    or_(
                        User.username.ilike(keyword),
                        User.real_name.ilike(keyword),
                        User.email.ilike(keyword)
                    )
                )
            
            if search_query.status:
                conditions.append(User.status == search_query.status)
            
            if search_query.created_after:
                conditions.append(User.created_at >= search_query.created_after)
            
            if search_query.created_before:
                conditions.append(User.created_at <= search_query.created_before)
            
            if conditions:
                query = query.where(and_(*conditions))
        
        # 排序
        if search_query and search_query.order_by:
            if search_query.order_desc:
                query = query.order_by(getattr(User, search_query.order_by).desc())
            else:
                query = query.order_by(getattr(User, search_query.order_by))
        else:
            query = query.order_by(User.created_at.desc())
        
        # 获取总数
        count_query = select(func.count(User.id))
        if search_query:
            # 应用相同的搜索条件
            conditions = []
            if search_query.keyword:
                keyword = f"%{search_query.keyword}%"
                conditions.append(
                    or_(
                        User.username.ilike(keyword),
                        User.real_name.ilike(keyword),
                        User.email.ilike(keyword)
                    )
                )
            if search_query.status:
                conditions.append(User.status == search_query.status)
            if search_query.created_after:
                conditions.append(User.created_at >= search_query.created_after)
            if search_query.created_before:
                conditions.append(User.created_at <= search_query.created_before)
            
            if conditions:
                count_query = count_query.where(and_(*conditions))
        
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()
        
        # 分页
        offset = (page - 1) * size
        query = query.offset(offset).limit(size)
        
        result = await self.db.execute(query)
        users = result.scalars().all()
        
        # 转换为UserListResponse格式的字典
        user_list = []
        for user in users:
            user_dict = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "real_name": user.real_name,
                "status": user.status,
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "roles": []  # TODO: 需要加载用户角色
            }
            user_list.append(user_dict)
        
        return user_list, total
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """认证用户"""
        user = await AuthManager.authenticate_user(self.db, username, password)
        
        if user:
            # 更新最后登录时间
            user.last_login = datetime.utcnow()
            await self.db.commit()
            logger.info(f"User authenticated: {user.username} (ID: {user.id})")
        
        return user
    
    async def create_user_profile(self, user_id: int, profile_data: UserProfileCreate) -> UserProfile:
        """创建用户档案"""
        # 检查用户是否存在
        user = await self.get_user_by_id(user_id)
        if not user:
            raise_not_found("User", user_id)
        
        # 检查是否已有档案
        existing_profile = await self.get_user_profile(user_id)
        if existing_profile:
            raise_duplicate("UserProfile", "user_id", str(user_id))
        
        # 创建档案
        profile_dict = profile_data.dict()
        profile_dict["user_id"] = user_id
        
        profile = UserProfile(**profile_dict)
        
        try:
            self.db.add(profile)
            await self.db.commit()
            await self.db.refresh(profile)
            
            logger.info(f"User profile created for user: {user.username} (ID: {user_id})")
            return profile
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to create user profile for user {user_id}: {str(e)}")
            raise_business_error("Failed to create user profile")
    
    async def get_user_profile(self, user_id: int) -> Optional[UserProfile]:
        """获取用户档案"""
        result = await self.db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def update_user_profile(self, user_id: int, profile_data: UserProfileUpdate) -> UserProfile:
        """更新用户档案"""
        profile = await self.get_user_profile(user_id)
        if not profile:
            raise_not_found("UserProfile", user_id)
        
        # 更新档案信息
        update_data = profile_data.dict(exclude_unset=True)
        
        try:
            await self.db.execute(
                update(UserProfile)
                .where(UserProfile.user_id == user_id)
                .values(**update_data)
            )
            await self.db.commit()
            
            # 重新获取更新后的档案
            updated_profile = await self.get_user_profile(user_id)
            
            logger.info(f"User profile updated for user ID: {user_id}")
            return updated_profile
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update user profile for user {user_id}: {str(e)}")
            raise_business_error("Failed to update user profile")
    
    async def batch_operation(self, operation: UserBatchOperation) -> Dict[str, Any]:
        """批量操作用户"""
        results = {
            "success_count": 0,
            "failed_count": 0,
            "errors": []
        }
        
        try:
            for user_id in operation.user_ids:
                try:
                    if operation.operation == "activate":
                        await self.db.execute(
                            update(User)
                            .where(User.id == user_id)
                            .values(status="active")
                        )
                    elif operation.operation == "deactivate":
                        await self.db.execute(
                            update(User)
                            .where(User.id == user_id)
                            .values(status="inactive")
                        )
                    elif operation.operation == "delete":
                        await self.db.execute(
                            delete(User).where(User.id == user_id)
                        )
                    
                    results["success_count"] += 1
                    
                except Exception as e:
                    results["failed_count"] += 1
                    results["errors"].append({
                        "user_id": user_id,
                        "error": str(e)
                    })
            
            await self.db.commit()
            
            logger.info(
                f"Batch operation '{operation.operation}' completed: "
                f"{results['success_count']} success, {results['failed_count']} failed"
            )
            
            return results
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Batch operation failed: {str(e)}")
            raise_business_error("Batch operation failed")
    
    async def get_user_statistics(self) -> Dict[str, Any]:
        """获取用户统计信息"""
        # 总用户数
        total_users_result = await self.db.execute(
            select(func.count(User.id))
        )
        total_users = total_users_result.scalar()
        
        # 活跃用户数
        active_users_result = await self.db.execute(
            select(func.count(User.id)).where(User.status == "active")
        )
        active_users = active_users_result.scalar()
        
        # 今日新增用户
        today = datetime.utcnow().date()
        today_users_result = await self.db.execute(
            select(func.count(User.id)).where(
                func.date(User.created_at) == today
            )
        )
        today_users = today_users_result.scalar()
        
        # 本周新增用户
        week_ago = datetime.utcnow() - timedelta(days=7)
        week_users_result = await self.db.execute(
            select(func.count(User.id)).where(
                User.created_at >= week_ago
            )
        )
        week_users = week_users_result.scalar()
        
        # 按状态统计
        status_stats_result = await self.db.execute(
            select(User.status, func.count(User.id))
            .group_by(User.status)
        )
        status_stats = dict(status_stats_result.all())
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "today_new_users": today_users,
            "week_new_users": week_users,
            "status_distribution": status_stats,
            "activity_rate": round(active_users / total_users * 100, 2) if total_users > 0 else 0
        }
    
    async def search_users_by_role(self, role_name: str) -> List[User]:
        """根据角色搜索用户"""
        result = await self.db.execute(
            select(User)
            .join(UserRole, User.id == UserRole.user_id)
            .join(Role, UserRole.role_id == Role.id)
            .where(Role.name == role_name)
            .options(selectinload(User.profile))
        )
        return list(result.scalars().all())
    
    async def get_user_roles(self, user_id: int) -> List[str]:
        """获取用户角色"""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise_not_found("User", user_id)
        
        return await user.get_roles(self.db)
    
    async def get_user_permissions(self, user_id: int) -> List[str]:
        """获取用户权限"""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise_not_found("User", user_id)
        
        return await user.get_permissions(self.db)