# 部门管理系统使用指南

## 概述

部门管理系统是绘声绘社管理平台的核心模块之一，提供了完整的组织架构管理功能。支持多级部门层级结构，包含部门信息管理、成员管理、权限控制等功能。

## 功能特性

### 🏢 部门管理

- **多级层级**：支持最多10级的部门层级结构
- **树形展示**：提供树形结构的部门展示
- **灵活组织**：支持部门的创建、移动、删除等操作
- **状态管理**：支持部门的启用/停用状态管理

### 👥 成员管理

- **成员关联**：支持用户与部门的关联管理
- **职位设置**：为部门成员设置具体职位
- **负责人指定**：支持指定部门负责人
- **成员状态**：管理成员的在职/离职状态

### 🔐 权限控制

- **细粒度权限**：提供创建、查看、更新、删除等细粒度权限控制
- **角色集成**：与现有角色权限系统无缝集成
- **操作审计**：记录所有部门操作的审计日志

### 📊 统计分析

- **部门统计**：提供部门数量、成员数量等统计信息
- **层级分析**：分析部门层级分布情况
- **成员分布**：统计各部门成员分布情况

## 数据模型

### 部门表 (departments)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键ID |
| name | VARCHAR(100) | 部门名称 |
| parent_id | INTEGER | 上级部门ID |
| manager_id | INTEGER | 部门负责人ID |
| manager_phone | VARCHAR(20) | 负责人手机号 |
| manager_email | VARCHAR(100) | 负责人邮箱 |
| description | TEXT | 部门描述 |
| sort_order | INTEGER | 排序 |
| status | INTEGER | 部门状态（1-正常，2-停用） |
| level | INTEGER | 部门层级 |
| path | VARCHAR(500) | 部门路径 |
| remarks | TEXT | 备注 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |
| created_by | INTEGER | 创建人ID |
| updated_by | INTEGER | 更新人ID |

### 部门成员表 (department_members)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键ID |
| department_id | INTEGER | 部门ID |
| user_id | INTEGER | 用户ID |
| position | VARCHAR(100) | 职位 |
| is_manager | BOOLEAN | 是否为负责人 |
| status | INTEGER | 成员状态（1-正常，2-离职） |
| joined_at | TIMESTAMP | 加入时间 |
| left_at | TIMESTAMP | 离职时间 |
| remarks | TEXT | 备注 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

## API 接口文档

### 基础路径

```base
/api/v1/departments
```

### 1. 部门管理接口

#### 1.1 创建部门

```http
POST /api/v1/departments/
```

**请求体：**

```json
{
  "name": "技术部",
  "parent_id": 1,
  "manager_id": 2,
  "manager_phone": "13800138000",
  "manager_email": "manager@example.com",
  "description": "负责技术开发工作",
  "sort_order": 1,
  "remarks": "新成立的技术部门"
}
```

**响应：**

```json
{
  "code": 0,
  "message": "部门创建成功",
  "data": {
    "id": 3,
    "name": "技术部",
    "parent_id": 1,
    "manager_id": 2,
    "level": 2,
    "path": "/1/3/",
    "status": 1,
    "created_at": "2024-01-01T10:00:00Z"
  }
}
```

#### 1.2 获取部门列表

```http
GET /api/v1/departments/?page=1&page_size=20&name=技术&status=1
```

**查询参数：**

- `name`: 部门名称（模糊搜索）
- `parent_id`: 上级部门ID
- `manager_id`: 负责人ID
- `status`: 部门状态
- `level`: 部门层级
- `include_children`: 是否包含子部门
- `include_members`: 是否包含成员信息
- `page`: 页码
- `page_size`: 每页数量

**响应：**

```json
{
  "code": 0,
  "message": "获取部门列表成功",
  "data": {
    "items": [
      {
        "id": 1,
        "name": "绘声绘社",
        "parent_id": null,
        "level": 1,
        "member_count": 25,
        "children": []
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 20,
    "pages": 1
  }
}
```

#### 1.3 获取部门树

```http
GET /api/v1/departments/tree?root_id=1
```

**响应：**

```json
{
  "code": 0,
  "message": "获取部门树成功",
  "data": [
    {
      "id": 1,
      "name": "绘声绘社",
      "level": 1,
      "member_count": 5,
      "children": [
        {
          "id": 2,
          "name": "管理部",
          "level": 2,
          "member_count": 3,
          "children": []
        },
        {
          "id": 3,
          "name": "编剧部",
          "level": 2,
          "member_count": 8,
          "children": []
        }
      ]
    }
  ]
}
```

