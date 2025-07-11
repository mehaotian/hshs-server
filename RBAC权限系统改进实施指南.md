# RBAC权限系统改进实施指南

## 概述

本文档提供了从当前混合权限设计迁移到标准RBAC三表结构的完整实施指南，包括迁移脚本、新的权限服务和最佳实践。

## 当前问题分析

### 现有设计的问题

1. **数据库设计问题**
   - 角色表直接存储权限JSON，违反数据库范式化原则
   - 无法利用外键约束保证数据完整性
   - 权限变更时需要更新所有相关角色的JSON字段

2. **维护困难**
   - JSON字段不利于数据库索引优化
   - 难以进行复杂权限查询和统计
   - 数据冗余，存在不一致风险

3. **扩展性限制**
   - 难以实现细粒度权限控制
   - 不便于权限审计和追踪
   - 无法支持动态权限分配

## 改进方案

### 标准RBAC三表结构

```sql
-- 权限表（已存在，需要扩展）
CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    module VARCHAR(50) NOT NULL,
    action VARCHAR(50) NOT NULL,
    resource VARCHAR(50),
    is_system INTEGER DEFAULT 0,
    is_wildcard INTEGER DEFAULT 0,  -- 新增：标识通配符权限
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 角色表（已存在，需要移除permissions字段）
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    description TEXT,
    is_system INTEGER DEFAULT 0,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
    -- 移除: permissions JSON字段
);

-- 角色权限关联表（新增）
CREATE TABLE role_permissions (
    id SERIAL PRIMARY KEY,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    granted_by INTEGER REFERENCES users(id),
    granted_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT uk_role_permission UNIQUE(role_id, permission_id)
);

-- 用户角色关联表（已存在，可能需要调整）
CREATE TABLE user_roles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_by INTEGER REFERENCES users(id),
    assigned_at TIMESTAMP DEFAULT NOW(),
    revoked_at TIMESTAMP,
    is_active INTEGER DEFAULT 1,
    CONSTRAINT uk_user_role UNIQUE(user_id, role_id)
);
```

### 通配符权限支持

新设计中，通配符权限作为正式权限记录存储在`permissions`表中：

```sql
-- 示例通配符权限
INSERT INTO permissions (name, display_name, description, module, action, resource, is_wildcard, is_system) VALUES
('*', '全部权限', '拥有系统所有权限', 'system', 'manage', 'system', 1, 1),
('user:*', '用户模块全部权限', '拥有用户模块的所有权限', 'user', 'manage', 'user', 1, 1),
('script:*', '剧本模块全部权限', '拥有剧本模块的所有权限', 'script', 'manage', 'script', 1, 1),
('*:read', '全模块读取权限', '拥有所有模块的读取权限', 'system', 'read', 'system', 1, 1);
```

## 实施步骤

### 第一阶段：准备工作

1. **数据备份**
   ```bash
   # 备份当前数据库
   pg_dump -h localhost -U username -d database_name > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **代码审查**
   - 识别所有使用`role.permissions`的代码位置
   - 评估迁移影响范围
   - 制定测试计划

### 第二阶段：迁移执行

1. **运行迁移脚本**
   ```bash
   # 预览迁移
   python scripts/migrate_to_rbac.py --dry-run
   
   # 执行迁移
   python scripts/migrate_to_rbac.py --execute
   
   # 验证迁移结果
   python scripts/migrate_to_rbac.py --verify
   ```

2. **数据验证**
   - 检查权限数据完整性
   - 验证角色权限关联正确性
   - 确认通配符权限正常工作

### 第三阶段：代码重构

1. **更新权限检查逻辑**
   ```python
   # 旧代码
   if role.has_permission("user:read"):
       # 业务逻辑
   
   # 新代码
   service = RBACPermissionService(db)
   if await service.check_permission(user_id, "user:read"):
       # 业务逻辑
   ```

2. **更新API路由**
   ```python
   # 使用新的权限装饰器
   @router.get("/users/{user_id}")
   @require_permission("user:read", "user_id")
   async def get_user(user_id: int):
       # 业务逻辑
   ```

3. **更新角色管理**
   ```python
   # 角色权限分配
   await service.assign_role_to_user(user_id, role_id, assigned_by)
   
   # 权限检查
   permissions = await service.get_user_permissions(user_id)
   ```

### 第四阶段：清理和优化

1. **移除旧代码**
   - 删除`Role.permissions`字段相关代码
   - 移除旧的权限检查方法
   - 清理不再使用的工具函数

2. **性能优化**
   - 添加数据库索引
   - 实施权限缓存策略
   - 优化查询语句

## 核心文件说明

### 1. 迁移脚本

**文件**: `scripts/migrate_to_rbac.py`

**功能**:
- 创建`role_permissions`关联表
- 创建通配符权限记录
- 迁移现有角色权限数据
- 验证迁移结果
- 支持回滚操作

**使用方法**:
```bash
# 预览迁移
python scripts/migrate_to_rbac.py --dry-run

