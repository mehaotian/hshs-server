#!/usr/bin/env python3
"""
用户角色分配脚本
用于为现有用户分配默认角色和权限
"""

import asyncio
import sys
from app.core.database import get_db
from app.services.role import RoleService
from app.services.user import UserService
from app.schemas.role import UserRoleCreate
from sqlalchemy import text

async def init_system_roles_and_assign():
    """初始化系统角色并为用户分配默认角色"""
    async for db in get_db():
        try:
            role_service = RoleService(db)
            user_service = UserService(db)
            
            print("=== 初始化系统角色和权限 ===")
            # 初始化系统角色
            init_result = await role_service.initialize_system_data()
            print(f"系统角色初始化完成: {init_result}")
            
            print("\n=== 查看可用角色 ===")
            # 获取所有角色
            roles, total = await role_service.get_roles(page=1, size=100)
            for role in roles:
                print(f"角色ID: {role.id}, 名称: {role.name}, 显示名: {role.display_name}")
            
            print("\n=== 查看现有用户 ===")
            # 获取所有用户
            result = await db.execute(text('SELECT id, username, email FROM users ORDER BY id'))
            users = result.fetchall()
            
            if not users:
                print("暂无用户")
                return
            
            for user in users:
                print(f"用户ID: {user.id}, 用户名: {user.username}, 邮箱: {user.email}")
            
            print("\n=== 为用户分配默认角色 ===")
            # 找到 CV 角色（适合普通用户的默认角色）
            cv_role = None
            for role in roles:
                if role.name == 'cv':
                    cv_role = role
                    break
            
            if not cv_role:
                print("未找到 CV 角色，尝试创建...")
                return
            
            # 为每个用户分配 CV 角色
            for user in users:
                try:
                    # 检查用户是否已有角色
                    user_roles = await role_service.get_user_roles(user.id)
                    if user_roles:
                        print(f"用户 {user.username} 已有角色: {[r.name for r in user_roles]}")
                        continue
                    
                    # 分配 CV 角色
                    user_role_data = UserRoleCreate(
                        user_id=user.id,
                        role_id=cv_role.id
                    )
                    await role_service.assign_role_to_user(user_role_data)
                    print(f"✓ 为用户 {user.username} 分配了 CV 角色")
                    
                except Exception as e:
                    print(f"✗ 为用户 {user.username} 分配角色失败: {str(e)}")
            
            print("\n=== 角色分配完成 ===")
            
        except Exception as e:
            print(f"操作失败: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            break

async def assign_specific_role(user_id: int, role_name: str):
    """为特定用户分配特定角色"""
    async for db in get_db():
        try:
            role_service = RoleService(db)
            
            # 获取角色
            role = await role_service.get_role_by_name(role_name)
            if not role:
                print(f"角色 '{role_name}' 不存在")
                return
            
            # 分配角色
            user_role_data = UserRoleCreate(
                user_id=user_id,
                role_id=role.id
            )
            await role_service.assign_role_to_user(user_role_data)
            print(f"✓ 为用户ID {user_id} 分配了角色 '{role_name}'")
            
        except Exception as e:
            print(f"分配角色失败: {str(e)}")
        finally:
            break

def print_usage():
    print("用法:")
    print("  python assign_user_role.py init          # 初始化系统角色并为所有用户分配默认角色")
    print("  python assign_user_role.py assign <user_id> <role_name>  # 为特定用户分配特定角色")
    print("")
    print("可用角色名称:")
    print("  super_admin     - 超级管理员")
    print("  project_leader  - 项目组长")
    print("  director        - 导演")
    print("  scriptwriter    - 编剧")
    print("  cv              - CV配音演员")
    print("  post_production - 后期制作")
    print("  first_reviewer  - 一审")
    print("  second_reviewer - 二审")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "init":
        asyncio.run(init_system_roles_and_assign())
    elif command == "assign":
        if len(sys.argv) != 4:
            print("错误: assign 命令需要用户ID和角色名称")
            print_usage()
            sys.exit(1)
        
        try:
            user_id = int(sys.argv[2])
            role_name = sys.argv[3]
            asyncio.run(assign_specific_role(user_id, role_name))
        except ValueError:
            print("错误: 用户ID必须是数字")
            sys.exit(1)
    else:
        print(f"未知命令: {command}")
        print_usage()
        sys.exit(1)