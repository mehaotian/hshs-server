# API开发统一规范与问题记录

## 文档说明

本文档记录了在API开发过程中遇到的统一性问题、解决方案和最佳实践，旨在提高代码质量和开发效率，确保项目的一致性和可维护性。

## 1. 响应格式统一化

### 1.1 问题描述

在项目开发过程中，不同接口的响应格式不统一，特别是分页接口的返回格式存在差异，影响前端开发体验和代码维护。

### 1.2 解决方案

#### 标准响应格式

所有API接口必须使用统一的响应格式：

```json
{
  "code": 0,
  "message": "操作成功",
  "data": {},
}
```

#### 分页响应格式

所有分页接口必须使用 `ResponseBuilder.paginated()` 方法：

```python
# ❌ 错误做法 - 自定义分页格式
return ResponseBuilder.success(
    data={
        "list": data_list,
        "pagination": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    }
)

# ✅ 正确做法 - 使用统一的分页响应
return ResponseBuilder.paginated(
    data=data_list,
    page=page,
    size=page_size,
    total=total,
    message="获取列表成功"
)
```

标准分页响应格式：

```json
{
  "code": 0,
  "message": "获取列表成功",
  "data": {
    "list": [],
    "pagination": {
      "page": 1,
      "size": 20,
      "total": 100,
      "pages": 5,
      "has_next": true,
      "has_prev": false
    }
  }
}
```

### 1.3 实施检查清单

- [ ] 所有接口使用 `ResponseBuilder` 类的方法
- [ ] 分页接口统一使用 `ResponseBuilder.paginated()`
- [ ] 错误响应使用对应的错误方法（如 `ResponseBuilder.business_error()`）
- [ ] 响应消息使用中文，语义明确

## 2. 数据库外键约束处理

### 2.1 问题描述

在处理树形结构数据（如部门层级）时，前端传递 `parent_id=0` 表示根节点，但数据库外键约束要求 `parent_id` 为 `NULL` 或有效的外键值，导致约束冲突。

### 2.2 解决方案

#### 统一处理规则

在所有涉及父子关系的业务逻辑中，统一将 `parent_id=0` 转换为 `None`：

```python
# 在 Service 层统一处理
def normalize_parent_id(parent_id: Optional[int]) -> Optional[int]:
    """标准化父级ID，将0转换为None"""
    return None if parent_id == 0 else parent_id

# 在创建、更新、移动等操作中应用
async def create_department(self, department_data: DepartmentCreate) -> Department:
    # 标准化 parent_id
    department_data.parent_id = normalize_parent_id(department_data.parent_id)
    # ... 其他业务逻辑
```

#### 应用场景

- 部门创建：`create_department`
- 部门更新：`update_department`
- 部门移动：`move_department`
- 其他树形结构数据操作

### 2.3 最佳实践

1. **在 Service 层处理**：不要在 API 层或数据库层处理，保持业务逻辑集中
2. **统一函数**：创建通用的标准化函数，避免重复代码
3. **文档说明**：在相关方法中添加注释说明处理逻辑

## 3. JSON序列化问题

### 3.1 常见问题

#### 日期时间序列化

```python
# ❌ 问题：datetime对象无法直接序列化
return {"created_at": datetime.now()}

# ✅ 解决：使用Pydantic模型或手动转换
class ResponseModel(BaseModel):
    created_at: datetime
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

#### Decimal类型序列化

```python
# ❌ 问题：Decimal对象序列化精度问题
from decimal import Decimal
price = Decimal('99.99')

# ✅ 解决：在Pydantic模型中正确配置
class ProductModel(BaseModel):
    price: Decimal
    
    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }
```

### 3.2 解决方案

1. **统一使用Pydantic模型**：定义响应模型，自动处理序列化
2. **配置JSON编码器**：在模型配置中指定特殊类型的序列化方式
3. **避免直接返回ORM对象**：始终通过Pydantic模型转换

## 4. 接口生成规则

### 4.1 URL命名规范

#### RESTful风格

```python
# 资源操作
GET    /api/v1/departments/list          # 获取列表
POST   /api/v1/departments/add           # 创建资源
GET    /api/v1/departments/detail/{id}   # 获取详情
PUT    /api/v1/departments/update/{id}   # 更新资源
DELETE /api/v1/departments/delete/{id}  # 删除资源

