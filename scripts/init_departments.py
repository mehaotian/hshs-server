#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
部门管理系统初始化脚本

该脚本用于初始化部门管理系统的基础数据，包括：
1. 创建部门相关权限
2. 创建默认的部门结构
3. 分配管理员权限

使用方法：
    python scripts/init_departments.py
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.role import Role, Permission, RolePermission
from app.models.department import Department
from app.core.logger import logger


class DepartmentInitializer:
    """部门管理系统初始化器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def init_permissions(self):
        """初始化部门相关权限"""
        logger.info("开始初始化部门权限...")
        
        # 定义部门相关权限
        department_permissions = [
            {
                'name': 'department:create',
                'display_name': '创建部门',
                'description': '创建新部门的权限',
                'resource': 'department',
                'action': 'create'
            },
            {
                'name': 'department:read',
                'display_name': '查看部门',
                'description': '查看部门信息的权限',
                'resource': 'department',
                'action': 'read'
            },
            {
                'name': 'department:update',
                'display_name': '更新部门',
                'description': '更新部门信息的权限',
                'resource': 'department',
                'action': 'update'
            },
            {
                'name': 'department:delete',
                'display_name': '删除部门',
                'description': '删除部门的权限',
                'resource': 'department',
                'action': 'delete'
            },
            {
                'name': 'department:manage_members',
                'display_name': '管理部门成员',
                'description': '管理部门成员的权限',
                'resource': 'department',
                'action': 'manage_members'
            },
            {
                'name': 'department:view_statistics',
                'display_name': '查看部门统计',
                'description': '查看部门统计信息的权限',
                'resource': 'department',
                'action': 'view_statistics'
            }
        ]
        
        created_permissions = []
        
        for perm_data in department_permissions:
            # 检查权限是否已存在
            result = await self.db.execute(
                select(Permission).where(Permission.name == perm_data['name'])
            )
            existing_permission = result.scalar_one_or_none()
            
            if not existing_permission:
                permission = Permission(**perm_data)
                self.db.add(permission)
                created_permissions.append(permission)
                logger.info(f"创建权限: {perm_data['name']}")
            else:
                logger.info(f"权限已存在: {perm_data['name']}")
                created_permissions.append(existing_permission)
        
        await self.db.commit()
        logger.info(f"部门权限初始化完成，共创建 {len([p for p in created_permissions if p.id is None])} 个新权限")
        
        return created_permissions
    
    async def assign_permissions_to_admin(self, permissions):
        """将部门权限分配给管理员角色"""
        logger.info("开始为管理员角色分配部门权限...")
        
        # 获取管理员角色
        result = await self.db.execute(
            select(Role).where(Role.name == 'admin')
        )
        admin_role = result.scalar_one_or_none()
        
        if not admin_role:
            logger.warning("未找到管理员角色，跳过权限分配")
            return
        
        assigned_count = 0
        
        for permission in permissions:
            # 检查角色权限关联是否已存在
            result = await self.db.execute(
                select(RolePermission).where(
                    RolePermission.role_id == admin_role.id,
                    RolePermission.permission_id == permission.id
                )
            )
            existing_relation = result.scalar_one_or_none()
            
            if not existing_relation:
                role_permission = RolePermission(
                    role_id=admin_role.id,
                    permission_id=permission.id
                )
                self.db.add(role_permission)
                assigned_count += 1
                logger.info(f"为管理员角色分配权限: {permission.name}")
        
        await self.db.commit()
        logger.info(f"管理员权限分配完成，共分配 {assigned_count} 个新权限")
    
    async def init_default_departments(self):
        """初始化默认部门结构"""
        logger.info("开始初始化默认部门结构...")
        
        # 获取系统管理员用户（假设ID为1）
        result = await self.db.execute(
            select(User).where(User.id == 1)
        )
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            logger.warning("未找到系统管理员用户，使用 None 作为创建者")
            admin_user_id = None
        else:
            admin_user_id = admin_user.id
        
        # 检查根部门是否已存在
        result = await self.db.execute(
            select(Department).where(
                Department.name == '绘声绘社',
                Department.parent_id.is_(None)
            )
        )
        root_department = result.scalar_one_or_none()
        
        if root_department:
            logger.info("根部门已存在，跳过创建")
            return root_department
        
        # 创建根部门
        root_department = Department(
            name='绘声绘社',
            description='绘声绘社根部门',
            level=1,
            path='/1/',
            sort_order=0,
            status=Department.STATUS_ACTIVE
        )
        
        self.db.add(root_department)
        await self.db.flush()  # 获取ID但不提交
        
        # 更新路径
        root_department.path = f'/{root_department.id}/'
        
        # 创建子部门
        sub_departments = [
            {
                'name': '管理部',
                'description': '负责绘声绘社的日常管理工作',
                'sort_order': 1
            },
            {
                'name': '编剧部',
                'description': '负责剧本创作和编辑工作',
                'sort_order': 2
            },
            {
                'name': '配音部',
                'description': '负责配音录制和音频制作工作',
                'sort_order': 3
            },
            {
                'name': '后期部',
                'description': '负责音频后期制作和剪辑工作',
                'sort_order': 4
            },
            {
                'name': '外宣部',
                'description': '负责对外宣传和推广工作',
                'sort_order': 5
            },
            {
                'name': '美工部',
                'description': '负责美术设计和视觉创作工作',
                'sort_order': 6
            }
        ]
        
        created_departments = [root_department]
        
        for dept_data in sub_departments:
            department = Department(
                name=dept_data['name'],
                description=dept_data['description'],
                parent_id=root_department.id,
                level=2,
                sort_order=dept_data['sort_order'],
                status=Department.STATUS_ACTIVE
            )
            
            self.db.add(department)
            await self.db.flush()  # 获取ID
            
            # 设置路径
            department.path = f'{root_department.path}{department.id}/'
            
            created_departments.append(department)
            logger.info(f"创建子部门: {dept_data['name']}")
        
        await self.db.commit()
        logger.info(f"默认部门结构初始化完成，共创建 {len(created_departments)} 个部门")
        
        return created_departments
    
    async def run(self):
        """运行初始化流程"""
        try:
            logger.info("开始初始化部门管理系统...")
            
            # 1. 初始化权限
            permissions = await self.init_permissions()
            
            # 2. 为管理员分配权限
            await self.assign_permissions_to_admin(permissions)
            
            # 3. 初始化默认部门结构
            departments = await self.init_default_departments()
            
            logger.info("部门管理系统初始化完成！")
            
            # 打印创建的部门结构
            logger.info("\n创建的部门结构：")
            for dept in departments:
                indent = "  " * (dept.level - 1)
                logger.info(f"{indent}- {dept.name} (ID: {dept.id}, 层级: {dept.level})")
            
            return True
            
        except Exception as e:
            logger.error(f"初始化过程中发生错误: {str(e)}")
            await self.db.rollback()
            return False


async def main():
    """主函数"""
    try:
        # 获取数据库会话
        async with AsyncSessionLocal() as db:
            initializer = DepartmentInitializer(db)
            success = await initializer.run()
            
            if success:
                print("\n✅ 部门管理系统初始化成功！")
                print("\n可以通过以下接口测试部门功能：")
                print("- GET /api/v1/departments/tree - 获取部门树")
                print("- GET /api/v1/departments/ - 获取部门列表")
                print("- POST /api/v1/departments/ - 创建新部门")
                print("- GET /api/v1/departments/statistics - 获取部门统计")
            else:
                print("\n❌ 部门管理系统初始化失败！")
                sys.exit(1)
            
    except Exception as e:
        logger.error(f"初始化脚本执行失败: {str(e)}")
        print(f"\n❌ 初始化脚本执行失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # 设置日志级别
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("🚀 开始初始化部门管理系统...")
    asyncio.run(main())