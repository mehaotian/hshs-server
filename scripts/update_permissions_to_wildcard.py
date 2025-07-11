#!/usr/bin/env python3
"""
权限和角色通配符模式更新脚本

该脚本用于将系统内置的权限和角色配置修改为通配符模式，
包括添加所有必要的内置权限和通配符权限。

使用方法:
    python scripts/update_permissions_to_wildcard.py
"""

import asyncio
import sys
import os
from typing import Dict, List, Any

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.role import Role, Permission, SYSTEM_PERMISSIONS, SYSTEM_ROLES
from app.services.role import RoleService
from app.schemas.role import PermissionCreate, RoleCreate, RoleUpdate, PermissionType, ResourceType


# 扩展的系统权限配置（支持通配符）
EXTENDED_SYSTEM_PERMISSIONS = [
    # 超级权限
    {
        "name": "*",
        "display_name": "超级权限",
        "description": "拥有系统所有权限",
        "module": "system",
        "action": PermissionType.MANAGE,
        "resource": ResourceType.SYSTEM,
        "sort_order": 1
    },
    {
        "name": "*:*",
        "display_name": "全模块全操作权限",
        "description": "拥有所有模块的所有操作权限",
        "module": "system",
        "action": PermissionType.MANAGE,
        "resource": ResourceType.SYSTEM,
        "sort_order": 2
    },
    
    # 模块通配符权限
    {
        "name": "user:*",
        "display_name": "用户模块所有权限",
        "description": "用户模块的所有操作权限",
        "module": "user",
        "action": PermissionType.MANAGE,
        "resource": ResourceType.USER,
        "sort_order": 10
    },
    {
        "name": "role:*",
        "display_name": "角色模块所有权限",
        "description": "角色模块的所有操作权限",
        "module": "role",
        "action": PermissionType.MANAGE,
        "resource": ResourceType.ROLE,
        "sort_order": 11
    },
    {
        "name": "script:*",
        "display_name": "剧本模块所有权限",
        "description": "剧本模块的所有操作权限",
        "module": "script",
        "action": PermissionType.MANAGE,
        "resource": ResourceType.SCRIPT,
        "sort_order": 12
    },
    {
        "name": "audio:*",
        "display_name": "音频模块所有权限",
        "description": "音频模块的所有操作权限",
        "module": "audio",
        "action": PermissionType.MANAGE,
        "resource": ResourceType.AUDIO,
        "sort_order": 13
    },
    {
        "name": "review:*",
        "display_name": "审听模块所有权限",
        "description": "审听模块的所有操作权限",
        "module": "review",
        "action": PermissionType.MANAGE,
        "resource": ResourceType.REVIEW,
        "sort_order": 14
    },
    {
         "name": "society:*",
         "display_name": "社团模块所有权限",
         "description": "社团模块的所有操作权限",
         "module": "society",
         "action": PermissionType.MANAGE,
         "resource": ResourceType.SOCIETY,
         "sort_order": 15
     },
    {
        "name": "system:*",
        "display_name": "系统模块所有权限",
        "description": "系统模块的所有操作权限",
        "module": "system",
        "action": PermissionType.MANAGE,
        "resource": ResourceType.SYSTEM,
        "sort_order": 17
    },
     
     # 操作通配符权限
     {
         "name": "*:read",
         "display_name": "全模块读取权限",
         "description": "所有模块的读取权限",
         "module": "system",
         "action": PermissionType.READ,
         "resource": ResourceType.SYSTEM,
         "sort_order": 20
     },
     {
         "name": "*:write",
         "display_name": "全模块写入权限",
         "description": "所有模块的写入权限",
         "module": "system",
         "action": PermissionType.WRITE,
         "resource": ResourceType.SYSTEM,
         "sort_order": 21
     },
     {
         "name": "*:delete",
         "display_name": "全模块删除权限",
         "description": "所有模块的删除权限",
         "module": "system",
         "action": PermissionType.DELETE,
         "resource": ResourceType.SYSTEM,
         "sort_order": 22
     },
     {
         "name": "*:manage",
         "display_name": "全模块管理权限",
         "description": "所有模块的管理权限",
         "module": "system",
         "action": PermissionType.MANAGE,
         "resource": ResourceType.SYSTEM,
         "sort_order": 23
     }
]

