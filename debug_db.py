#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接和用户创建调试脚本
"""

import asyncio
import sys
import traceback
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# 添加项目根目录到 Python 路径
sys.path.insert(0, '.')

from app.core.database import get_db, AsyncSessionLocal
from app.services.user import UserService
from app.schemas.user import UserCreate
from app.core.logger import logger


async def test_database_connection():
    """测试数据库连接"""
    try:
        print("测试数据库连接...")
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            print(f"数据库连接成功: {result.scalar()}")
            return True
    except Exception as e:
        print(f"数据库连接失败: {e}")
        traceback.print_exc()
        return False


async def test_user_creation():
    """测试用户创建"""
    try:
        print("\n测试用户创建...")
        
        # 创建数据库会话
        async with AsyncSessionLocal() as session:
            print("数据库会话创建成功")
            
            # 创建用户服务
            user_service = UserService(session)
            print("用户服务创建成功")
            
            # 创建测试用户数据
            user_data = UserCreate(
                username="debug_test_user",
                email="debug@test.com",
                password="Test123456",
                confirm_password="Test123456",
                real_name="Debug Test User"
            )
            print(f"用户数据创建成功: {user_data}")
            
            # 检查用户名是否已存在
            existing_user = await user_service.get_user_by_username(user_data.username)
            if existing_user:
                print(f"用户名已存在，删除旧用户: {existing_user.id}")
                await user_service.delete_user(existing_user.id)
            
            # 检查邮箱是否已存在
            existing_email = await user_service.get_user_by_email(user_data.email)
            if existing_email:
                print(f"邮箱已存在，删除旧用户: {existing_email.id}")
                await user_service.delete_user(existing_email.id)
            
            # 创建用户
            print("开始创建用户...")
            user = await user_service.create_user(user_data)
            print(f"用户创建成功: ID={user.id}, 用户名={user.username}")
            
            return True
            
    except Exception as e:
        print(f"用户创建失败: {e}")
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    print("开始数据库调试...")
    
    # 测试数据库连接
    db_ok = await test_database_connection()
    if not db_ok:
        print("数据库连接失败，退出")
        return
    
    # 测试用户创建
    user_ok = await test_user_creation()
    if user_ok:
        print("\n✅ 所有测试通过")
    else:
        print("\n❌ 用户创建测试失败")


if __name__ == "__main__":
    asyncio.run(main())