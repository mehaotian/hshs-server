from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta

from app.models.user import User, UserProfile
from app.models.role import UserRole, Role
from app.models.department import DepartmentMember
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
        
        # 如果指定了部门，检查部门是否存在
        if user_data.dept_id:
            from app.models.department import Department
            dept_result = await self.db.execute(
                select(Department).where(
                    and_(
                        Department.id == user_data.dept_id,
                        Department.status == Department.STATUS_ACTIVE
                    )
                )
            )
            department = dept_result.scalar_one_or_none()
            if not department:
                raise_not_found("Department", user_data.dept_id)
        
        # 创建用户
        user_dict = user_data.model_dump(exclude={"password", "confirm_password", "dept_id"})
        user_dict["password_hash"] = AuthManager.get_password_hash(user_data.password)
        
        user = User(**user_dict)
        
        try:
            self.db.add(user)
            await self.db.flush()  # 获取用户ID但不提交事务
            
            # 如果指定了部门，创建部门成员关联
            if user_data.dept_id:
                from app.models.department import DepartmentMember, PositionType
                dept_member = DepartmentMember(
                    department_id=user_data.dept_id,
                    user_id=user.id,
                    position_type=PositionType.MEMBER,
                    status=DepartmentMember.STATUS_ACTIVE
                )
                self.db.add(dept_member)
            
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
        from app.models.role import UserRole, Role
        
        result = await self.db.execute(
            select(User)
            .options(
                selectinload(User.profile),
                selectinload(User.user_roles).selectinload(UserRole.role)
            )
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
        
        # 如果要更新部门，检查部门是否存在
        if hasattr(user_data, 'dept_id') and user_data.dept_id is not None:
            from app.models.department import Department
            dept_result = await self.db.execute(
                select(Department).where(
                    and_(
                        Department.id == user_data.dept_id,
                        Department.status == Department.STATUS_ACTIVE
                    )
                )
            )
            department = dept_result.scalar_one_or_none()
            if not department:
                raise_not_found("Department", user_data.dept_id)
        
        # 更新用户信息
        update_data = user_data.model_dump(exclude_unset=True, exclude={'dept_id'})
        
        try:
            # 更新用户基本信息
            await self.db.execute(
                update(User)
                .where(User.id == user_id)
                .values(**update_data)
            )
            
            # 处理部门更新
            if hasattr(user_data, 'dept_id'):
                from app.models.department import DepartmentMember, PositionType
                
                # 先删除现有的部门关联（设置为离职状态）
                await self.db.execute(
                    update(DepartmentMember)
                    .where(
                        and_(
                            DepartmentMember.user_id == user_id,
                            DepartmentMember.status == DepartmentMember.STATUS_ACTIVE
                        )
                    )
                    .values(
                        status=DepartmentMember.STATUS_INACTIVE,
                        left_at=func.now()
                    )
                )
                
                # 如果指定了新部门，创建新的部门关联
                if user_data.dept_id:
                    dept_member = DepartmentMember(
                        department_id=user_data.dept_id,
                        user_id=user_id,
                        position_type=PositionType.MEMBER,
                        status=DepartmentMember.STATUS_ACTIVE
                    )
                    self.db.add(dept_member)
            
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
    
    async def update_user_status(self, user_id: int, status: int) -> User:
        """更新用户状态（启用/禁用/暂停/删除）"""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise_not_found("User", user_id)
        
        try:
            # 更新用户状态
            await self.db.execute(
                update(User)
                .where(User.id == user_id)
                .values(status=status)
            )
            
            await self.db.commit()
            
            # 重新获取更新后的用户
            result = await self.db.execute(
                select(User)
                .options(selectinload(User.profile))
                .where(User.id == user_id)
            )
            updated_user = result.scalar_one()
            
            status_map = {
                1: "启用",
                0: "禁用", 
                -1: "暂停",
                -2: "删除"
            }
            status_text = status_map.get(status, "未知")
            logger.info(f"User {status_text}: {user.username} (ID: {user_id})")
            return updated_user
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update user status {user_id}: {str(e)}")
            raise_business_error("Failed to update user status")
    
    async def delete_user(self, user_id: int) -> bool:
        """删除用户"""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise_not_found("User", user_id)
        
        try:
            # 1. 删除用户的部门成员关系
            await self.db.execute(
                delete(DepartmentMember).where(DepartmentMember.user_id == user_id)
            )
            
            # 2. 删除用户的角色关系
            await self.db.execute(
                delete(UserRole).where(UserRole.user_id == user_id)
            )
            
            # 3. 删除用户档案（如果存在）
            await self.db.execute(
                delete(UserProfile).where(UserProfile.user_id == user_id)
            )
            
            # 4. 最后删除用户本身
            await self.db.execute(
                delete(User).where(User.id == user_id)
            )
            
            await self.db.commit()
            
            logger.info(f"User deleted: {user.username} (ID: {user_id}) with all related data")
            return True
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete user {user_id}: {str(e)}")
            raise_business_error("删除用户失败")
    
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
            
            # 关键词搜索（用户名、邮箱、真实姓名）
            if search_query.keyword:
                keyword = f"%{search_query.keyword}%"
                conditions.append(
                    or_(
                        User.username.ilike(keyword),
                        User.real_name.ilike(keyword),
                        User.email.ilike(keyword)
                    )
                )
            
            # 真实姓名模糊匹配
            if search_query.username:
                username_pattern = f"%{search_query.username}%"
                conditions.append(User.real_name.ilike(username_pattern))
            
            # 手机号模糊匹配
            if search_query.phone:
                phone_pattern = f"%{search_query.phone}%"
                conditions.append(User.phone.ilike(phone_pattern))
            
            # 性别筛选
            if search_query.sex:
                conditions.append(User.sex == search_query.sex.value)
            
            # 用户状态
            if search_query.status is not None:
                conditions.append(User.status == search_query.status)
            
            # 部门查询
            if search_query.dept_id:
                # 需要关联部门成员表
                query = query.join(
                    DepartmentMember, 
                    and_(
                        User.id == DepartmentMember.user_id,
                        DepartmentMember.department_id == search_query.dept_id,
                        DepartmentMember.status == DepartmentMember.STATUS_ACTIVE
                    )
                )
            
            # 时间范围查询
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
            
            # 关键词搜索
            if search_query.keyword:
                keyword = f"%{search_query.keyword}%"
                conditions.append(
                    or_(
                        User.username.ilike(keyword),
                        User.real_name.ilike(keyword),
                        User.email.ilike(keyword)
                    )
                )
            
            # 真实姓名模糊匹配
            if search_query.username:
                username_pattern = f"%{search_query.username}%"
                conditions.append(User.real_name.ilike(username_pattern))
            
            # 手机号模糊匹配
            if search_query.phone:
                phone_pattern = f"%{search_query.phone}%"
                conditions.append(User.phone.ilike(phone_pattern))
            
            # 性别筛选
            if search_query.sex:
                conditions.append(User.sex == search_query.sex.value)
            
            # 用户状态
            if search_query.status is not None:
                conditions.append(User.status == search_query.status)
            
            # 部门查询
            if search_query.dept_id:
                count_query = count_query.join(
                    DepartmentMember, 
                    and_(
                        User.id == DepartmentMember.user_id,
                        DepartmentMember.department_id == search_query.dept_id,
                        DepartmentMember.status == DepartmentMember.STATUS_ACTIVE
                    )
                )
            
            # 时间范围查询
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
        
        # 批量获取所有用户的角色信息和部门信息
        user_ids = [user.id for user in users]
        user_roles_map = {}
        user_departments_map = {}
        
        if user_ids:
            # 查询所有用户的角色
            roles_result = await self.db.execute(
                select(UserRole.user_id, Role.id, Role.name, Role.display_name)
                .join(Role, UserRole.role_id == Role.id)
                .where(UserRole.user_id.in_(user_ids))
                .where(or_(UserRole.expires_at.is_(None), UserRole.expires_at > func.now()))
            )
            
            # 组织角色数据
            for user_id, role_id, role_name, role_display_name in roles_result:
                if user_id not in user_roles_map:
                    user_roles_map[user_id] = []
                user_roles_map[user_id].append({
                    "id": role_id,
                    "name": role_name,
                    "display_name": role_display_name
                })
            
            # 查询所有用户的部门信息
            from app.models.department import Department
            departments_result = await self.db.execute(
                select(
                    DepartmentMember.user_id,
                    Department.id,
                    Department.name
                )
                .join(Department, DepartmentMember.department_id == Department.id)
                .where(
                    and_(
                        DepartmentMember.user_id.in_(user_ids),
                        DepartmentMember.status == DepartmentMember.STATUS_ACTIVE,
                        Department.status == Department.STATUS_ACTIVE
                    )
                )
            )
            
            # 组织部门数据
            for user_id, dept_id, dept_name in departments_result:
                user_departments_map[user_id] = {
                    "id": dept_id,
                    "name": dept_name
                }
        
        # 转换为UserListResponse格式的字典
        user_list = []
        for user in users:
            user_dict = {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "real_name": user.real_name,
                "phone": user.phone,
                "wechat": user.wechat,
                "sex": user.sex,
                "remark": user.remark,
                "status": user.status,
                "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "roles": user_roles_map.get(user.id, []),
                "department": user_departments_map.get(user.id)
            }
            user_list.append(user_dict)
        
        return user_list, total
    
    async def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """认证用户"""
        user = await AuthManager.authenticate_user(self.db, username, password)
        
        if user:
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
                            .values(status=User.STATUS_ACTIVE)
                        )
                    elif operation.operation == "deactivate":
                        await self.db.execute(
                            update(User)
                            .where(User.id == user_id)
                            .values(status=User.STATUS_INACTIVE)
                        )
                    elif operation.operation == "suspend":
                         await self.db.execute(
                             update(User)
                             .where(User.id == user_id)
                             .values(status=User.STATUS_SUSPENDED)
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
            select(func.count(User.id)).where(User.status == User.STATUS_ACTIVE)
        )
        active_users = active_users_result.scalar()
        
        # 非活跃用户数
        inactive_users_result = await self.db.execute(
            select(func.count(User.id)).where(User.status == User.STATUS_INACTIVE)
        )
        inactive_users = inactive_users_result.scalar()
        
        # 暂停用户数
        suspended_users_result = await self.db.execute(
            select(func.count(User.id)).where(User.status == User.STATUS_SUSPENDED)
        )
        suspended_users = suspended_users_result.scalar()
        
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
            "inactive_users": inactive_users,
            "suspended_users": suspended_users,
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
        """获取用户权限（包括通配符权限）"""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise_not_found("User", user_id)
        
        return await user.get_permissions(self.db)
    
    async def get_user_expanded_permissions(self, user_id: int) -> List[str]:
        """获取用户展开权限列表（将通配符权限展开为具体权限）"""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise_not_found("User", user_id)
        
        return await user.get_expanded_permissions(self.db)