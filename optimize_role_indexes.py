#!/usr/bin/env python3
"""
角色查询性能优化脚本
添加必要的数据库索引以提高查询性能
"""

import asyncio
from sqlalchemy import text
from app.core.database import engine
from app.core.config import settings
from app.core.logger import logger


async def create_role_indexes():
    """创建角色相关的数据库索引"""
    
    # 需要创建的索引列表
    indexes = [
        # 角色表索引
        "CREATE INDEX IF NOT EXISTS idx_roles_display_name ON roles(display_name);",
        "CREATE INDEX IF NOT EXISTS idx_roles_is_system ON roles(is_system);",
        "CREATE INDEX IF NOT EXISTS idx_roles_sort_order ON roles(sort_order);",
        "CREATE INDEX IF NOT EXISTS idx_roles_created_at ON roles(created_at);",
        "CREATE INDEX IF NOT EXISTS idx_roles_name_display_name ON roles(name, display_name);",
        
        # 用户角色关联表索引
        "CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_user_roles_role_id ON user_roles(role_id);",
        "CREATE INDEX IF NOT EXISTS idx_user_roles_expires_at ON user_roles(expires_at);",
        "CREATE INDEX IF NOT EXISTS idx_user_roles_assigned_at ON user_roles(assigned_at);",
        
        # 权限表索引
        "CREATE INDEX IF NOT EXISTS idx_permissions_module ON permissions(module);",
        "CREATE INDEX IF NOT EXISTS idx_permissions_action ON permissions(action);",
        "CREATE INDEX IF NOT EXISTS idx_permissions_resource ON permissions(resource);",
        "CREATE INDEX IF NOT EXISTS idx_permissions_is_system ON permissions(is_system);",
        "CREATE INDEX IF NOT EXISTS idx_permissions_sort_order ON permissions(sort_order);",
        "CREATE INDEX IF NOT EXISTS idx_permissions_display_name ON permissions(display_name);",
        
        # 复合索引用于常见查询模式
        "CREATE INDEX IF NOT EXISTS idx_roles_system_sort ON roles(is_system, sort_order);",
        "CREATE INDEX IF NOT EXISTS idx_user_roles_user_role ON user_roles(user_id, role_id);",
        "CREATE INDEX IF NOT EXISTS idx_permissions_module_action ON permissions(module, action);",
    ]
    
    async with engine.begin() as conn:
        for index_sql in indexes:
            try:
                await conn.execute(text(index_sql))
                logger.info(f"Successfully created index: {index_sql.split()[5]}")
            except Exception as e:
                logger.warning(f"Failed to create index {index_sql}: {str(e)}")
    
    logger.info("Role indexes optimization completed")


async def analyze_table_stats():
    """分析表统计信息以优化查询计划"""
    
    analyze_commands = [
        "ANALYZE roles;",
        "ANALYZE user_roles;", 
        "ANALYZE permissions;",
    ]
    
    async with engine.begin() as conn:
        for cmd in analyze_commands:
            try:
                await conn.execute(text(cmd))
                logger.info(f"Successfully analyzed: {cmd.split()[1]}")
            except Exception as e:
                logger.warning(f"Failed to analyze {cmd}: {str(e)}")


async def show_query_performance_tips():
    """显示查询性能优化建议"""
    tips = [
        "\n=== 角色查询性能优化建议 ===",
        "1. 已添加必要的数据库索引以提高查询性能",
        "2. 使用 selectinload 预加载关联数据，避免 N+1 查询",
        "3. 批量查询用户数量统计，减少数据库往返次数",
        "4. 优化搜索条件构建，复用查询逻辑",
        "5. 建议定期运行 ANALYZE 命令更新表统计信息",
        "\n=== 进一步优化建议 ===",
        "1. 考虑为大表实施分区策略",
        "2. 监控慢查询日志，识别性能瓶颈",
        "3. 使用连接池优化数据库连接管理",
        "4. 考虑实施查询结果缓存（Redis）",
        "5. 定期清理过期的用户角色关联记录",
        "\n=== 监控指标 ===",
        "1. 查询响应时间（目标：< 100ms）",
        "2. 数据库连接池使用率",
        "3. 索引命中率",
        "4. 慢查询数量和频率",
        "="*50
    ]
    
    for tip in tips:
        print(tip)


async def main():
    """主函数"""
    try:
        logger.info("Starting role query optimization...")
        
        # 创建索引
        await create_role_indexes()
        
        # 分析表统计信息
        await analyze_table_stats()
        
        # 显示优化建议
        await show_query_performance_tips()
        
        logger.info("Role query optimization completed successfully")
        
    except Exception as e:
        logger.error(f"Optimization failed: {str(e)}")
        raise


if __name__ == "__main__":
    asyncio.run(main())