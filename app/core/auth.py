from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.role import UserRole, Role


# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer 认证
security = HTTPBearer()


class AuthManager:
    """认证管理器"""
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """获取密码哈希"""
        return pwd_context.hash(password)
    
    @staticmethod
    def create_access_token(
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.SECRET_KEY, 
            algorithm=settings.ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(
        data: Dict[str, Any], 
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """创建刷新令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh"
        })
        
        encoded_jwt = jwt.encode(
            to_encode, 
            settings.SECRET_KEY, 
            algorithm=settings.ALGORITHM
        )
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
        """验证令牌"""
        try:
            payload = jwt.decode(
                token, 
                settings.SECRET_KEY, 
                algorithms=[settings.ALGORITHM]
            )
            
            # 检查令牌类型
            if payload.get("type") != token_type:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="令牌类型无效",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # 检查过期时间
            exp = payload.get("exp")
            if exp is None or datetime.fromtimestamp(exp) < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="登录已过期",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            return payload
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="登录已过期",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    @staticmethod
    def verify_refresh_token(token: str) -> Dict[str, Any]:
        """验证刷新令牌"""
        return AuthManager.verify_token(token, token_type="refresh")
    
    @staticmethod
    async def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        """获取当前用户"""
        token = credentials.credentials
        payload = AuthManager.verify_token(token)
        
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="登录已过期",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 将字符串类型的用户ID转换为整数
        try:
            user_id: int = int(user_id_str)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="令牌中的用户ID无效",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 查询用户并预加载角色和权限关系
        result = await db.execute(
            select(User)
            .options(
                joinedload(User.user_roles).joinedload(UserRole.role)
            )
            .where(User.id == user_id)
        )
        user = result.unique().scalar_one_or_none()
        
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 检查用户状态
        if not user.is_active:
            # 根据用户状态返回更精确的错误信息
            status_messages = {
                User.STATUS_INACTIVE: "用户账户已被禁用",
                User.STATUS_SUSPENDED: "用户账户已被暂停",
                User.STATUS_DELETED: "用户账户已被删除"
            }
            detail_message = status_messages.get(user.status, "用户账户状态异常")
            
            # 记录详细的认证失败日志
            from app.core.logger import logger
            logger.warning(
                f"User authentication failed - inactive user: {user.id} ({user.username}) - "
                f"Status: {user.status} - Detail: {detail_message}"
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=detail_message,
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
    
    @staticmethod
    async def get_current_active_user(
        current_user: User = Depends(get_current_user)
    ) -> User:
        """获取当前活跃用户"""
        if not current_user.is_active:
            # 根据用户状态返回更精确的错误信息
            status_messages = {
                User.STATUS_INACTIVE: "用户账户已被禁用",
                User.STATUS_SUSPENDED: "用户账户已被暂停",
                User.STATUS_DELETED: "用户账户已被删除"
            }
            detail_message = status_messages.get(current_user.status, "用户账户状态异常")
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail=detail_message
            )
        return current_user
    
    @staticmethod
    async def authenticate_user(
        db: AsyncSession, 
        username: str, 
        password: str
    ) -> Optional[User]:
        """认证用户"""
        # 支持用户名或邮箱登录
        result = await db.execute(
            select(User).where(
                (User.username == username) | (User.email == username)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return None
        
        if not AuthManager.verify_password(password, user.password_hash):
            return None
        
        return user
    
    @staticmethod
    async def check_permission(
        user: User,
        permission: str,
        db: AsyncSession,
        resource_id: Optional[int] = None
    ) -> bool:
        """检查用户权限"""
        # 拥有通配符权限(*)的用户拥有所有权限
        if await user.has_permission("*", db):
            return True
         # 拥有通配符权限(*)的用户拥有所有权限
        if await user.has_permission("super", db):
            return True
        
        
        # 检查用户是否有指定权限
        return await user.has_permission(permission, db)
    
    @staticmethod
    def require_permission(permission: str):
        """权限装饰器"""
        async def permission_checker(
            current_user: User = Depends(get_current_active_user),
            db: AsyncSession = Depends(get_db)
        ) -> User:
            has_permission = await AuthManager.check_permission(
                current_user, permission, db
            )
            
            if not has_permission:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="权限不足"
                )
            
            return current_user
        
        return permission_checker
    
    @staticmethod
    def require_role(role: str):
        """角色装饰器"""
        async def role_checker(
            current_user: User = Depends(get_current_active_user),
            db: AsyncSession = Depends(get_db)
        ) -> User:
            has_role = await current_user.has_role(role, db)
            
            if not has_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"需要'{role}'角色权限"
                )
            
            return current_user
        
        return role_checker
    
    @staticmethod
    def require_roles(*roles: str):
        """多角色装饰器（满足其中一个即可）"""
        async def roles_checker(
            current_user: User = Depends(get_current_active_user),
            db: AsyncSession = Depends(get_db)
        ) -> User:
            user_roles = await current_user.get_roles(db)
            user_role_names = [role.name for role in user_roles]
            
            has_any_role = any(role in user_role_names for role in roles)
            
            if not has_any_role:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"One of roles {roles} required"
                )
            
            return current_user
        
        return roles_checker
    
    @staticmethod
    async def get_user_permissions(
        user: User, 
        db: AsyncSession
    ) -> List[str]:
        """获取用户所有权限"""
        return await user.get_permissions(db)
    
    @staticmethod
    async def get_user_roles(
        user: User, 
        db: AsyncSession
    ) -> List[str]:
        """获取用户所有角色"""
        roles = await user.get_roles(db)
        return [role.name for role in roles]
    
    @staticmethod
    def create_token_response(
        user: User, 
        access_token: str, 
        refresh_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建令牌响应"""
        response = {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": user.to_dict()
        }
        
        if refresh_token:
            response["refresh_token"] = refresh_token
        
        return response


# 常用依赖项
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """获取当前用户"""
    return await AuthManager.get_current_user(credentials, db)

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前活跃用户"""
    return await AuthManager.get_current_active_user(current_user)

# 权限和角色检查函数
def require_permission(permission: str):
    """权限装饰器"""
    return AuthManager.require_permission(permission)

def require_role(role: str):
    """角色装饰器"""
    return AuthManager.require_role(role)

def require_roles(*roles: str):
    """多角色装饰器（满足其中一个即可）"""
    return AuthManager.require_roles(*roles)


# 预定义的角色检查器函数
def require_admin():
    return require_role("admin")

def require_super_admin():
    return require_permission("*")

def require_director():
    return require_role("director")

def require_scriptwriter():
    return require_role("scriptwriter")

def require_cv():
    return require_role("cv")

def require_reviewer():
    return require_roles("first_reviewer", "second_reviewer")

def require_post_production():
    return require_role("post_production")

# 预定义的权限检查器函数
def require_user_read():
    return require_permission("user:read")

def require_user_write():
    return require_permission("user:write")

def require_user_delete():
    return require_permission("user:delete")

def require_script_read():
    return require_permission("script:read")

def require_script_write():
    return require_permission("script:write")

def require_script_delete():
    return require_permission("script:delete")

def require_audio_read():
    return require_permission("audio:read")

def require_audio_write():
    return require_permission("audio:write")

def require_audio_review():
    return require_permission("audio:review")

def require_system_manage():
    return require_permission("system:manage")