# 特殊操作
POST   /api/v1/departments/move/{id}     # 移动部门
GET    /api/v1/departments/tree/list     # 获取树形结构
GET    /api/v1/departments/statistics/list # 获取统计信息
```

#### 命名约定

- 使用复数形式：`departments`、`users`、`roles`
- 动作使用动词：`add`、`update`、`delete`、`move`
- 特殊视图使用描述性名称：`tree/list`、`statistics/list`

### 4.2 参数规范

#### 分页参数

```python
# 统一的分页参数
page: int = Query(1, ge=1, description="页码")
size: int = Query(20, ge=1, le=100, description="每页数量")
```

#### 搜索参数

```python
# 统一的搜索参数
keyword: Optional[str] = Query(None, description="搜索关键词")
status: Optional[str] = Query(None, description="状态筛选")
created_after: Optional[str] = Query(None, description="创建时间起始")
created_before: Optional[str] = Query(None, description="创建时间结束")
```

#### 排序参数

```python
# 统一的排序参数
sort_by: Optional[str] = Query("created_at", description="排序字段")
sort_order: Optional[str] = Query("asc", description="排序方向")
```

### 4.3 响应模型规范

#### 列表响应模型

```python
class DepartmentListResponse(BaseModel):
    """部门列表响应模型"""
    id: int
    name: str
    parent_id: Optional[int]
    level: int
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

#### 详情响应模型

```python
class DepartmentDetailResponse(DepartmentListResponse):
    """部门详情响应模型"""
    description: Optional[str]
    path: str
    children_count: int
    member_count: int
```

## 5. 权限控制统一化

### 5.1 权限装饰器使用

```python
# 统一使用权限装饰器
@router.get("/list")
async def get_departments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("department:read"))
):
    pass

@router.post("/add")
async def create_department(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("department:create"))
):
    pass
```

### 5.2 权限命名规范

- 格式：`{resource}:{action}`
- 资源：`user`、`department`、`role`、`script`
- 动作：`read`、`create`、`update`、`delete`、`manage`

## 6. 错误处理统一化

### 6.1 异常处理模式

```python
@router.post("/add")
async def create_department(
    department_data: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("department:create"))
):
    try:
        service = DepartmentService(db)
        result = await service.create_department(department_data)
        return ResponseBuilder.success(
            data=result,
            message="部门创建成功"
        )
    except BaseCustomException:
        # 让自定义异常传播到全局异常处理器
        raise
    except Exception as e:
        logger.error(f"Failed to create department: {str(e)}")
        raise_business_error("部门创建失败", 1000)
```

### 6.2 日志记录规范

```python
# 统一的日志格式
logger.error(f"Failed to {operation}: {str(e)}")
logger.info(f"User {user_id} performed {operation} on {resource}")
logger.warning(f"Invalid request: {validation_error}")
```

## 7. 测试规范

### 7.1 API测试模板

```python
# 测试文件命名：test_{module_name}.py
# 测试类命名：Test{ModuleName}API
# 测试方法命名：test_{operation}_{scenario}

class TestDepartmentAPI:
    async def test_create_department_success(self):
        """测试成功创建部门"""
        pass
    
    async def test_create_department_invalid_parent(self):
        """测试创建部门时父部门无效"""
        pass
    
    async def test_get_departments_with_pagination(self):
        """测试分页获取部门列表"""
        pass
```

### 7.2 测试数据管理

- 使用fixture创建测试数据
- 测试后清理数据
- 使用独立的测试数据库

## 8. 代码审查检查清单

### 8.1 API接口检查

- [ ] 使用统一的响应格式
- [ ] 分页接口使用 `ResponseBuilder.paginated()`
- [ ] 权限控制正确配置
- [ ] 异常处理完整
- [ ] 日志记录规范
- [ ] 参数验证充分

### 8.2 数据处理检查

- [ ] 外键约束处理正确
- [ ] JSON序列化无问题
- [ ] 数据类型转换安全
- [ ] 空值处理完善

### 8.3 性能检查

- [ ] 避免N+1查询问题
- [ ] 使用适当的数据库索引
- [ ] 分页查询优化
- [ ] 缓存策略合理

## 9. 持续改进

### 9.1 问题收集

定期收集开发过程中遇到的新问题，更新本文档。

### 9.2 最佳实践分享

团队成员分享解决方案和优化经验，持续完善开发规范。

### 9.3 工具支持

- 使用代码检查工具（如 pylint、black）
- 配置pre-commit钩子
- 集成自动化测试

## 10. 相关文档

- [后端开发规范](./后端开发规范.md)
- [数据库设计方案](./数据库设计方案.md)
- [API文档](../docs/frontend-api-guide.md)
- [测试规范](./规范/测试规范.md)

---