# 执行迁移
python scripts/migrate_to_rbac.py --execute

# 回滚迁移
python scripts/migrate_to_rbac.py --rollback
```

### 2. 新权限服务

**文件**: `app/services/rbac_permission_service.py`

**核心功能**:
- 权限检查和验证
- 通配符权限匹配
- 用户角色管理
- 权限缓存机制
- 权限树构建

**主要方法**:
```python
# 检查单个权限
await service.check_permission(user_id, "user:read")

# 批量权限检查
await service.check_permissions(user_id, ["user:read", "user:write"])

# 获取用户权限
permissions = await service.get_user_permissions(user_id)

# 角色分配
await service.assign_role_to_user(user_id, role_id, assigned_by)
```

### 3. 权限装饰器

**使用示例**:
```python
@require_permission("user:read")
async def get_user_profile(user_id: int):
    # 业务逻辑
    pass

@require_permission("script:write", "script_id")
async def update_script(script_id: int, data: dict):
    # 业务逻辑
    pass
```

## 通配符权限匹配规则

### 支持的通配符模式

1. **全权限**: `*`
   - 匹配所有权限
   - 通常分配给超级管理员

2. **模块通配符**: `module:*`
   - 匹配指定模块的所有权限
   - 例如：`user:*` 匹配 `user:read`, `user:write`, `user:delete`

3. **操作通配符**: `*:action`
   - 匹配所有模块的指定操作
   - 例如：`*:read` 匹配 `user:read`, `script:read`, `audio:read`

4. **资源通配符**: `module:action:*`
   - 匹配指定模块和操作的所有资源
   - 例如：`script:read:*` 匹配所有剧本的读取权限

### 匹配算法

```python
def _is_wildcard_match(self, required: str, pattern: str) -> bool:
    # 全权限通配符
    if pattern == '*':
        return True
    
    # 使用fnmatch进行通配符匹配
    if fnmatch.fnmatch(required, pattern):
        return True
    
    # 层级权限匹配
    return self._hierarchical_match(required, pattern)
```

## 性能优化建议

### 1. 数据库索引

```sql
-- 角色权限关联表索引
CREATE INDEX idx_role_permissions_role_id ON role_permissions(role_id);
CREATE INDEX idx_role_permissions_permission_id ON role_permissions(permission_id);

-- 用户角色关联表索引
CREATE INDEX idx_user_roles_user_id ON user_roles(user_id) WHERE is_active = 1;
CREATE INDEX idx_user_roles_role_id ON user_roles(role_id) WHERE is_active = 1;

-- 权限表索引
CREATE INDEX idx_permissions_module ON permissions(module);
CREATE INDEX idx_permissions_name ON permissions(name);
```

### 2. 权限缓存策略

```python
# 用户权限缓存（5分钟）
cache_key = f"user_permissions:{user_id}"
await cache_manager.set(cache_key, permissions, expire=300)

