# 贡献指南

感谢您对 HSHS Server 项目的关注！我们欢迎所有形式的贡献，包括但不限于：

- 🐛 报告 Bug
- 💡 提出新功能建议
- 📝 改进文档
- 🔧 提交代码修复
- ✨ 实现新功能
- 🧪 编写测试
- 📖 翻译文档

## 🚀 快速开始

### 1. Fork 项目

点击项目页面右上角的 "Fork" 按钮，将项目 fork 到您的 GitHub 账户。

### 2. 克隆项目

```bash
git clone https://github.com/your-username/hshs-server.git
cd hshs-server
```

### 3. 设置开发环境

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 安装 pre-commit 钩子
pre-commit install
```

### 4. 配置环境

```bash
# 复制环境配置
cp .env.example .env

# 启动数据库服务
docker-compose up -d postgres redis

# 运行数据库迁移
alembic upgrade head
```

### 5. 运行测试

```bash
# 运行所有测试
make test

# 或者
pytest
```

## 📋 开发流程

### 1. 创建分支

为您的贡献创建一个新分支：

```bash
git checkout -b feature/your-feature-name
# 或
git checkout -b fix/your-bug-fix
# 或
git checkout -b docs/your-documentation-update
```

分支命名规范：

- `feature/` - 新功能
- `fix/` - Bug 修复
- `docs/` - 文档更新
- `refactor/` - 代码重构
- `test/` - 测试相关
- `chore/` - 构建/工具相关

### 2. 进行开发

在开发过程中，请遵循以下原则：

- 保持代码简洁、可读
- 添加必要的注释
- 遵循项目的代码规范
- 为新功能编写测试
- 更新相关文档

### 3. 提交代码

我们使用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```bash
git add .
git commit -m "feat: 添加用户头像上传功能"
```

提交信息格式：

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

类型说明：

- `feat` - 新功能
- `fix` - Bug 修复
- `docs` - 文档更新
- `style` - 代码格式（不影响代码运行的变动）
- `refactor` - 重构（既不是新增功能，也不是修改bug的代码变动）
- `test` - 增加测试
- `chore` - 构建过程或辅助工具的变动
- `perf` - 性能优化
- `ci` - CI/CD 相关

示例：

```bash
git commit -m "feat(auth): 添加双因素认证功能"
git commit -m "fix(api): 修复用户登录时的内存泄漏问题"
git commit -m "docs: 更新 API 文档"
```

### 4. 推送分支

```bash
git push origin feature/your-feature-name
```

### 5. 创建 Pull Request

1. 访问您 fork 的项目页面
2. 点击 "New Pull Request"
3. 选择您的分支
4. 填写 PR 描述

## 📝 Pull Request 指南

### PR 标题

使用清晰、描述性的标题：

- ✅ `feat: 添加用户头像上传功能`
- ✅ `fix: 修复音频文件上传失败的问题`
- ❌ `更新代码`
- ❌ `修复bug`

### PR 描述模板

```markdown
## 变更类型
- [ ] Bug 修复
- [ ] 新功能
- [ ] 文档更新
- [ ] 代码重构
- [ ] 性能优化
- [ ] 其他

## 变更描述
简要描述您的变更内容...

## 相关 Issue
关闭 #123

## 测试
- [ ] 已添加单元测试
- [ ] 已添加集成测试
- [ ] 所有测试通过
- [ ] 手动测试通过

## 检查清单
- [ ] 代码遵循项目规范
- [ ] 已添加必要的文档
- [ ] 已更新 CHANGELOG.md
- [ ] 已通过所有检查
```

### 代码审查

所有 PR 都需要经过代码审查：

1. 至少一个维护者的批准
2. 所有 CI 检查通过
3. 没有合并冲突
4. 符合项目标准

## 🔧 代码规范

### Python 代码规范

我们使用以下工具确保代码质量：

```bash
# 代码格式化
black app/ tests/
isort app/ tests/

# 代码检查
flake8 app/ tests/
mypy app/