#### 1.4 获取部门详情

```http
GET /api/v1/departments/{department_id}?include_children=true&include_members=true
```

#### 1.5 更新部门信息

```http
PUT /api/v1/departments/{department_id}
```

**请求体：**

```json
{
  "name": "技术研发部",
  "description": "负责技术研发和创新工作",
  "manager_phone": "13900139000"
}
```

#### 1.6 删除部门

```http
DELETE /api/v1/departments/{department_id}?force=false
```

**查询参数：**

- `force`: 是否强制删除（包括子部门和成员）

#### 1.7 移动部门

```http
POST /api/v1/departments/{department_id}/move
```

**请求体：**

```json
{
  "new_parent_id": 2,
  "new_sort_order": 1
}
```

#### 1.8 批量操作部门

```http
POST /api/v1/departments/batch
```

**请求体：**

```json
{
  "operation": "activate",
  "department_ids": [1, 2, 3]
}
```

**支持的操作：**

- `activate`: 激活部门
- `deactivate`: 停用部门
- `delete`: 删除部门

#### 1.9 获取部门统计

```http
GET /api/v1/departments/statistics
```

**响应：**

```json
{
  "code": 0,
  "message": "获取部门统计信息成功",
  "data": {
    "total_departments": 15,
    "active_departments": 12,
    "inactive_departments": 3,
    "total_members": 85,
    "departments_by_level": {
      "1": 1,
      "2": 6,
      "3": 8
    },
    "top_departments_by_members": [
      {
        "id": 3,
        "name": "编剧部",
        "member_count": 15
      }
    ]
  }
}
```

### 2. 部门成员管理接口

#### 2.1 添加部门成员

```http
POST /api/v1/departments/{department_id}/members
```

**请求体：**

```json
{
  "user_id": 5,
  "position": "高级工程师",
  "is_manager": false,
  "remarks": "技术骨干"
}
```

#### 2.2 获取部门成员列表

```http
GET /api/v1/departments/{department_id}/members?status=1
```

**响应：**

```json
{
  "code": 0,
  "message": "获取部门成员列表成功",
  "data": [
    {
      "id": 1,
      "user_id": 5,
      "position": "高级工程师",
      "is_manager": false,
      "status": 1,
      "joined_at": "2024-01-01T10:00:00Z",
      "user": {
        "id": 5,
        "username": "zhangsan",
        "real_name": "张三",
        "display_name": "张三",
        "avatar_url": "/avatars/zhangsan.jpg"
      }
    }
  ]
}
```

#### 2.3 更新部门成员信息

```http
PUT /api/v1/departments/{department_id}/members/{member_id}
```

#### 2.4 移除部门成员

```http
DELETE /api/v1/departments/{department_id}/members/{member_id}
```

## 权限说明

### 部门权限列表

| 权限名称 | 权限标识 | 说明 |
|----------|----------|------|
| 创建部门 | `department:create` | 创建新部门的权限 |
| 查看部门 | `department:read` | 查看部门信息的权限 |
| 更新部门 | `department:update` | 更新部门信息的权限 |
| 删除部门 | `department:delete` | 删除部门的权限 |
| 管理成员 | `department:manage_members` | 管理部门成员的权限 |
| 查看统计 | `department:view_statistics` | 查看部门统计的权限 |

### 权限分配建议

- **系统管理员**：拥有所有部门权限
- **部门经理**：拥有所管理部门的查看、更新、成员管理权限
- **普通成员**：拥有部门查看权限

## 使用示例

### 1. 初始化部门结构

```bash
# 运行初始化脚本
python scripts/init_departments.py
```

### 2. 创建新部门

```javascript
// 创建技术部
const response = await fetch('/api/v1/departments/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + token
  },
  body: JSON.stringify({
    name: '技术部',
    parent_id: 1,
    description: '负责技术开发工作',
    sort_order: 1
  })
});

const result = await response.json();
console.log('部门创建结果:', result);
```

### 3. 获取部门树

```javascript
// 获取完整部门树
const response = await fetch('/api/v1/departments/tree', {
  headers: {
    'Authorization': 'Bearer ' + token
  }
});

const departments = await response.json();
console.log('部门树:', departments.data);
```

### 4. 添加部门成员

