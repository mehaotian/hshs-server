#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
添加通配符权限脚本
用于向权限表中添加通配符权限数据
"""

import asyncio
import sys
import os
from typing import List, Dict

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_db
from app.models.role import Permission
from app.schemas.role import PermissionType, ResourceType
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


class WildcardPermissionAdder:
    """通配符权限添加器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def log(self, message: str):
        """日志输出"""
        print(f"[INFO] {message}")
    
    async def add_wildcard_permissions(self) -> None:
        """添加通配符权限"""
        self.log("开始添加通配符权限...")
        
        # 定义通配符权限
        wildcard_permissions = [
            {
                'name': '*',
                'display_name': '全部权限',
                'description': '拥有系统所有权限',
                'module': 'system',
                'action': PermissionType.MANAGE,
                'resource': ResourceType.SYSTEM,
                'is_wildcard': True,
                'is_active': True,
                'sort_order': 0
            },
            {
                'name': 'user:*',
                'display_name': '用户模块全部权限',
                'description': '拥有用户模块的所有权限',
                'module': 'user',
                'action': PermissionType.MANAGE,
                'resource': ResourceType.USER,
                'is_wildcard': True,
                'is_active': True,
                'sort_order': 10
            },
            {
                'name': 'role:*',
                'display_name': '角色模块全部权限',
                'description': '拥有角色模块的所有权限',
                'module': 'role',
                'action': PermissionType.MANAGE,
                'resource': ResourceType.ROLE,
                'is_wildcard': True,
                'is_active': True,
                'sort_order': 20
            },
            {
                'name': 'script:*',
                'display_name': '剧本模块全部权限',
                'description': '拥有剧本模块的所有权限',
                'module': 'script',
                'action': PermissionType.MANAGE,
                'resource': ResourceType.SCRIPT,
                'is_wildcard': True,
                'is_active': True,
                'sort_order': 30
            },
            {
                'name': 'audio:*',
                'display_name': '音频模块全部权限',
                'description': '拥有音频模块的所有权限',
                'module': 'audio',
                'action': PermissionType.MANAGE,
                'resource': ResourceType.AUDIO,
                'is_wildcard': True,
                'is_active': True,
                'sort_order': 40
            },
            {
                'name': 'review:*',
                'display_name': '审听模块全部权限',
                'description': '拥有审听模块的所有权限',
                'module': 'review',
                'action': PermissionType.MANAGE,
                'resource': ResourceType.REVIEW,
                'is_wildcard': True,
                'is_active': True,
                'sort_order': 50
            },
            {
                'name': 'society:*',
                'display_name': '社团模块全部权限',
                'description': '拥有社团模块的所有权限',
                'module': 'society',
                'action': PermissionType.MANAGE,
                'resource': ResourceType.SOCIETY,
                'is_wildcard': True,
                'is_active': True,
                'sort_order': 60
            },
            {
                'name': '*:read',
                'display_name': '全模块读取权限',
                'description': '拥有所有模块的读取权限',
                'module': 'system',
                'action': PermissionType.READ,
                'resource': ResourceType.SYSTEM,
                'is_wildcard': True,
                'is_active': True,
                'sort_order': 100
            },
            {
                'name': '*:write',
                'display_name': '全模块写入权限',
                'description': '拥有所有模块的写入权限',
                'module': 'system',
                'action': PermissionType.WRITE,
                'resource': ResourceType.SYSTEM,
                'is_wildcard': True,
                'is_active': True,
                'sort_order': 110
            },
            {
                'name': '*:delete',
                'display_name': '全模块删除权限',
                'description': '拥有所有模块的删除权限',
                'module': 'system',
                'action': PermissionType.DELETE,
                'resource': ResourceType.SYSTEM,
                'is_wildcard': True,
                'is_active': True,
                'sort_order': 120
            },
            {
                'name': '*:manage',
                'display_name': '全模块管理权限',
                'description': '拥有所有模块的管理权限',
                'module': 'system',
                'action': PermissionType.MANAGE,
                'resource': ResourceType.SYSTEM,
                'is_wildcard': True,
                'is_active': True,
                'sort_order': 130
            }
        ]
        
        added_count = 0
        skipped_count = 0
        
        for perm_data in wildcard_permissions:
            # 检查权限是否已存在
            result = await self.db.execute(
                select(Permission).where(Permission.name == perm_data['name'])
            )
            existing_perm = result.scalar_one_or_none()
            
            if existing_perm:
                self.log(f"通配符权限 '{perm_data['name']}' 已存在，跳过创建")
                skipped_count += 1
            else:
                # 创建新权限
                new_permission = Permission(**perm_data)
                self.db.add(new_permission)
                await self.db.flush()
                self.log(f"创建通配符权限: {perm_data['name']} - {perm_data['display_name']}")
                added_count += 1
        
        await self.db.commit()
        self.log(f"通配符权限添加完成！新增: {added_count} 个，跳过: {skipped_count} 个")
    
    async def list_wildcard_permissions(self) -> None:
        """列出所有通配符权限"""
        self.log("查询通配符权限...")
        
        result = await self.db.execute(
            select(Permission).where(Permission.is_wildcard == True).order_by(Permission.sort_order)
        )
        permissions = result.scalars().all()
        
        if not permissions:
            self.log("未找到通配符权限")
            return
        
        self.log(f"找到 {len(permissions)} 个通配符权限:")
        print("\n🌟 通配符权限列表:")
        for perm in permissions:
            print(f"  {perm.name:<15} - {perm.display_name}")
            print(f"    描述: {perm.description}")
            print(f"    模块: {perm.module}, 操作: {perm.action}, 资源: {perm.resource}")
            print(f"    激活: {'是' if perm.is_active else '否'}")
            print()


async def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("""
🔧 通配符权限管理工具

用法: python add_wildcard_permissions.py [命令]

命令:
  add     添加通配符权限
  list    列出所有通配符权限
  help    显示此帮助信息

示例:
  python add_wildcard_permissions.py add
  python add_wildcard_permissions.py list
""")
        return
    
    command = sys.argv[1]
    
    if command == "help":
        print("""
🔧 通配符权限管理工具

用法: python add_wildcard_permissions.py [命令]

命令:
  add     添加通配符权限
  list    列出所有通配符权限
  help    显示此帮助信息

示例:
  python add_wildcard_permissions.py add
  python add_wildcard_permissions.py list
""")
        return
    
    print(f"[INFO] 开始执行命令: {command}")
    print(f"[INFO] 正在连接数据库...")
    
    # 获取数据库会话
    try:
        async for db in get_db():
            print(f"[INFO] 数据库连接成功")
            adder = WildcardPermissionAdder(db)
            
            try:
                if command == "add":
                    await adder.add_wildcard_permissions()
                elif command == "list":
                    await adder.list_wildcard_permissions()
                else:
                    print(f"❌ 未知命令: {command}")
                    print("使用 'help' 查看可用命令")
                    
            except Exception as e:
                print(f"❌ 执行命令时出错: {str(e)}")
                import traceback
                traceback.print_exc()
            
            break
    except Exception as e:
        print(f"❌ 数据库连接失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())