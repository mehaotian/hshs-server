from datetime import timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import AuthManager, get_current_user, get_current_active_user
from app.core.response import ResponseBuilder
from app.core.logger import logger
from app.core.config import settings
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import (
    Token, RefreshToken, UserLogin, UserRegister,
    PasswordReset, PasswordResetConfirm, PasswordChange
)
from app.services.user import UserService

router = APIRouter(prefix="/auth", tags=["认证授权"])
auth_manager = AuthManager()


@router.post("/register", response_model=UserResponse, summary="用户注册")
async def register(
    register_data: UserRegister,
    db: AsyncSession = Depends(get_db)
):
    """用户注册"""
    try:
        user_service = UserService(db)
        
        # 检查用户名是否已存在
        existing_user = await user_service.get_user_by_username(register_data.username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )
        
        # 检查邮箱是否已存在
        existing_email = await user_service.get_user_by_email(register_data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已被注册"
            )
        
        # 创建用户数据
        user_create = UserCreate(
            username=register_data.username,
            email=register_data.email,
            password=register_data.password,
            full_name=register_data.full_name
        )
        
        # 创建用户
        user = await user_service.create_user(user_create)
        
        logger.log_security_event(
            "user_registered",
            user_id=user.id,
            details={
                "username": user.username,
                "email": user.email,
                "registration_ip": "unknown"  # 可以从请求中获取IP
            }
        )
        
        return ResponseBuilder.created(
            data=user,
            message="用户注册成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="注册失败，请稍后重试"
        )


@router.post("/login", response_model=Token, summary="用户登录")
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """用户登录"""
    try:
        user_service = UserService(db)
        
        # 验证用户凭据
        user = await user_service.authenticate_user(
            login_data.username, 
            login_data.password
        )
        
        if not user:
            logger.log_auth_attempt(
                login_data.username,
                success=False,
                reason="invalid_credentials"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            logger.log_auth_attempt(
                login_data.username,
                success=False,
                reason="user_inactive"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户账户已被禁用"
            )
        
        # 生成访问令牌
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth_manager.create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires
        )
        
        # 生成刷新令牌
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = auth_manager.create_refresh_token(
            data={"sub": str(user.id)},
            expires_delta=refresh_token_expires
        )
        
        logger.log_auth_attempt(
            login_data.username,
            success=True,
            user_id=user.id
        )
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败，请稍后重试"
        )


@router.post("/login/form", response_model=Token, summary="表单登录")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """OAuth2 表单登录（兼容标准OAuth2流程）"""
    try:
        user_service = UserService(db)
        
        # 验证用户凭据
        user = await user_service.authenticate_user(
            form_data.username, 
            form_data.password
        )
        
        if not user:
            logger.log_auth_attempt(
                form_data.username,
                success=False,
                reason="invalid_credentials"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            logger.log_auth_attempt(
                form_data.username,
                success=False,
                reason="user_inactive"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户账户已被禁用"
            )
        
        # 生成访问令牌
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth_manager.create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires
        )
        
        # 生成刷新令牌
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        refresh_token = auth_manager.create_refresh_token(
            data={"sub": str(user.id)},
            expires_delta=refresh_token_expires
        )
        
        logger.log_auth_attempt(
            form_data.username,
            success=True,
            user_id=user.id
        )
        
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Form login failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败，请稍后重试"
        )


@router.post("/refresh", response_model=Token, summary="刷新令牌")
async def refresh_token(
    token_data: RefreshToken,
    db: AsyncSession = Depends(get_db)
):
    """使用刷新令牌获取新的访问令牌"""
    try:
        # 验证刷新令牌
        payload = auth_manager.verify_refresh_token(token_data.refresh_token)
        user_id = int(payload.get("sub"))
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌"
            )
        
        # 获取用户信息
        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)
        
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在或已被禁用"
            )
        
        # 生成新的访问令牌
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = auth_manager.create_access_token(
            data={"sub": str(user.id)},
            expires_delta=access_token_expires
        )
        
        # 可选：生成新的刷新令牌
        refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        new_refresh_token = auth_manager.create_refresh_token(
            data={"sub": str(user.id)},
            expires_delta=refresh_token_expires
        )
        
        logger.log_security_event(
            "token_refreshed",
            user_id=user.id,
            details={"username": user.username}
        )
        
        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌刷新失败"
        )


