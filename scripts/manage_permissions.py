#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
权限和角色管理脚本
用于查看、添加、修改系统内置的权限和角色配置
支持通配符权限模式
"""

import asyncio
import sys
import os
from typing import List, Dict, Any, Optional

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_db
from app.services.role import RoleService
from app.models.role import Role, Permission
from app.schemas.role import PermissionCreate, RoleCreate, RoleUpdate, PermissionType, ResourceType
from sqlalchemy.ext.asyncio import AsyncSession


class PermissionManager:
    """权限管理器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.role_service = RoleService(db)
    
    async def list_permissions(self, filter_wildcard: bool = False) -> None:
        """列出所有权限"""
        print("\n=== 系统权限列表 ===")
        permissions, _ = await self.role_service.get_permissions(page=1, size=1000)
        
        # 按模块分组
        modules = {}
        wildcards = []
        
        for perm in permissions:
            if '*' in perm.name:
                if not filter_wildcard:
                    wildcards.append(perm)
            else:
                if filter_wildcard:
                    continue
                module = getattr(perm, 'module', 'other') or 'other'
                if module not in modules:
                    modules[module] = []
                modules[module].append(perm)
        
        # 显示通配符权限
        if wildcards and not filter_wildcard:
            print("\n🌟 通配符权限:")
            for perm in sorted(wildcards, key=lambda x: x.name):
                print(f"  {perm.name:<20} - {perm.display_name}")
                print(f"    描述: {perm.description}")
                print(f"    模块: {perm.module}, 操作: {perm.action}, 资源: {perm.resource}")
                print()
        
        # 显示模块权限
        if not filter_wildcard:
            for module, perms in sorted(modules.items()):
                if module and module != 'None':
                    print(f"\n📁 {module} 模块权限:")
                    for perm in sorted(perms, key=lambda x: x.name):
                        print(f"  {perm.name:<25} - {perm.display_name}")
    
    async def list_roles(self) -> None:
        """列出所有角色"""
        print("\n=== 系统角色列表 ===")
        roles, _ = await self.role_service.get_roles(page=1, size=1000)
        
        for role in sorted(roles, key=lambda x: x.name):
            print(f"\n👤 {role.name} - {role.display_name}")
            print(f"   描述: {role.description}")
            print(f"   系统角色: {'是' if role.is_system else '否'}")
            
            permissions = getattr(role, 'permissions', []) or []
            if permissions:
                # 分类显示权限
                wildcards = [p for p in permissions if '*' in p]
                specifics = [p for p in permissions if '*' not in p]
                
                if wildcards:
                    print(f"   🌟 通配符权限: {', '.join(wildcards)}")
                if specifics:
                    print(f"   📋 具体权限: {', '.join(specifics[:10])}{'...' if len(specifics) > 10 else ''}")
            else:
                print("   权限: 无")
    
    async def show_role_details(self, role_name: str) -> None:
        """显示角色详细信息"""
        role = await self.role_service.get_role_by_name(role_name)
        if not role:
            print(f"❌ 角色 '{role_name}' 不存在")
            return
        
        print(f"\n=== 角色详情: {role.name} ===")
        print(f"显示名称: {role.display_name}")
        print(f"描述: {role.description}")
        print(f"系统角色: {'是' if role.is_system else '否'}")
        print(f"创建时间: {role.created_at}")
        print(f"更新时间: {role.updated_at}")
        
        permissions = getattr(role, 'permissions', []) or []
        if permissions:
            print(f"\n权限列表 ({len(permissions)} 个):")
            
            # 分类显示
            wildcards = [p for p in permissions if '*' in p]
            specifics = [p for p in permissions if '*' not in p]
            
            if wildcards:
                print("\n🌟 通配符权限:")
                for perm in sorted(wildcards):
                    print(f"  - {perm}")
            
            if specifics:
                print("\n📋 具体权限:")
                # 按模块分组
                modules = {}
                for perm in specifics:
                    module = perm.split(':')[0] if ':' in perm else 'other'
                    if module not in modules:
                        modules[module] = []
                    modules[module].append(perm)
                
                for module, perms in sorted(modules.items()):
                    print(f"  {module}:")
                    for perm in sorted(perms):
                        print(f"    - {perm}")
        else:
            print("\n权限: 无")
    
    async def add_permission(self, name: str, display_name: str, description: str, 
                           module: str, action: str, resource: str) -> None:
        """添加新权限"""
        try:
            # 映射操作类型
            action_mapping = {
                'read': PermissionType.READ,
                'write': PermissionType.WRITE,
                'delete': PermissionType.DELETE,
                'execute': PermissionType.EXECUTE,
                'manage': PermissionType.MANAGE,
            }
            
            # 映射资源类型
            resource_mapping = {
                'user': ResourceType.USER,
                'role': ResourceType.ROLE,
                'script': ResourceType.SCRIPT,
                'audio': ResourceType.AUDIO,
                'review': ResourceType.REVIEW,
                'society': ResourceType.SOCIETY,
                'system': ResourceType.SYSTEM,
            }
            
            perm_action = action_mapping.get(action.lower(), PermissionType.READ)
            perm_resource = resource_mapping.get(resource.lower(), ResourceType.SYSTEM)
            
            permission_create = PermissionCreate(
                name=name,
                display_name=display_name,
                description=description,
                module=module,
                action=perm_action,
                resource=perm_resource
            )
            
            new_permission = await self.role_service.create_permission(permission_create)
            print(f"✅ 成功创建权限: {name} - {display_name}")
            
        except Exception as e:
            print(f"❌ 创建权限失败: {str(e)}")
    
    async def add_role(self, name: str, display_name: str, description: str, 
                      permissions: List[str]) -> None:
        """添加新角色"""
        try:
            role_create = RoleCreate(
                name=name,
                display_name=display_name,
                description=description,
                permissions=permissions
            )
            
            new_role = await self.role_service.create_role(role_create)
            print(f"✅ 成功创建角色: {name} - {display_name}")
            print(f"   权限: {', '.join(permissions)}")
            
        except Exception as e:
            print(f"❌ 创建角色失败: {str(e)}")
    
    async def update_role_permissions(self, role_name: str, permissions: List[str]) -> None:
        """更新角色权限"""
        try:
            role = await self.role_service.get_role_by_name(role_name)
            if not role:
                print(f"❌ 角色 '{role_name}' 不存在")
                return
            
            role_update = RoleUpdate(permissions=permissions)
            updated_role = await self.role_service.update_role(role.id, role_update)
            
            print(f"✅ 成功更新角色 '{role_name}' 的权限")
            print(f"   新权限: {', '.join(permissions)}")
            
        except Exception as e:
            print(f"❌ 更新角色权限失败: {str(e)}")


