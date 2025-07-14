#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Super权限诊断脚本
用于检查super角色权限分配和权限检查逻辑是否正常工作
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.role import Role, Permission, RolePermission, UserRole
from app.services.user import UserService
from app.services.role import RoleService

class SuperPermissionDiagnoser:
    def __init__(self):
        self.session = None
        
    async def setup_session(self):
        """设置数据库会话"""
        self.session = AsyncSessionLocal()
    
    async def check_super_role_permissions(self):
        """检查super角色的权限分配"""
        print("\n=== 检查Super角色权限分配 ===")
        
        # 查询super角色
        result = await self.session.execute(
            select(Role)
            .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
            .where(Role.name == 'super')
        )
        super_role = result.scalar_one_or_none()
        
        if not super_role:
            print("❌ 未找到super角色！")
            return False
            
        print(f"✅ 找到super角色 (ID: {super_role.id})")
        
        # 获取super角色的权限
        super_permissions = [rp.permission.name for rp in super_role.role_permissions]
        print(f"Super角色拥有 {len(super_permissions)} 个权限:")
        for perm in sorted(super_permissions):
            print(f"  - {perm}")
        
        # 获取系统中所有权限
        all_permissions_result = await self.session.execute(select(Permission))
        all_permissions = [p.name for p in all_permissions_result.scalars().all()]
        
        print(f"\n系统总权限数: {len(all_permissions)}")
        
        # 检查缺失的权限
        missing_permissions = set(all_permissions) - set(super_permissions)
        if missing_permissions:
            print(f"❌ Super角色缺少 {len(missing_permissions)} 个权限:")
            for perm in sorted(missing_permissions):
                print(f"  - {perm}")
            return False
        else:
            print("✅ Super角色拥有所有权限")
            return True
    
    async def check_super_users(self):
        """检查拥有super角色的用户"""
        print("\n=== 检查Super用户 ===")
        
        # 查询拥有super角色的用户
        result = await self.session.execute(
            select(User)
            .join(UserRole, User.id == UserRole.user_id)
            .join(Role, UserRole.role_id == Role.id)
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
            .where(Role.name == 'super')
        )
        super_users = result.scalars().all()
        
        if not super_users:
            print("❌ 没有用户拥有super角色！")
            return False
            
        print(f"✅ 找到 {len(super_users)} 个super用户:")
        for user in super_users:
            print(f"  - {user.username} (ID: {user.id})")
            
        return super_users
    
    async def test_permission_checking(self):
        """测试权限检查功能"""
        print("\n=== 测试权限检查功能 ===")
        
        # 获取super角色并加载权限关联数据
        result = await self.session.execute(
            select(Role)
            .options(selectinload(Role.role_permissions).selectinload(RolePermission.permission))
            .where(Role.name == 'super')
        )
        super_role = result.scalar_one_or_none()
        
        # 确保权限关联数据已加载
        if super_role:
            # 访问role_permissions属性以触发懒加载
            _ = len(super_role.role_permissions)
        
        if not super_role:
            print("❌ 未找到super角色")
            return False
            
        # 获取一些测试权限
        test_permissions = [
            'user:read', 'user:create', 'user:update', 'user:delete',
            'role:read', 'role:create', 'role:update', 'role:delete',
            'script:read', 'script:create', 'script:update', 'script:delete'
        ]
        
        print("测试super角色权限检查:")
        all_passed = True
        for perm in test_permissions:
            has_permission = super_role.has_permission(perm)
            status = "✅" if has_permission else "❌"
            print(f"  {status} {perm}: {has_permission}")
            if not has_permission:
                all_passed = False
                
        return all_passed
    
    async def test_user_service_permissions(self):
        """测试用户服务权限检查"""
        print("\n=== 测试用户服务权限检查 ===")
        
        # 获取一个super用户
        result = await self.session.execute(
            select(User)
            .join(UserRole, User.id == UserRole.user_id)
            .join(Role, UserRole.role_id == Role.id)
            .where(Role.name == 'super')
            .limit(1)
        )
        super_user = result.scalar_one_or_none()
        
        if not super_user:
            print("❌ 没有super用户可供测试")
            return False
            
        print(f"测试用户: {super_user.username} (ID: {super_user.id})")
        
        # 使用UserService获取用户权限
        user_service = UserService(self.session)
        user_permissions = await user_service.get_user_permissions(super_user.id)
        
        print(f"用户服务返回 {len(user_permissions)} 个权限:")
        for perm in sorted(user_permissions):
            print(f"  - {perm}")
            
        # 检查是否包含关键权限
        key_permissions = ['user:read', 'user:create', 'role:read', 'role:create']
        all_found = True
        for perm in key_permissions:
            if perm in user_permissions:
                print(f"  ✅ 找到关键权限: {perm}")
            else:
                print(f"  ❌ 缺少关键权限: {perm}")
                all_found = False
                
        return all_found
    
    async def test_role_service_permissions(self):
        """测试角色服务权限检查"""
        print("\n=== 测试角色服务权限检查 ===")
        
        # 获取一个super用户
        result = await self.session.execute(
            select(User)
            .join(UserRole, User.id == UserRole.user_id)
            .join(Role, UserRole.role_id == Role.id)
            .where(Role.name == 'super')
            .limit(1)
        )
        super_user = result.scalar_one_or_none()
        
        if not super_user:
            print("❌ 没有super用户可供测试")
            return False
            
        # 使用RoleService检查权限
        role_service = RoleService(self.session)
        
        test_permissions = ['user:read', 'user:create', 'role:read', 'role:create']
        all_passed = True
        
        for perm in test_permissions:
            has_permission = await role_service.check_user_permission(super_user.id, perm)
            status = "✅" if has_permission else "❌"
            print(f"  {status} {perm}: {has_permission}")
            if not has_permission:
                all_passed = False
                
        return all_passed
    
    async def fix_super_permissions(self):
        """修复super角色权限"""
        print("\n=== 修复Super角色权限 ===")
        
        # 获取super角色
        result = await self.session.execute(
            select(Role).where(Role.name == 'super')
        )
        super_role = result.scalar_one_or_none()
        
        if not super_role:
            print("❌ 未找到super角色")
            return False
            
        # 获取所有权限
        all_permissions_result = await self.session.execute(select(Permission))
        all_permissions = all_permissions_result.scalars().all()
        
        # 获取super角色当前权限
        current_permissions_result = await self.session.execute(
            select(RolePermission).where(RolePermission.role_id == super_role.id)
        )
        current_permission_ids = {rp.permission_id for rp in current_permissions_result.scalars().all()}
        
        # 添加缺失的权限
        added_count = 0
        for permission in all_permissions:
            if permission.id not in current_permission_ids:
                role_permission = RolePermission(
                    role_id=super_role.id,
                    permission_id=permission.id
                )
                self.session.add(role_permission)
                added_count += 1
                print(f"  + 添加权限: {permission.name}")
        
        if added_count > 0:
            await self.session.commit()
            print(f"✅ 成功为super角色添加了 {added_count} 个权限")
        else:
            print("✅ Super角色已拥有所有权限，无需修复")
            
        return True
    
    async def run_diagnosis(self):
        """运行完整诊断"""
        print("开始Super权限系统诊断...")
        
        await self.setup_session()
        
        try:
            # 1. 检查super角色权限
            super_permissions_ok = await self.check_super_role_permissions()
            
            # 2. 检查super用户
            super_users = await self.check_super_users()
            
            # 3. 测试权限检查
            permission_check_ok = await self.test_permission_checking()
            
            # 4. 测试用户服务
            user_service_ok = await self.test_user_service_permissions()
            
            # 5. 测试角色服务
            role_service_ok = await self.test_role_service_permissions()
            
            # 如果发现问题，尝试修复
            if not super_permissions_ok:
                print("\n检测到super角色权限不完整，开始修复...")
                await self.fix_super_permissions()
                
                # 重新测试
                print("\n重新测试修复后的权限...")
                super_permissions_ok = await self.check_super_role_permissions()
                permission_check_ok = await self.test_permission_checking()
                user_service_ok = await self.test_user_service_permissions()
                role_service_ok = await self.test_role_service_permissions()
            
            # 总结
            print("\n=== 诊断总结 ===")
            print(f"Super角色权限完整性: {'✅' if super_permissions_ok else '❌'}")
            print(f"Super用户存在: {'✅' if super_users else '❌'}")
            print(f"权限检查功能: {'✅' if permission_check_ok else '❌'}")
            print(f"用户服务权限: {'✅' if user_service_ok else '❌'}")
            print(f"角色服务权限: {'✅' if role_service_ok else '❌'}")
            
            all_ok = all([super_permissions_ok, super_users, permission_check_ok, user_service_ok, role_service_ok])
            
            if all_ok:
                print("\n🎉 所有测试通过！Super权限系统工作正常。")
            else:
                print("\n⚠️  发现问题，请检查上述失败的测试项。")
                
            return all_ok
            
        except Exception as e:
            print(f"\n❌ 诊断过程中发生错误: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            if self.session:
                await self.session.close()

async def main():
    diagnoser = SuperPermissionDiagnoser()
    await diagnoser.run_diagnosis()

if __name__ == "__main__":
    asyncio.run(main())