# 添加具体的系统权限
for perm_name, perm_display in SYSTEM_PERMISSIONS.items():
    # 解析权限名称
    if ':' in perm_name:
        module, action = perm_name.split(':', 1)
    else:
        module = 'system'
        action = perm_name
    
    # 映射操作类型
    action_mapping = {
        'create': PermissionType.WRITE,
        'read': PermissionType.READ,
        'update': PermissionType.WRITE,
        'delete': PermissionType.DELETE,
        'manage': PermissionType.MANAGE,
        'assign': PermissionType.WRITE,
        'upload': PermissionType.WRITE,
        'download': PermissionType.READ,
        'review': PermissionType.READ,
        'approve': PermissionType.WRITE,
        'reject': PermissionType.WRITE,
        'publish': PermissionType.WRITE,
        'archive': PermissionType.WRITE,
        'export': PermissionType.READ,
        'import': PermissionType.WRITE,
        'process': PermissionType.WRITE,
        'merge': PermissionType.WRITE,
        'split': PermissionType.WRITE,
        'batch': PermissionType.WRITE,
        'config': PermissionType.MANAGE,
        'log': PermissionType.READ,
        'monitor': PermissionType.READ,
        'backup': PermissionType.MANAGE,
        'restore': PermissionType.MANAGE,
        'maintenance': PermissionType.MANAGE,
        'statistics': PermissionType.READ,
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
    
    perm_action = action_mapping.get(action, PermissionType.READ)
    perm_resource = resource_mapping.get(module, ResourceType.SYSTEM)
    
    EXTENDED_SYSTEM_PERMISSIONS.append({
        "name": perm_name,
        "display_name": perm_display,
        "description": f"{perm_display}权限",
        "module": module,
        "action": perm_action,
        "resource": perm_resource,
        "sort_order": 100 + len(EXTENDED_SYSTEM_PERMISSIONS)
    })

# 更新的系统角色配置（使用通配符权限）
UPDATED_SYSTEM_ROLES = {
    'super_admin': {
        'display_name': '超级管理员',
        'description': '系统最高权限管理员，拥有所有权限',
        'permissions': ['*']  # 超级权限
    },
    'admin': {
        'display_name': '管理员',
        'description': '系统管理员，拥有大部分管理权限',
        'permissions': [
            'user:*', 'role:*', 'department:*', 'system:config', 'system:log', 'system:monitor'
        ]
    },
    'project_leader': {
        'display_name': '项目组长',
        'description': '项目负责人，管理项目全流程',
        'permissions': [
            'script:*', 'audio:*', 'assignment:*', 'review:*',
            'user:read', 'user:assign_role', 'department:read'
        ]
    },
    'director': {
        'display_name': '导演',
        'description': '艺术指导和质量监督',
        'permissions': [
            'script:read', 'script:update', 'audio:*', 'review:*',
            'assignment:read', 'user:read'
        ]
    },
    'scriptwriter': {
        'display_name': '编剧',
        'description': '剧本创作和内容管理',
        'permissions': [
            'script:create', 'script:read', 'script:update', 'script:export',
            'user:read'
        ]
    },
    'cv': {
        'display_name': 'CV配音演员',
        'description': '角色配音和音频录制',
        'permissions': [
            'script:read', 'audio:create', 'audio:read', 'audio:upload', 'audio:download',
            'assignment:read', 'user:read'
        ]
    },
    'post_production': {
        'display_name': '后期制作',
        'description': '音频处理和技术制作',
        'permissions': [
            'audio:*', 'script:read', 'assignment:read', 'user:read'
        ]
    },
    'first_reviewer': {
        'display_name': '一审',
        'description': '技术质量审听',
        'permissions': [
            'audio:read', 'audio:download', 'audio:review',
            'review:create', 'review:read', 'review:update',
            'script:read', 'assignment:read', 'user:read'
        ]
    },
    'second_reviewer': {
        'display_name': '二审',
        'description': '内容质量审听和最终审批',
        'permissions': [
            'audio:read', 'audio:download', 'audio:review',
            'review:*', 'script:read', 'assignment:read', 'user:read'
        ]
    },
    'user': {
        'display_name': '普通用户',
        'description': '基础用户权限',
        'permissions': [
            'user:read', 'script:read', 'audio:read', 'assignment:read'
        ]
    }
}


class PermissionUpdater:
    """权限更新器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.role_service = RoleService(db)
    
    async def update_system_permissions(self) -> None:
        """更新系统权限"""
        print("开始更新系统权限...")
        
        # 获取现有权限
        existing_permissions, _ = await self.role_service.get_permissions(page=1, size=1000)
        existing_names = {perm.name for perm in existing_permissions}
        
        # 添加新权限
        new_permissions = []
        for perm_data in EXTENDED_SYSTEM_PERMISSIONS:
            if perm_data['name'] not in existing_names:
                new_permissions.append(perm_data)
        
        # 批量创建权限
        if new_permissions:
            for perm_data in new_permissions:
                try:
                    permission_create = PermissionCreate(**perm_data)
                    await self.role_service.create_permission(permission_create)
                    print(f"✓ 创建权限: {perm_data['name']} - {perm_data['display_name']}")
                except Exception as e:
                    print(f"✗ 创建权限失败: {perm_data['name']} - {e}")
        
        print(f"权限更新完成，新增 {len(new_permissions)} 个权限")
    
    async def update_system_roles(self) -> None:
        """更新系统角色"""
        print("开始更新系统角色...")
        
        # 获取现有角色
        existing_roles, _ = await self.role_service.get_roles(page=1, size=1000)
        existing_names = {role.name for role in existing_roles}
        
        # 更新或创建角色
        for name, config in UPDATED_SYSTEM_ROLES.items():
            try:
                if name in existing_names:
                    # 更新现有角色
                    role = await self.role_service.get_role_by_name(name)
                    if role:
                        # 更新角色权限
                        role_update = RoleUpdate(
                            display_name=config['display_name'],
                            description=config['description'],
                            permissions=config['permissions']
                        )
                        await self.role_service.update_role(role.id, role_update)
                        print(f"✓ 更新角色: {name} - {config['display_name']}")
                else:
                    # 创建新角色
                    role_create = RoleCreate(
                         name=name,
                         display_name=config['display_name'],
                         description=config['description'],
                         permissions=config['permissions']
                     )
                    await self.role_service.create_role(role_create)
                    print(f"✓ 创建角色: {name} - {config['display_name']}")
            except Exception as e:
                print(f"✗ 处理角色失败: {name} - {e}")
        
        print("角色更新完成")
    
    async def display_current_config(self) -> None:
        """显示当前配置"""
        print("\n=== 当前权限配置 ===")
        permissions, _ = await self.role_service.get_permissions(page=1, size=1000)
        
        # 按模块分组显示权限
        modules = {}
        wildcards = []
        
        for perm in permissions:
            name = perm.name
            if '*' in name:
                wildcards.append(perm)
            else:
                module = getattr(perm, 'module', 'other') or 'other'
                if module not in modules:
                    modules[module] = []
                modules[module].append(perm)
        
        # 显示通配符权限
        if wildcards:
            print("\n通配符权限:")
            for perm in sorted(wildcards, key=lambda x: x.name):
                print(f"  {perm.name} - {perm.display_name}")
        
        # 显示模块权限
        for module, perms in sorted(modules.items()):
            if module and module != 'None':
                print(f"\n{module} 模块权限:")
                for perm in sorted(perms, key=lambda x: x.name):
                    print(f"  {perm.name} - {perm.display_name}")
        
        print("\n=== 当前角色配置 ===")
        roles, _ = await self.role_service.get_roles(page=1, size=1000)
        for role in sorted(roles, key=lambda x: x.name):
            print(f"\n{role.name} - {role.display_name}")
            print(f"  描述: {role.description}")
            permissions = getattr(role, 'permissions', []) or []
            if permissions:
                print(f"  权限: {', '.join(permissions)}")
            else:
                print("  权限: 无")


async def main():
    """主函数"""
    print("权限和角色通配符模式更新脚本")
    print("=" * 50)
    
    try:
        # 获取数据库会话
        async for db in get_db():
            updater = PermissionUpdater(db)
            
            # 显示当前配置
            print("\n1. 显示当前配置")
            await updater.display_current_config()
            
            # 询问是否继续
            print("\n" + "="*50)
            response = input("是否继续更新权限和角色配置？(y/N): ").strip().lower()
            if response not in ['y', 'yes']:
                print("操作已取消")
                return
            
            # 更新权限
            print("\n2. 更新系统权限")
            await updater.update_system_permissions()
            
            # 更新角色
            print("\n3. 更新系统角色")
            await updater.update_system_roles()
            
            # 提交事务
            await db.commit()
            
            # 显示更新后的配置
            print("\n4. 显示更新后的配置")
            await updater.display_current_config()
            
            print("\n" + "="*50)
            print("权限和角色更新完成！")
            
            break
    
    except Exception as e:
        print(f"更新过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())