def print_help():
    """打印帮助信息"""
    print("""
🔧 权限和角色管理工具

用法: python manage_permissions.py [命令] [参数]

命令:
  list-permissions [--wildcard-only]  列出所有权限
  list-roles                          列出所有角色
  show-role <角色名>                   显示角色详细信息
  add-permission <名称> <显示名> <描述> <模块> <操作> <资源>  添加权限
  add-role <名称> <显示名> <描述> <权限1,权限2,...>  添加角色
  update-role <角色名> <权限1,权限2,...>  更新角色权限
  help                                显示此帮助信息

示例:
  # 列出所有权限
  python manage_permissions.py list-permissions
  
  # 只显示通配符权限
  python manage_permissions.py list-permissions --wildcard-only
  
  # 显示角色详情
  python manage_permissions.py show-role super_admin
  
  # 添加新权限
  python manage_permissions.py add-permission "test:create" "创建测试" "创建测试数据" "test" "write" "system"
  
  # 添加新角色
  python manage_permissions.py add-role "tester" "测试员" "系统测试人员" "test:*,user:read"
  
  # 更新角色权限
  python manage_permissions.py update-role "tester" "test:*,user:read,script:read"

权限格式说明:
  - 通配符权限: *, *:*, module:*, *:action
  - 具体权限: module:action (如 user:create, script:read)
  
操作类型: read, write, delete, execute, manage
资源类型: user, role, script, audio, review, society, system
""")


async def main():
    """主函数"""
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1]
    
    if command == "help":
        print_help()
        return
    
    # 获取数据库会话
    async for db in get_db():
        manager = PermissionManager(db)
        
        try:
            if command == "list-permissions":
                wildcard_only = len(sys.argv) > 2 and sys.argv[2] == "--wildcard-only"
                await manager.list_permissions(filter_wildcard=wildcard_only)
                
            elif command == "list-roles":
                await manager.list_roles()
                
            elif command == "show-role":
                if len(sys.argv) < 3:
                    print("❌ 请提供角色名称")
                    return
                await manager.show_role_details(sys.argv[2])
                
            elif command == "add-permission":
                if len(sys.argv) < 8:
                    print("❌ 参数不足，需要: 名称 显示名 描述 模块 操作 资源")
                    return
                await manager.add_permission(
                    sys.argv[2], sys.argv[3], sys.argv[4], 
                    sys.argv[5], sys.argv[6], sys.argv[7]
                )
                
            elif command == "add-role":
                if len(sys.argv) < 6:
                    print("❌ 参数不足，需要: 名称 显示名 描述 权限列表")
                    return
                permissions = sys.argv[5].split(',') if sys.argv[5] else []
                await manager.add_role(
                    sys.argv[2], sys.argv[3], sys.argv[4], permissions
                )
                
            elif command == "update-role":
                if len(sys.argv) < 4:
                    print("❌ 参数不足，需要: 角色名 权限列表")
                    return
                permissions = sys.argv[3].split(',') if sys.argv[3] else []
                await manager.update_role_permissions(sys.argv[2], permissions)
                
            else:
                print(f"❌ 未知命令: {command}")
                print_help()
                
        except Exception as e:
            print(f"❌ 执行命令时出错: {str(e)}")
        
        break


if __name__ == "__main__":
    asyncio.run(main())