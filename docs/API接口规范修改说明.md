# API接口规范修改说明

## 修改目标

为了统一API接口规范，确保所有增删改查操作使用一致的路径命名规则：
- 创建操作：使用 `/add` 路径
- 更新操作：使用 `/update/{id}` 路径
- 删除操作：使用 `/delete/{id}` 路径
- 详情查询：使用 `/detail/{id}` 路径

## 修改内容

### 权限管理接口修改

#### 1. 角色权限分配接口
- **修改前**: `POST /roles/{role_id}/permissions`
- **修改后**: `POST /roles/{role_id}/permissions/add`
- **说明**: 为角色分配权限的接口路径规范化

#### 2. 角色权限移除接口
- **修改前**: `DELETE /roles/{role_id}/permissions/{permission_id}`
- **修改后**: `DELETE /roles/{role_id}/permissions/delete/{permission_id}`
- **说明**: 移除角色权限的接口路径规范化

#### 3. 权限详情接口
- **修改前**: `GET /roles/permissions/{permission_id}`
- **修改后**: `GET /roles/permissions/detail/{permission_id}`
- **说明**: 获取权限详情的接口路径规范化，避免与其他操作路径冲突

### 部门管理接口修改

#### 1. 部门成员删除接口
- **修改前**: `DELETE /departments/members/remove/{department_id}/{member_id}`
- **修改后**: `DELETE /departments/members/delete/{department_id}/{member_id}`
- **说明**: 移除部门成员的接口路径规范化

#### 2. 副部长删除接口
- **修改前**: `DELETE /departments/remove-deputy-manager/{department_id}/{user_id}`
- **修改后**: `DELETE /departments/delete-deputy-manager/{department_id}/{user_id}`
- **说明**: 移除副部长的接口路径规范化

### 剧本管理接口修改

#### 1. 创建剧本接口
- **修改前**: `POST /scripts/`
- **修改后**: `POST /scripts/add`
- **说明**: 创建剧本的接口路径规范化

#### 2. 创建章节接口
- **修改前**: `POST /scripts/{script_id}/chapters`
- **修改后**: `POST /scripts/{script_id}/chapters/add`
- **说明**: 创建章节的接口路径规范化

### 音频管理接口修改

#### 1. 创建CV录音接口
- **修改前**: `POST /audios/recordings`
- **修改后**: `POST /audios/recordings/add`
- **说明**: 创建CV录音的接口路径规范化

#### 2. 创建审听记录接口
- **修改前**: `POST /audios/reviews`
- **修改后**: `POST /audios/reviews/add`
- **说明**: 创建审听记录的接口路径规范化

#### 3. 创建反音记录接口
- **修改前**: `POST /audios/feedback`
- **修改后**: `POST /audios/feedback/add`
- **说明**: 创建反音记录的接口路径规范化

## 影响范围

### 后端代码修改
- `app/api/v1/roles.py`: 更新权限管理相关路由定义
- `app/api/v1/departments.py`: 更新部门管理相关路由定义
- `app/api/v1/scripts.py`: 更新剧本管理相关路由定义
- `app/api/v1/audios.py`: 更新音频管理相关路由定义

### 前端影响
所有涉及以下操作的前端代码都需要更新API调用路径：
- 权限管理：角色权限分配、移除、权限详情查询
- 部门管理：部门成员删除、副部长删除
- 剧本管理：创建剧本、创建章节
- 音频管理：创建CV录音、创建审听记录、创建反音记录

## 注意事项

1. 所有修改都保持向后兼容性，旧的路径暂时保留但标记为废弃
2. 前端需要逐步迁移到新的API路径
3. 文档和测试用例需要同步更新
4. 部署时需要确保前后端版本兼容性

## 修改时间

- 初始修改：2024年当前日期
- 最后更新：2024年当前日期