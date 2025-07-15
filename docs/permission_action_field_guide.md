# 权限 Action 字段填写指南

## 概述

本文档详细说明了权限系统中 `action`、`resource` 和 `module` 字段的用途、填写规则和最佳实践。

## 字段说明

### 1. action 字段

**用途**: 定义对资源执行的具体操作类型

**数据类型**: `Optional[str]` - 可以为 `None`、空字符串或有效的操作类型

**可选值**:

- `create` - 创建操作
- `read` - 读取/查看操作
- `update` - 更新/修改操作
- `delete` - 删除操作
- `manage` - 管理操作（通常包含多种操作）
- `assign` - 分配操作
- `execute` - 执行操作
- `upload` - 上传操作
- `download` - 下载操作
- `review` - 审核操作
- `approve` - 批准操作
- `reject` - 拒绝操作
- `config` - 配置操作
- `log` - 日志操作
- `monitor` - 监控操作
- `assign_role` - 分配角色
- `assign_permission` - 分配权限
- `manage_members` - 管理成员
- `view_statistics` - 查看统计
- `add_member` - 添加成员
- `remove_member` - 移除成员

### 2. resource 字段

**用途**: 定义权限作用的资源类型

**数据类型**: `Optional[str]` - 可以为 `None`、空字符串或资源类型

**预定义值**:

- `user` - 用户资源
- `role` - 角色资源
- `permission` - 权限资源
- `script` - 剧本资源
- `audio` - 音频资源
- `review` - 审核资源
- `society` - 社团资源
- `system` - 系统资源
- `department` - 部门资源
- `department_member` - 部门成员资源
- `content` - 内容资源

**自定义值**: 也可以使用自定义的资源类型名称

### 3. module 字段

**用途**: 定义权限所属的功能模块

**数据类型**: `Optional[str]` - 可以为 `None` 或模块名称

**示例值**:

- `user_management` - 用户管理模块
- `role_management` - 角色管理模块
- `script_management` - 剧本管理模块
- `audio_management` - 音频管理模块
- `department_management` - 部门管理模块

## 填写规则

### 根权限（分类权限）

对于根权限或分类权限，`action` 字段可以：

- 设置为 `None`
- 设置为空字符串 `""`
- 设置为具体的操作类型（如果该分类代表特定操作）

**示例**:

```python
# 用户管理分类（根权限）
PermissionCreate(
    name="user_management",
    display_name="用户管理",
    description="用户管理相关权限分类",
    module="user_management",
    action=None,  # 或 "" 或 "manage"
    resource="user",
    parent_id=None
)
```

### 具体权限（叶子权限）

对于具体的操作权限，`action` 字段应该：

- 设置为具体的操作类型
- 不能为 `None` 或空字符串

**示例**:

```python
# 创建用户权限
PermissionCreate(
    name="user_create",
    display_name="创建用户",
    description="创建新用户的权限",
    module="user_management",
    action="create",
    resource="user",
    parent_id=user_management_id
)
```

## 层级权限设计示例

### 用户管理权限层级

```
用户管理 (action: None, resource: "user")
├── 用户查看 (action: "read", resource: "user")
├── 用户创建 (action: "create", resource: "user")
├── 用户编辑 (action: "update", resource: "user")
├── 用户删除 (action: "delete", resource: "user")
└── 角色管理 (action: None, resource: "role")
    ├── 分配角色 (action: "assign_role", resource: "user")
    └── 移除角色 (action: "remove_role", resource: "user")
```

### 部门管理权限层级

```
部门管理 (action: None, resource: "department")
├── 部门查看 (action: "read", resource: "department")
├── 部门创建 (action: "create", resource: "department")
├── 部门编辑 (action: "update", resource: "department")
├── 部门删除 (action: "delete", resource: "department")
└── 成员管理 (action: None, resource: "department_member")
    ├── 添加成员 (action: "add_member", resource: "department_member")
    ├── 移除成员 (action: "remove_member", resource: "department_member")
    └── 查看统计 (action: "view_statistics", resource: "department")
```

### 剧本管理权限层级

```
剧本管理 (action: None, resource: "script")
├── 剧本查看 (action: "read", resource: "script")
├── 剧本创建 (action: "create", resource: "script")
├── 剧本编辑 (action: "update", resource: "script")
├── 剧本删除 (action: "delete", resource: "script")
└── 音频管理 (action: None, resource: "audio")
    ├── 音频上传 (action: "upload", resource: "audio")
    ├── 音频下载 (action: "download", resource: "audio")
    └── 音频删除 (action: "delete", resource: "audio")
```

## 最佳实践

### 1. 命名规范

- **权限名称**: 使用 `{resource}_{action}` 或 `{module}_{action}` 格式
- **显示名称**: 使用中文，简洁明了
- **描述**: 详细说明权限的作用和适用场景

### 2. 层级设计原则

- **逻辑清晰**: 按功能模块和操作类型进行分层
- **粒度适中**: 既不过于细化也不过于粗糙
- **易于理解**: 权限名称和层级结构应该直观易懂
- **便于管理**: 支持批量分配和继承

### 3. 字段填写建议

- **根权限**: `action` 可以为 `None`，`resource` 设置为主要资源类型
- **分类权限**: `action` 可以为 `None` 或 `"manage"`，`resource` 设置为相关资源类型
- **具体权限**: `action` 必须设置为具体操作，`resource` 设置为目标资源
- **模块字段**: 统一使用模块名称，便于权限分组和管理

### 4. 验证规则

- `action` 字段允许为 `None`、空字符串或预定义的操作类型
- `resource` 字段允许为 `None`、空字符串、预定义类型或自定义类型
- `module` 字段允许为 `None` 或自定义模块名称
- 系统会自动验证字段值的有效性，无效值会被接受但建议使用标准值

## 错误处理

### 常见错误

1. **权限名称重复**: 确保权限名称在系统中唯一
2. **父权限不存在**: 创建子权限时确保父权限ID有效
3. **循环引用**: 避免将权限设置为自己的子权限

### 解决方案

- 使用唯一的权限名称
- 验证父权限存在性
- 系统自动检测并防止循环引用

## 总结

权限系统的 `action`、`resource` 和 `module` 字段设计灵活，支持多种使用场景：

1. **根权限**: `action` 可以为 `None`，用于权限分类
2. **具体权限**: `action` 设置为具体操作类型
3. **自定义扩展**: 支持自定义 `resource` 和 `module` 值
4. **层级管理**: 自动计算权限层级和路径
5. **验证机制**: 灵活的验证规则，兼容多种使用方式

通过合理的权限设计和字段填写，可以构建出清晰、灵活、易于管理的权限体系。