```javascript
// 为技术部添加成员
const response = await fetch('/api/v1/departments/3/members', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + token
  },
  body: JSON.stringify({
    user_id: 5,
    position: '前端工程师',
    is_manager: false
  })
});

const result = await response.json();
console.log('成员添加结果:', result);
```

## 前端集成

### Vue 3 组合式 API 示例

```vue
<template>
  <div class="department-tree">
    <el-tree
      :data="departmentTree"
      :props="treeProps"
      node-key="id"
      :expand-on-click-node="false"
      @node-click="handleNodeClick"
    >
      <template #default="{ node, data }">
        <span class="tree-node">
          <span>{{ data.name }}</span>
          <span class="member-count">({{ data.member_count }}人)</span>
        </span>
      </template>
    </el-tree>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useDepartmentApi } from '@/composables/useDepartmentApi'

const { getDepartmentTree } = useDepartmentApi()

const departmentTree = ref([])
const treeProps = {
  children: 'children',
  label: 'name'
}

const loadDepartmentTree = async () => {
  try {
    const response = await getDepartmentTree()
    departmentTree.value = response.data
  } catch (error) {
    console.error('加载部门树失败:', error)
  }
}

const handleNodeClick = (data) => {
  console.log('选中部门:', data)
}

onMounted(() => {
  loadDepartmentTree()
})
</script>
```

### React Hooks 示例

```jsx
import React, { useState, useEffect } from 'react';
import { Tree } from 'antd';
import { useDepartmentApi } from '../hooks/useDepartmentApi';

const DepartmentTree = () => {
  const [treeData, setTreeData] = useState([]);
  const [loading, setLoading] = useState(false);
  const { getDepartmentTree } = useDepartmentApi();

  const loadDepartmentTree = async () => {
    setLoading(true);
    try {
      const response = await getDepartmentTree();
      const formatTreeData = (departments) => {
        return departments.map(dept => ({
          title: `${dept.name} (${dept.member_count}人)`,
          key: dept.id,
          children: dept.children ? formatTreeData(dept.children) : []
        }));
      };
      setTreeData(formatTreeData(response.data));
    } catch (error) {
      console.error('加载部门树失败:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSelect = (selectedKeys, info) => {
    console.log('选中部门:', info.node);
  };

  useEffect(() => {
    loadDepartmentTree();
  }, []);

  return (
    <div className="department-tree">
      <Tree
        treeData={treeData}
        onSelect={handleSelect}
        loading={loading}
      />
    </div>
  );
};

export default DepartmentTree;
```

## 最佳实践

### 1. 部门结构设计

- **层级控制**：建议不超过5级层级，避免结构过于复杂
- **命名规范**：使用清晰、简洁的部门名称
- **职责明确**：每个部门应有明确的职责描述

### 2. 成员管理

- **权限最小化**：遵循最小权限原则
- **定期审查**：定期审查部门成员和权限分配
- **离职处理**：及时处理离职人员的部门关联

### 3. 性能优化

- **分页查询**：大量数据时使用分页查询
- **缓存策略**：对部门树等相对稳定的数据进行缓存
- **索引优化**：确保数据库索引配置正确

### 4. 安全考虑

- **权限验证**：所有操作都需要进行权限验证
- **操作日志**：记录重要操作的审计日志
- **数据备份**：定期备份部门数据

## 故障排除

### 常见问题

1. **部门树加载失败**
   - 检查权限配置
   - 确认数据库连接正常
   - 查看服务器日志

2. **成员添加失败**
   - 确认用户存在
   - 检查部门状态
   - 验证权限设置

3. **部门删除失败**
   - 检查是否有子部门
   - 确认是否有关联成员
   - 使用强制删除参数

### 日志查看

```bash
# 查看应用日志
tail -f logs/app.log | grep department

# 查看数据库日志
tail -f /var/log/postgresql/postgresql.log
```

## 更新日志

### v1.0.0 (2024-01-01)

- ✨ 新增部门管理基础功能
- ✨ 支持多级部门层级结构
- ✨ 实现部门成员管理
- ✨ 集成权限控制系统
- ✨ 提供完整的 REST API
- 📝 完善文档和使用示例

## 技术支持

如有问题或建议，请通过以下方式联系：

- 📧 邮箱：<support@hshs.com>
- 💬 微信群：绘声绘社技术交流群
- 🐛 问题反馈：[GitHub Issues](https://github.com/hshs/hshs-server/issues)
