# -*- coding: utf-8 -*-
"""
Pytest 配置文件

包含测试夹具、数据库设置、认证配置等公共测试配置
"""

import asyncio
import os
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.core.database import Base, get_db
from app.core.auth import AuthManager
from app.models.user import User
from app.models.role import Role
from app.services.user import UserService
from app.services.role import RoleService
from main import create_app

# 设置测试环境变量
os.environ["TESTING"] = "true"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"

# 测试数据库引擎
test_engine = create_async_engine(
    "sqlite+aiosqlite:///./test.db",
    echo=False,
    poolclass=StaticPool,
    connect_args={
        "check_same_thread": False,
    },
)

# 测试会话工厂
TestSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """
    创建事件循环用于整个测试会话
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    创建测试数据库会话
    """
    # 创建所有表
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # 创建会话
    async with TestSessionLocal() as session:
        yield session
    
    # 清理数据库
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def app(db_session: AsyncSession) -> FastAPI:
    """
    创建测试 FastAPI 应用
    """
    app = create_app()
    
    # 覆盖数据库依赖
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """
    创建测试客户端
    """
    return TestClient(app)


@pytest.fixture
def auth_manager() -> AuthManager:
    """
    创建认证管理器
    """
    return AuthManager()


@pytest_asyncio.fixture
async def user_service(db_session: AsyncSession) -> UserService:
    """
    创建用户服务
    """
    return UserService(db_session)


@pytest_asyncio.fixture
async def role_service(db_session: AsyncSession) -> RoleService:
    """
    创建角色服务
    """
    return RoleService(db_session)


@pytest_asyncio.fixture
async def test_role(db_session: AsyncSession, role_service: RoleService) -> Role:
    """
    创建测试角色
    """
    role_data = {
        "name": "测试角色",
        "description": "用于测试的角色",
        "permissions": ["test:read", "test:write"]
    }
    return await role_service.create_role(role_data)


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession, user_service: UserService, test_role: Role) -> User:
    """
    创建测试用户
    """
    user_data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
        "nickname": "测试用户"
    }
    user = await user_service.create_user(user_data)
    
    # 分配角色
    await user_service.assign_role(user.id, test_role.id)
    
    return user


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession, user_service: UserService) -> User:
    """
    创建管理员用户
    """
    user_data = {
        "username": "admin",
        "email": "admin@example.com",
        "password": "adminpassword123",
        "nickname": "管理员",
        "is_superuser": True
    }
    return await user_service.create_user(user_data)


@pytest.fixture
def test_user_token(auth_manager: AuthManager, test_user: User) -> str:
    """
    创建测试用户的访问令牌
    """
    return auth_manager.create_access_token(
        data={"sub": str(test_user.id), "username": test_user.username}
    )


@pytest.fixture
def admin_user_token(auth_manager: AuthManager, admin_user: User) -> str:
    """
    创建管理员用户的访问令牌
    """
    return auth_manager.create_access_token(
        data={"sub": str(admin_user.id), "username": admin_user.username}
    )


@pytest.fixture
def auth_headers(test_user_token: str) -> dict:
    """
    创建认证请求头
    """
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest.fixture
def admin_auth_headers(admin_user_token: str) -> dict:
    """
    创建管理员认证请求头
    """
    return {"Authorization": f"Bearer {admin_user_token}"}


# 测试数据工厂
class TestDataFactory:
    """
    测试数据工厂类
    """
    
    @staticmethod
    def user_data(username: str = "testuser", email: str = "test@example.com") -> dict:
        """
        生成用户测试数据
        """
        return {
            "username": username,
            "email": email,
            "password": "testpassword123",
            "nickname": f"{username}的昵称"
        }
    
    @staticmethod
    def role_data(name: str = "测试角色") -> dict:
        """
        生成角色测试数据
        """
        return {
            "name": name,
            "description": f"{name}的描述",
            "permissions": ["test:read", "test:write"]
        }
    
    @staticmethod
    def script_data(title: str = "测试剧本") -> dict:
        """
        生成剧本测试数据
        """
        return {
            "title": title,
            "description": f"{title}的描述",
            "content": "这是一个测试剧本的内容",
            "tags": ["测试", "剧本"]
        }
    
    @staticmethod
    def audio_data(title: str = "测试音频") -> dict:
        """
        生成音频测试数据
        """
        return {
            "title": title,
            "description": f"{title}的描述",
            "file_name": "test_audio.wav",
            "file_size": 1024000,
            "duration": 60
        }


@pytest.fixture
def test_data_factory() -> TestDataFactory:
    """
    提供测试数据工厂
    """
    return TestDataFactory()


# 测试标记
pytestmark = pytest.mark.asyncio