# 角色权限缓存（10分钟）
cache_key = f"role_permissions:{role_id}"
await cache_manager.set(cache_key, permissions, expire=600)
```

### 3. 批量权限检查

```python
# 避免循环查询
user_permissions = await service.get_user_permissions(user_id)
results = [
    service._match_permission(perm, user_permissions) 
    for perm in required_permissions
]
```

## 测试策略

### 1. 单元测试

```python
# 测试权限匹配
def test_wildcard_permission_matching():
    service = RBACPermissionService(mock_db)
    
    user_permissions = {'user:*', 'script:read'}
    
    assert service._match_permission('user:read', user_permissions)
    assert service._match_permission('user:write', user_permissions)
    assert service._match_permission('script:read', user_permissions)
    assert not service._match_permission('script:write', user_permissions)
```

### 2. 集成测试

```python
# 测试完整权限检查流程
async def test_permission_check_flow():
    # 创建测试用户和角色
    user = await create_test_user()
    role = await create_test_role(['user:read', 'script:*'])
    
    # 分配角色
    await service.assign_role_to_user(user.id, role.id, admin_user.id)
    
    # 测试权限检查
    assert await service.check_permission(user.id, 'user:read')
    assert await service.check_permission(user.id, 'script:write')
    assert not await service.check_permission(user.id, 'audio:read')
```

### 3. 迁移测试

```python
# 测试迁移数据一致性
async def test_migration_consistency():
    # 执行迁移
    migrator = RBACMigrator(db)
    await migrator.execute_migration()
    
    # 验证数据一致性
    inconsistencies = await migrator.check_data_consistency()
    assert len(inconsistencies) == 0
```

## 监控和维护

### 1. 权限审计

```python
# 记录权限检查日志
logger.info(
    f"权限检查: 用户{user_id} 权限'{permission}' "
    f"资源{resource_id} 结果:{has_permission}"
)

# 记录角色分配日志
logger.info(f"用户{user_id}分配角色{role_id}成功，分配者:{assigned_by}")
```

### 2. 性能监控

```python
# 监控权限检查耗时
import time

start_time = time.time()
result = await service.check_permission(user_id, permission)
end_time = time.time()

if end_time - start_time > 0.1:  # 超过100ms
    logger.warning(f"权限检查耗时过长: {end_time - start_time:.3f}s")
```

### 3. 缓存命中率监控

```python
# 监控缓存命中率
cache_stats = await cache_manager.get_stats()
logger.info(f"权限缓存命中率: {cache_stats['hit_rate']:.2%}")
```

## 常见问题和解决方案

### Q1: 迁移后权限检查失败

**原因**: 可能是通配符权限未正确创建或权限匹配逻辑有误

**解决方案**:
1. 检查通配符权限是否正确创建
2. 验证权限匹配算法
3. 查看权限检查日志

### Q2: 性能下降

**原因**: 新的三表结构需要JOIN查询，可能影响性能

**解决方案**:
1. 添加适当的数据库索引
2. 实施权限缓存
3. 优化查询语句
4. 考虑读写分离

### Q3: 数据不一致

**原因**: 迁移过程中可能出现数据丢失或错误

**解决方案**:
1. 运行数据一致性检查
2. 对比迁移前后的权限配置
3. 必要时进行数据修复

## 总结

通过实施标准RBAC三表结构，我们可以获得以下收益：

1. **数据完整性**: 通过外键约束保证数据一致性
2. **可维护性**: 标准化的数据结构便于维护和扩展
3. **查询能力**: 支持复杂的权限查询和统计
4. **审计追踪**: 完整的权限分配和变更记录
5. **性能优化**: 通过索引和缓存提升查询性能

虽然迁移过程需要一定的工作量，但长期来看，标准RBAC结构将为系统的可扩展性和可维护性提供坚实的基础。

## 相关文档

- [权限系统设计分析与改进建议.md](./权限系统设计分析与改进建议.md)
- [权限角色配置总结.md](./权限角色配置总结.md)
- [scripts/migrate_to_rbac.py](./scripts/migrate_to_rbac.py)
- [app/services/rbac_permission_service.py](./app/services/rbac_permission_service.py)