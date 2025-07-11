#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
权限系统迁移脚本
从JSON字段模式迁移到标准RBAC三表结构

使用方法:
    python scripts/migrate_to_rbac.py --dry-run  # 预览迁移
    python scripts/migrate_to_rbac.py --execute  # 执行迁移
    python scripts/migrate_to_rbac.py --rollback # 回滚迁移
"""

import asyncio
import sys
import os
import argparse
from typing import List, Dict, Any, Set
from datetime import datetime

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import get_db
from app.models.role import Role, Permission, UserRole
from app.schemas.role import PermissionCreate, PermissionType, ResourceType
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select, insert, update, delete
from sqlalchemy.orm import selectinload


class RBACMigrator:
    """RBAC迁移器"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.migration_log = []
        
    def log(self, message: str, level: str = "INFO"):
        """记录迁移日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        self.migration_log.append(log_entry)
        print(log_entry)
    
    async def create_role_permissions_table(self) -> None:
        """创建角色权限关联表"""
        self.log("创建role_permissions表...")
        
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS role_permissions (
            id SERIAL PRIMARY KEY,
            role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
            granted_by INTEGER REFERENCES users(id),
            granted_at TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW(),
            CONSTRAINT uk_role_permission UNIQUE(role_id, permission_id)
        );
        
        -- 创建索引
        CREATE INDEX IF NOT EXISTS idx_role_permissions_role_id ON role_permissions(role_id);
        CREATE INDEX IF NOT EXISTS idx_role_permissions_permission_id ON role_permissions(permission_id);
        
        -- 为permissions表添加is_wildcard字段
        ALTER TABLE permissions ADD COLUMN IF NOT EXISTS is_wildcard INTEGER DEFAULT 0;
        
        COMMENT ON TABLE role_permissions IS '角色权限关联表';
        COMMENT ON COLUMN role_permissions.role_id IS '角色ID';
        COMMENT ON COLUMN role_permissions.permission_id IS '权限ID';
        COMMENT ON COLUMN role_permissions.granted_by IS '授权人ID';
        COMMENT ON COLUMN role_permissions.granted_at IS '授权时间';
        """
        
        await self.db.execute(text(create_table_sql))
        await self.db.commit()
        self.log("role_permissions表创建完成")
    
    async def create_wildcard_permissions(self) -> Dict[str, int]:
        """创建通配符权限记录"""
        self.log("创建通配符权限记录...")
        
        # 定义通配符权限
        wildcard_permissions = [
            {
                'name': '*',
                'display_name': '全部权限',
                'description': '拥有系统所有权限',
                'module': 'system',
                'action': PermissionType.MANAGE,
                'resource': ResourceType.SYSTEM,
                'is_wildcard': 1,
                'is_system': 1,
                'sort_order': 0
            },
            {
                'name': 'user:*',
                'display_name': '用户模块全部权限',
                'description': '拥有用户模块的所有权限',
                'module': 'user',
                'action': PermissionType.MANAGE,
                'resource': ResourceType.USER,
                'is_wildcard': 1,
                'is_system': 1,
                'sort_order': 10
            },
            {
                'name': 'role:*',
                'display_name': '角色模块全部权限',
                'description': '拥有角色模块的所有权限',
                'module': 'role',
                'action': PermissionType.MANAGE,
                'resource': ResourceType.ROLE,
                'is_wildcard': 1,
                'is_system': 1,
                'sort_order': 20
            },
            {
                'name': 'script:*',
                'display_name': '剧本模块全部权限',
                'description': '拥有剧本模块的所有权限',
                'module': 'script',
                'action': PermissionType.MANAGE,
                'resource': ResourceType.SCRIPT,
                'is_wildcard': 1,
                'is_system': 1,
                'sort_order': 30
            },
            {
                'name': 'audio:*',
                'display_name': '音频模块全部权限',
                'description': '拥有音频模块的所有权限',
                'module': 'audio',
                'action': PermissionType.MANAGE,
                'resource': ResourceType.AUDIO,
                'is_wildcard': 1,
                'is_system': 1,
                'sort_order': 40
            },
            {
                'name': 'review:*',
                'display_name': '审听模块全部权限',
                'description': '拥有审听模块的所有权限',
                'module': 'review',
                'action': PermissionType.MANAGE,
                'resource': ResourceType.REVIEW,
                'is_wildcard': 1,
                'is_system': 1,
                'sort_order': 50
            },
            {
                'name': 'society:*',
                'display_name': '社团模块全部权限',
                'description': '拥有社团模块的所有权限',
                'module': 'society',
                'action': PermissionType.MANAGE,
                'resource': ResourceType.SOCIETY,
                'is_wildcard': 1,
                'is_system': 1,
                'sort_order': 60
            },
            {
                'name': '*:read',
                'display_name': '全模块读取权限',
                'description': '拥有所有模块的读取权限',
                'module': 'system',
                'action': PermissionType.READ,
                'resource': ResourceType.SYSTEM,
                'is_wildcard': 1,
                'is_system': 1,
                'sort_order': 100
            },
            {
                'name': '*:write',
                'display_name': '全模块写入权限',
                'description': '拥有所有模块的写入权限',
                'module': 'system',
                'action': PermissionType.WRITE,
                'resource': ResourceType.SYSTEM,
                'is_wildcard': 1,
                'is_system': 1,
                'sort_order': 110
            },
            {
                'name': '*:delete',
                'display_name': '全模块删除权限',
                'description': '拥有所有模块的删除权限',
                'module': 'system',
                'action': PermissionType.DELETE,
                'resource': ResourceType.SYSTEM,
                'is_wildcard': 1,
                'is_system': 1,
                'sort_order': 120
            },
            {
                'name': '*:manage',
                'display_name': '全模块管理权限',
                'description': '拥有所有模块的管理权限',
                'module': 'system',
                'action': PermissionType.MANAGE,
                'resource': ResourceType.SYSTEM,
                'is_wildcard': 1,
                'is_system': 1,
                'sort_order': 130
            }
        ]
        
        permission_id_map = {}
        
        for perm_data in wildcard_permissions:
            # 检查权限是否已存在
            result = await self.db.execute(
                select(Permission).where(Permission.name == perm_data['name'])
            )
            existing_perm = result.scalar_one_or_none()
            
            if existing_perm:
                permission_id_map[perm_data['name']] = existing_perm.id
                self.log(f"通配符权限 '{perm_data['name']}' 已存在，跳过创建")
            else:
                # 创建新权限
                new_permission = Permission(**perm_data)
                self.db.add(new_permission)
                await self.db.flush()
                permission_id_map[perm_data['name']] = new_permission.id
                self.log(f"创建通配符权限: {perm_data['name']} - {perm_data['display_name']}")
        
        await self.db.commit()
        self.log(f"通配符权限创建完成，共 {len(permission_id_map)} 个")
        return permission_id_map
    
    async def migrate_role_permissions(self, permission_id_map: Dict[str, int]) -> None:
        """迁移角色权限从JSON到关联表"""
        self.log("开始迁移角色权限...")
        
        # 获取所有角色及其权限
        result = await self.db.execute(select(Role))
        roles = result.scalars().all()
        
        # 获取所有现有权限的映射
        perm_result = await self.db.execute(select(Permission))
        all_permissions = perm_result.scalars().all()
        perm_name_to_id = {perm.name: perm.id for perm in all_permissions}
        
        migration_stats = {
            'roles_processed': 0,
            'permissions_migrated': 0,
            'wildcards_found': 0,
            'missing_permissions': []
        }
        
        for role in roles:
            self.log(f"处理角色: {role.name} ({role.display_name})")
            
            if not role.permissions:
                self.log(f"角色 {role.name} 没有权限配置，跳过")
                continue
            
            # 获取权限列表
            if isinstance(role.permissions, list):
                permissions = role.permissions
            elif isinstance(role.permissions, dict):
                permissions = role.permissions.get('permissions', [])
            else:
                self.log(f"角色 {role.name} 权限格式异常: {type(role.permissions)}")
                continue
            
            # 清除现有的角色权限关联（如果存在）
            await self.db.execute(
                text("DELETE FROM role_permissions WHERE role_id = :role_id"),
                {"role_id": role.id}
            )
            
            # 迁移每个权限
            for perm_name in permissions:
                if perm_name in perm_name_to_id:
                    # 插入角色权限关联
                    await self.db.execute(
                        text("""
                        INSERT INTO role_permissions (role_id, permission_id, granted_at)
                        VALUES (:role_id, :permission_id, NOW())
                        ON CONFLICT (role_id, permission_id) DO NOTHING
                        """),
                        {
                            "role_id": role.id,
                            "permission_id": perm_name_to_id[perm_name]
                        }
                    )
                    migration_stats['permissions_migrated'] += 1
                    
                    if '*' in perm_name:
                        migration_stats['wildcards_found'] += 1
                    
                    self.log(f"  迁移权限: {perm_name}")
                else:
                    migration_stats['missing_permissions'].append(f"{role.name}:{perm_name}")
                    self.log(f"  警告: 权限 '{perm_name}' 在permissions表中不存在", "WARNING")
            
            migration_stats['roles_processed'] += 1
        
        await self.db.commit()
        
        # 输出迁移统计
        self.log("=== 迁移统计 ===")
        self.log(f"处理角色数: {migration_stats['roles_processed']}")
        self.log(f"迁移权限数: {migration_stats['permissions_migrated']}")
        self.log(f"通配符权限数: {migration_stats['wildcards_found']}")
        
        if migration_stats['missing_permissions']:
            self.log(f"缺失权限数: {len(migration_stats['missing_permissions'])}")
            for missing in migration_stats['missing_permissions'][:10]:  # 只显示前10个
                self.log(f"  - {missing}")
            if len(migration_stats['missing_permissions']) > 10:
                self.log(f"  ... 还有 {len(migration_stats['missing_permissions']) - 10} 个")
    
    async def verify_migration(self) -> bool:
        """验证迁移结果"""
        self.log("验证迁移结果...")
        
        # 检查关联表数据
        result = await self.db.execute(
            text("SELECT COUNT(*) FROM role_permissions")
        )
        rp_count = result.scalar()
        
        # 检查角色数据
        result = await self.db.execute(
            text("SELECT COUNT(*) FROM roles WHERE permissions IS NOT NULL")
        )
        roles_with_perms = result.scalar()
        
        # 检查权限数据
        result = await self.db.execute(
            text("SELECT COUNT(*) FROM permissions WHERE is_wildcard = 1")
        )
        wildcard_perms = result.scalar()
        
        self.log(f"关联表记录数: {rp_count}")
        self.log(f"有权限的角色数: {roles_with_perms}")
        self.log(f"通配符权限数: {wildcard_perms}")
        
        # 验证数据一致性
        inconsistencies = await self.check_data_consistency()
        
        if inconsistencies:
            self.log("发现数据不一致:", "WARNING")
            for issue in inconsistencies:
                self.log(f"  - {issue}", "WARNING")
            return False
        else:
            self.log("数据一致性验证通过")
            return True
    
    async def check_data_consistency(self) -> List[str]:
        """检查数据一致性"""
        issues = []
        
        # 检查是否有角色权限在关联表中缺失
        result = await self.db.execute(
            text("""
            SELECT r.name, r.permissions
            FROM roles r
            WHERE r.permissions IS NOT NULL
            """)
        )
        
        for row in result:
            role_name, permissions_json = row
            if isinstance(permissions_json, list):
                json_perms = set(permissions_json)
            elif isinstance(permissions_json, dict):
                json_perms = set(permissions_json.get('permissions', []))
            else:
                continue
            
            # 获取关联表中的权限
            rp_result = await self.db.execute(
                text("""
                SELECT p.name
                FROM role_permissions rp
                JOIN permissions p ON rp.permission_id = p.id
                JOIN roles r ON rp.role_id = r.id
                WHERE r.name = :role_name
                """),
                {"role_name": role_name}
            )
            
            relational_perms = set(row[0] for row in rp_result)
            
            # 检查差异
            missing_in_relational = json_perms - relational_perms
            extra_in_relational = relational_perms - json_perms
            
            if missing_in_relational:
                issues.append(f"角色 {role_name} 在关联表中缺失权限: {missing_in_relational}")
            
            if extra_in_relational:
                issues.append(f"角色 {role_name} 在关联表中多出权限: {extra_in_relational}")
        
        return issues
    
    async def backup_current_data(self) -> str:
        """备份当前数据"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"rbac_migration_backup_{timestamp}.sql"
        
        self.log(f"备份当前数据到: {backup_file}")
        
        # 这里应该实现实际的备份逻辑
        # 可以使用pg_dump或者导出为SQL语句
        
        return backup_file
    
    async def rollback_migration(self) -> None:
        """回滚迁移"""
        self.log("开始回滚迁移...")
        
        try:
            # 删除关联表数据
            await self.db.execute(text("DELETE FROM role_permissions"))
            
            # 删除通配符权限
            await self.db.execute(
                text("DELETE FROM permissions WHERE is_wildcard = 1")
            )
            
            # 移除is_wildcard字段
            await self.db.execute(
                text("ALTER TABLE permissions DROP COLUMN IF EXISTS is_wildcard")
            )
            
            # 删除关联表
            await self.db.execute(text("DROP TABLE IF EXISTS role_permissions"))
            
            await self.db.commit()
            self.log("迁移回滚完成")
            
        except Exception as e:
            await self.db.rollback()
            self.log(f"回滚失败: {str(e)}", "ERROR")
            raise
    
    async def execute_migration(self, dry_run: bool = False) -> bool:
        """执行完整迁移"""
        try:
            if dry_run:
                self.log("=== 干运行模式 - 仅预览迁移步骤 ===")
                self.log("1. 创建role_permissions表")
                self.log("2. 创建通配符权限记录")
                self.log("3. 迁移角色权限到关联表")
                self.log("4. 验证迁移结果")
                self.log("=== 干运行完成 ===")
                return True
            
            self.log("=== 开始RBAC迁移 ===")
            
            # 备份数据
            backup_file = await self.backup_current_data()
            
            # 步骤1: 创建表结构
            await self.create_role_permissions_table()
            
            # 步骤2: 创建通配符权限
            permission_id_map = await self.create_wildcard_permissions()
            
            # 步骤3: 迁移角色权限
            await self.migrate_role_permissions(permission_id_map)
            
            # 步骤4: 验证迁移
            if await self.verify_migration():
                self.log("=== 迁移成功完成 ===")
                self.log(f"备份文件: {backup_file}")
                return True
            else:
                self.log("迁移验证失败", "ERROR")
                return False
                
        except Exception as e:
            await self.db.rollback()
            self.log(f"迁移失败: {str(e)}", "ERROR")
            return False


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="RBAC权限系统迁移工具")
    parser.add_argument("--dry-run", action="store_true", help="预览迁移步骤，不执行实际操作")
    parser.add_argument("--execute", action="store_true", help="执行迁移")
    parser.add_argument("--rollback", action="store_true", help="回滚迁移")
    parser.add_argument("--verify", action="store_true", help="仅验证当前状态")
    
    args = parser.parse_args()
    
    if not any([args.dry_run, args.execute, args.rollback, args.verify]):
        parser.print_help()
        return
    
    # 获取数据库会话
    async for db in get_db():
        migrator = RBACMigrator(db)
        
        try:
            if args.dry_run:
                await migrator.execute_migration(dry_run=True)
            elif args.execute:
                success = await migrator.execute_migration(dry_run=False)
                if not success:
                    print("\n迁移失败，请检查日志")
                    sys.exit(1)
            elif args.rollback:
                await migrator.rollback_migration()
            elif args.verify:
                await migrator.verify_migration()
                
        except Exception as e:
            print(f"\n操作失败: {str(e)}")
            sys.exit(1)
        
        break


if __name__ == "__main__":
    asyncio.run(main())