# 安全检查
bandit -r app/
```

### 代码风格

- 遵循 [PEP 8](https://www.python.org/dev/peps/pep-0008/) 规范
- 使用 Black 进行代码格式化（行长度 120）
- 使用 isort 进行导入排序
- 添加类型注解
- 编写清晰的文档字符串

### 示例代码

```python
from typing import Optional, List
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    """用户服务类，处理用户相关的业务逻辑。"""
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
    
    async def create_user(
        self, 
        user_data: UserCreate
    ) -> User:
        """创建新用户。
        
        Args:
            user_data: 用户创建数据
            
        Returns:
            创建的用户对象
            
        Raises:
            HTTPException: 当用户名已存在时
        """
        # 实现逻辑...
        pass
```

## 🧪 测试指南

### 测试类型

1. **单元测试** - 测试单个函数或方法
2. **集成测试** - 测试多个组件的交互
3. **API 测试** - 测试 API 端点
4. **性能测试** - 测试系统性能

### 编写测试

```python
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_create_user():
    """测试用户创建功能。"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/users",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "password123"
            }
        )
    
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_users.py::test_create_user

# 运行带覆盖率的测试
pytest --cov=app

# 运行特定标记的测试
pytest -m unit
pytest -m integration
```

## 📚 文档规范

### API 文档

使用 FastAPI 的自动文档生成功能：

```python
from fastapi import APIRouter, Depends
from app.schemas.user import UserResponse, UserCreate

router = APIRouter()

@router.post(
    "/users",
    response_model=UserResponse,
    status_code=201,
    summary="创建用户",
    description="创建一个新的用户账户",
    responses={
        201: {"description": "用户创建成功"},
        400: {"description": "请求参数错误"},
        409: {"description": "用户名或邮箱已存在"}
    }
)
async def create_user(user_data: UserCreate) -> UserResponse:
    """创建新用户。
    
    - **username**: 用户名（必填，3-50字符）
    - **email**: 邮箱地址（必填，有效邮箱格式）
    - **password**: 密码（必填，8-128字符）
    - **nickname**: 昵称（可选，1-50字符）
    """
    # 实现逻辑...
    pass
```

### 代码注释

- 使用中文注释
- 复杂逻辑必须添加注释
- 公共 API 必须有文档字符串
- 使用 Google 风格的文档字符串

## 🐛 报告 Bug

### Bug 报告模板

在创建 Issue 时，请使用以下模板：

```markdown
## Bug 描述
简要描述遇到的问题...

## 复现步骤
1. 执行操作 A
2. 执行操作 B
3. 观察到错误

## 期望行为
描述您期望发生的情况...

## 实际行为
描述实际发生的情况...

## 环境信息
- OS: [例如 macOS 12.0]
- Python: [例如 3.11.0]
- FastAPI: [例如 0.104.1]
- 浏览器: [例如 Chrome 96.0]

## 附加信息
- 错误日志
- 截图
- 其他相关信息
```

## 💡 功能建议

### 功能建议模板

```markdown
## 功能描述
简要描述建议的功能...

## 使用场景
描述什么情况下会用到这个功能...

## 解决方案
描述您认为可行的解决方案...

## 替代方案
描述您考虑过的其他解决方案...

## 附加信息
其他相关信息、参考资料等...
```

## 🏷️ Issue 标签

我们使用以下标签来分类 Issue：

- `bug` - Bug 报告
- `enhancement` - 功能增强
- `documentation` - 文档相关
- `good first issue` - 适合新手的问题
- `help wanted` - 需要帮助
- `question` - 问题咨询
- `wontfix` - 不会修复
- `duplicate` - 重复问题
- `invalid` - 无效问题

## 🎯 开发优先级

我们按以下优先级处理贡献：

1. **安全问题** - 最高优先级
2. **Bug 修复** - 高优先级
3. **性能优化** - 中等优先级
4. **新功能** - 中等优先级
5. **文档改进** - 低优先级
6. **代码重构** - 低优先级

## 📞 联系我们

如果您有任何问题或需要帮助，可以通过以下方式联系我们：

- 创建 [GitHub Issue](https://github.com/your-username/hshs-server/issues)
- 发送邮件到：<your-email@example.com>
- 加入我们的讨论群：[链接]

## 🙏 致谢

感谢所有为项目做出贡献的开发者！您的贡献让这个项目变得更好。

---

再次感谢您的贡献！🎉
