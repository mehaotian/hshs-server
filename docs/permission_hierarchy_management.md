# 权限层级管理功能文档

## 功能概述

权限层级管理功能允许创建具有父子关系的权限结构，支持多级权限分类和组织。系统会自动计算和维护权限的层级（level）和路径（path）信息。

## 核心特性

### 1. 自动层级计算

- **level 字段**：系统自动计算权限的层级深度
  - 根权限：level = 0
  - 子权限：level = 父权限.level + 1
- **path 字段**：系统自动生成权限的完整路径
  - 根权限：path = 权限名称
  - 子权限：path = 父权限路径/权限名称
  - 使用 `/` 作为路径分隔符

### 2. 前端接口简化

- 创建权限时，前端**无需传递** `level` 和 `path` 字段
- 系统会根据 `parent_id` 自动计算这些字段
- 减少前端开发复杂度和出错概率

### 3. 动态层级重计算

- 当权限的 `parent_id` 发生变化时，系统会：
  - 重新计算该权限的 `level` 和 `path`
  - 递归更新所有子权限的层级信息
  - 确保整个权限树的一致性

## API 接口

### 创建权限

```http
POST /api/v1/permissions
```

**请求体示例：**

```json
{
  "name": "user_management",
  "display_name": "用户管理",
  "description": "用户管理相关权限",
  "parent_id": null,
  "module": "user",
  "action": "manage",
  "resource": "user"
}
```

**响应示例：**

```json
{
  "id": 1,
  "name": "user_management",
  "display_name": "用户管理",
  "description": "用户管理相关权限",
  "parent_id": null,
  "level": 0,
  "path": "user_management",
  "module": "user",
  "action": "manage",
  "resource": "user"
}
```

### 更新权限

```http
PUT /api/v1/permissions/{permission_id}
```

**移动权限到新父权限：**

```json
{
  "parent_id": 2
}
```

**移动权限为根权限：**

```json
{
  "parent_id": null
}
```

## 数据库设计

### Permission 模型字段

| 字段名 | 类型 | 说明 | 自动计算 |
|--------|------|------|----------|
| id | Integer | 主键 | ❌ |
| name | String | 权限名称 | ❌ |
| display_name | String | 显示名称 | ❌ |
| description | String | 描述 | ❌ |
| parent_id | Integer | 父权限ID | ❌ |
| level | Integer | 层级深度 | ✅ |
| path | String | 完整路径 | ✅ |
| module | String | 模块 | ❌ |
| action | String | 操作 | ❌ |
| resource | String | 资源 | ❌ |
| is_system | Boolean | 系统权限 | ❌ |
| sort_order | Integer | 排序 | ❌ |

### 层级结构示例

```
用户管理 (level: 0, path: "user_management")
├── 用户查看 (level: 1, path: "user_management/user_view")
├── 用户创建 (level: 1, path: "user_management/user_create")
└── 用户编辑 (level: 1, path: "user_management/user_edit")
    ├── 基本信息编辑 (level: 2, path: "user_management/user_edit/basic_info")
    └── 权限编辑 (level: 2, path: "user_management/user_edit/permissions")
```

## 核心服务方法

### RoleService 类方法

#### `create_permission(permission_data: PermissionCreate) -> Permission`

- 创建新权限
- 自动计算 `level` 和 `path` 字段
- 验证父权限存在性

#### `update_permission(permission_id: int, permission_data: PermissionUpdate) -> Permission`

- 更新权限信息
- 当 `parent_id` 变化时，触发层级重计算
- 防止循环引用

#### `_recalculate_permission_hierarchy(permission_id: int) -> None`

- 重新计算指定权限的层级和路径
- 递归更新所有子权限

#### `_recalculate_children_hierarchy(parent_id: int, parent_level: int, parent_path: str) -> None`

- 递归重新计算子权限的层级和路径

#### `_get_permission_ancestors(permission_id: int) -> List[Permission]`

- 获取权限的所有祖先权限
- 用于防止循环引用检查

## 业务规则

### 1. 权限创建规则

- 权限名称在同一层级下必须唯一
- 父权限必须存在（如果指定）
- 系统自动分配 `level` 和 `path`

### 2. 权限更新规则

- 系统权限的关键字段不可修改
- 不能将权限移动到自己的子权限下（防止循环引用）
- 父权限变化时自动重计算层级结构

### 3. 权限删除规则

- 系统权限不可删除
- 删除权限时会级联删除所有子权限

## 安全考虑

### 1. 循环引用防护

- 更新权限父子关系时检查是否会形成循环
- 使用祖先权限列表进行验证

### 2. 系统权限保护

- 系统权限的关键字段不可修改
- 系统权限不可删除

### 3. 数据一致性

- 使用数据库事务确保操作原子性
- 层级变更时同步更新所有相关权限

## 测试验证

项目包含完整的权限层级管理测试脚本 `test_permission_hierarchy.py`，验证以下功能：

1. ✅ 创建根权限、子权限、孙权限
2. ✅ 自动计算 `level` 和 `path` 字段
3. ✅ 更新权限父子关系
4. ✅ 层级结构重计算
5. ✅ 权限移动和重组
6. ✅ 测试数据清理

## 使用示例

### 创建权限层级结构

```python
# 1. 创建根权限
root_permission = await role_service.create_permission(
    PermissionCreate(
        name="system_management",
        display_name="系统管理",
        description="系统管理相关权限"
    )
)
# 结果: level=0, path="system_management"

# 2. 创建子权限
child_permission = await role_service.create_permission(
    PermissionCreate(
        name="user_management",
        display_name="用户管理",
        description="用户管理权限",
        parent_id=root_permission.id
    )
)
# 结果: level=1, path="system_management/user_management"

# 3. 移动权限
await role_service.update_permission(
    child_permission.id,
    PermissionUpdate(parent_id=None)  # 移动为根权限
)
# 结果: level=0, path="user_management"
```

## 总结

权限层级管理功能提供了完整的权限树结构管理能力，通过自动计算层级和路径信息，简化了前端开发工作，同时确保了数据的一致性和完整性。该功能支持动态的权限重组和层级调整，为复杂的权限管理需求提供了强大的基础支持。
