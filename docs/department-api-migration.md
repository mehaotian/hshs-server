# 部门接口地址重构说明

## 概述

为了保持项目接口地址的一致性，部门管理相关接口已从 RESTful 风格重构为与其他模块一致的地址模式（如用户接口的 `/add`、`/update/{id}` 等格式）。

## 接口地址变更对比

### 部门管理接口

| 功能 | 原地址 | 新地址 | HTTP方法 |
|------|--------|--------|----------|
| 创建部门 | `POST /departments/` | `POST /departments/add` | POST |
| 获取部门列表 | `GET /departments/` | `GET /departments/list` | GET |
| 获取部门详情 | `GET /departments/{id}` | `GET /departments/detail/{id}` | GET |
| 更新部门信息 | `PUT /departments/{id}` | `PUT /departments/update/{id}` | PUT |
| 删除部门 | `DELETE /departments/{id}` | `DELETE /departments/delete/{id}` | DELETE |
| 获取部门树 | `GET /departments/tree` | `GET /departments/tree/list` | GET |
| 获取统计信息 | `GET /departments/statistics` | `GET /departments/statistics/list` | GET |
| 移动部门 | `POST /departments/{id}/move` | `POST /departments/move/{id}` | POST |
| 批量操作部门 | `POST /departments/batch` | `POST /departments/batch/operation` | POST |

### 部门成员管理接口

| 功能 | 原地址 | 新地址 | HTTP方法 |
|------|--------|--------|----------|
| 添加部门成员 | `POST /departments/{dept_id}/members` | `POST /departments/members/add/{dept_id}` | POST |
| 获取成员列表 | `GET /departments/{dept_id}/members` | `GET /departments/members/list/{dept_id}` | GET |
| 更新成员信息 | `PUT /departments/{dept_id}/members/{member_id}` | `PUT /departments/members/update/{dept_id}/{member_id}` | PUT |
| 移除部门成员 | `DELETE /departments/{dept_id}/members/{member_id}` | `DELETE /departments/members/remove/{dept_id}/{member_id}` | DELETE |

## 设计原则

### 1. 一致性原则

- 与用户接口保持一致的地址模式
- 避免同一个接口使用不同HTTP方法的设计
- 统一使用动词+名词的地址格式

### 2. 语义化原则

- `/add` - 创建资源
- `/list` - 获取资源列表
- `/detail/{id}` - 获取单个资源详情
- `/update/{id}` - 更新资源
- `/delete/{id}` - 删除资源

### 3. 层次化原则

- 主要功能直接在根路径下：`/departments/add`
- 子功能使用分组：`/departments/members/add/{dept_id}`
- 特殊功能使用描述性路径：`/departments/tree/list`

## 兼容性说明

### 向后兼容

- 原有接口地址已完全替换，不再支持
- 建议前端应用尽快更新接口调用地址

### 迁移建议

1. 更新前端API调用地址
2. 更新API文档和测试用例
3. 通知相关开发人员接口变更

## 示例代码

### JavaScript/TypeScript 示例

```javascript
// 原来的调用方式
const departments = await api.get('/departments/');
const department = await api.get(`/departments/${id}`);
const newDept = await api.post('/departments/', data);
const updatedDept = await api.put(`/departments/${id}`, data);
await api.delete(`/departments/${id}`);

// 新的调用方式
const departments = await api.get('/departments/list');
const department = await api.get(`/departments/detail/${id}`);
const newDept = await api.post('/departments/add', data);
const updatedDept = await api.put(`/departments/update/${id}`, data);
await api.delete(`/departments/delete/${id}`);
```

### Python 示例

```python
# 原来的调用方式
departments = requests.get(f'{base_url}/departments/')
department = requests.get(f'{base_url}/departments/{id}')
new_dept = requests.post(f'{base_url}/departments/', json=data)
updated_dept = requests.put(f'{base_url}/departments/{id}', json=data)
requests.delete(f'{base_url}/departments/{id}')

# 新的调用方式
departments = requests.get(f'{base_url}/departments/list')
department = requests.get(f'{base_url}/departments/detail/{id}')
new_dept = requests.post(f'{base_url}/departments/add', json=data)
updated_dept = requests.put(f'{base_url}/departments/update/{id}', json=data)
requests.delete(f'{base_url}/departments/delete/{id}')
```

## 测试验证

项目根目录下的 `test_department_api.py` 脚本可用于验证新接口地址的可用性：

```bash
python test_department_api.py
```

## 相关文件

- 主要修改文件：`app/api/v1/departments.py`
- 测试脚本：`test_department_api.py`
- 接口文档：`docs/department-management.md`（需要同步更新）

## 注意事项

1. **认证要求**：所有接口仍需要有效的JWT token
2. **权限检查**：接口权限要求保持不变
3. **请求参数**：请求体和查询参数格式保持不变
4. **响应格式**：响应数据结构保持不变
5. **错误处理**：错误码和错误信息保持不变

## 更新日期

- 重构完成时间：2025-07-10
- 文档版本：v1.0
- 负责人：开发团队