@router.post("/logout", summary="用户登出")
async def logout(
    current_user: User = Depends(get_current_active_user)
):
    """用户登出（客户端需要删除本地令牌）"""
    try:
        logger.log_security_event(
            "user_logout",
            user_id=current_user.id,
            details={"username": current_user.username}
        )
        
        return ResponseBuilder.success(
            message="登出成功"
        )
        
    except Exception as e:
        logger.error(f"Logout failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登出失败"
        )


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """获取当前登录用户的详细信息"""
    return ResponseBuilder.success(
        data=current_user,
        message="获取用户信息成功"
    )


@router.post("/change-password", summary="修改密码")
async def change_password(
    password_data: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """修改当前用户密码"""
    try:
        user_service = UserService(db)
        
        # 验证当前密码
        if not auth_manager.verify_password(password_data.current_password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="当前密码错误"
            )
        
        # 更新密码
        from app.schemas.user import UserPasswordUpdate
        password_update = UserPasswordUpdate(
            current_password=password_data.current_password,
            new_password=password_data.new_password
        )
        
        await user_service.update_password(current_user.id, password_update)
        
        logger.log_security_event(
            "password_changed",
            user_id=current_user.id,
            details={"username": current_user.username}
        )
        
        return ResponseBuilder.success(
            message="密码修改成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Change password failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="密码修改失败"
        )


@router.post("/forgot-password", summary="忘记密码")
async def forgot_password(
    request_data: PasswordReset,
    db: AsyncSession = Depends(get_db)
):
    """发送密码重置邮件"""
    try:
        user_service = UserService(db)
        
        # 查找用户
        user = await user_service.get_user_by_email(request_data.email)
        
        if user:
            # 生成重置令牌（这里简化处理，实际应该生成临时令牌并发送邮件）
            reset_token = auth_manager.create_access_token(
                data={"sub": str(user.id), "type": "password_reset"},
                expires_delta=timedelta(hours=1)  # 1小时有效期
            )
            
            logger.log_security_event(
                "password_reset_requested",
                user_id=user.id,
                details={
                    "email": request_data.email,
                    "username": user.username
                }
            )
            
            # TODO: 发送重置邮件
            # await send_password_reset_email(user.email, reset_token)
        
        # 无论用户是否存在，都返回成功消息（安全考虑）
        return ResponseBuilder.success(
            message="如果该邮箱已注册，您将收到密码重置邮件"
        )
        
    except Exception as e:
        logger.error(f"Forgot password failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="密码重置请求失败"
        )


@router.post("/reset-password", summary="重置密码")
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db)
):
    """使用重置令牌重置密码"""
    try:
        # 验证重置令牌
        payload = auth_manager.verify_token(reset_data.token)
        user_id = int(payload.get("sub"))
        token_type = payload.get("type")
        
        if user_id is None or token_type != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的重置令牌"
            )
        
        # 获取用户
        user_service = UserService(db)
        user = await user_service.get_user_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户不存在"
            )
        
        # 更新密码
        new_password_hash = auth_manager.get_password_hash(reset_data.new_password)
        from app.schemas.user import UserUpdate
        user_update = UserUpdate(password_hash=new_password_hash)
        
        await user_service.update_user(user_id, user_update)
        
        logger.log_security_event(
            "password_reset_completed",
            user_id=user.id,
            details={"username": user.username}
        )
        
        return ResponseBuilder.success(
            message="密码重置成功"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset password failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="密码重置失败"
        )


@router.get("/verify-token", summary="验证令牌")
async def verify_token(
    current_user: User = Depends(get_current_user)
):
    """验证当前令牌是否有效"""
    return ResponseBuilder.success(
        data={
            "valid": True,
            "user_id": current_user.id,
            "username": current_user.username
        },
        message="令牌验证成功"
    )