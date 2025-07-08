# HSHS Server - 剧本音频管理系统后端

[![CI/CD Pipeline](https://github.com/your-username/hshs-server/workflows/CI/CD%20Pipeline/badge.svg)](https://github.com/your-username/hshs-server/actions)
[![codecov](https://codecov.io/gh/your-username/hshs-server/branch/main/graph/badge.svg)](https://codecov.io/gh/your-username/hshs-server)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

基于 FastAPI + PostgreSQL + Redis 构建的现代化剧本音频管理系统后端服务，支持音频上传、转录、审听和管理等功能。

## ✨ 主要特性

- 🚀 **高性能异步框架**：基于 FastAPI 构建，支持高并发请求处理
- 🔐 **完整的认证授权**：JWT 认证 + RBAC 权限控制
- 📁 **文件管理**：支持音频文件上传、存储和管理
- 🎵 **音频处理**：集成 AI 音频转录和分析服务
- 📊 **数据统计**：提供丰富的数据统计和分析功能
- 🔍 **全文搜索**：基于 PostgreSQL 的全文搜索功能
- 📝 **API 文档**：自动生成的 OpenAPI 文档
- 🐳 **容器化部署**：完整的 Docker 和 Docker Compose 配置
- 🧪 **完整测试**：单元测试、集成测试和 API 测试
- 📈 **监控告警**：集成日志记录和性能监控

## 🏗️ 技术栈

- **Web框架**：FastAPI 0.104+
- **数据库**：PostgreSQL 15+ (主数据库)
- **缓存**：Redis 7+ (缓存和会话存储)
- **ORM**：SQLAlchemy 2.0+ (异步ORM)
- **认证**：JWT + Passlib (密码加密)
- **任务队列**：Celery + Redis (异步任务处理)
- **文件存储**：本地存储 / 阿里云OSS (可配置)
- **API文档**：OpenAPI 3.0 + Swagger UI
- **测试框架**：Pytest + pytest-asyncio
- **代码质量**：Black + isort + flake8 + mypy
- **容器化**：Docker + Docker Compose
- **CI/CD**：GitHub Actions

## 📋 系统要求

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (可选)

## 🚀 快速开始

### 方式一：Docker Compose (推荐)

1. **克隆项目**

```bash
git clone https://github.com/your-username/hshs-server.git
cd hshs-server
```

2. **配置环境变量**

```bash
cp .env.example .env
# 编辑 .env 文件，配置数据库连接等信息
```

3. **启动服务**

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f app
```

4. **访问服务**

- API 服务：<http://localhost:8000>
- API 文档：<http://localhost:8000/docs>
- 健康检查：<http://localhost:8000/health>

### 方式二：本地开发

#### 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

#### 配置数据库

```bash
# 启动 PostgreSQL 和 Redis
docker-compose up -d postgres redis

# 运行数据库迁移
alembic upgrade head
```

#### 启动开发服务器

```bash
# 使用 Makefile
make dev

# 或直接使用 uvicorn
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 🛠️ 开发指南

### 项目结构

```base
hshs-server/
├── app/                    # 应用主目录
│   ├── api/               # API 路由
│   │   └── v1/           # API v1 版本
│   │       ├── auth.py   # 认证相关
│   │       ├── users.py  # 用户管理
│   │       ├── roles.py  # 角色权限
│   │       ├── dramas.py # 剧本管理
│   │       └── audios.py # 音频管理
│   ├── core/              # 核心配置
│   │   ├── config.py     # 应用配置
│   │   ├── database.py   # 数据库配置
│   │   ├── auth.py       # 认证管理
│   │   ├── exceptions.py # 异常处理
│   │   └── middleware.py # 中间件
│   ├── models/            # 数据模型
│   │   ├── user.py       # 用户模型
│   │   ├── role.py       # 角色模型
│   │   ├── drama.py      # 剧本模型
│   │   └── audio.py      # 音频模型
│   ├── schemas/           # Pydantic 模式
│   ├── services/          # 业务逻辑
│   ├── utils/             # 工具函数
│   └── main.py           # 应用入口
├── tests/                 # 测试文件
│   ├── test_auth.py      # 认证测试
│   ├── test_users.py     # 用户测试
│   ├── test_roles.py     # 角色测试
│   └── conftest.py       # 测试配置
├── alembic/              # 数据库迁移
├── docker/               # Docker 配置
├── docs/                 # 项目文档
├── scripts/              # 脚本文件
├── requirements.txt      # 生产依赖
├── requirements-dev.txt  # 开发依赖
├── docker-compose.yml    # Docker Compose 配置
├── Dockerfile           # Docker 镜像配置
├── Makefile            # 开发命令
└── README.md           # 项目说明
```

### 常用命令

```bash
# 安装依赖
make install

# 启动开发服务器
make dev

# 运行测试
make test
make test-unit          # 单元测试
make test-integration   # 集成测试
make test-coverage      # 覆盖率测试

# 代码检查和格式化
make lint              # 代码检查
make format            # 代码格式化
make type-check        # 类型检查

# 数据库操作
make db-upgrade        # 运行迁移
make db-downgrade      # 回滚迁移
make db-revision       # 创建新迁移

# Docker 操作
make docker-build      # 构建镜像
make docker-run        # 运行容器
make docker-clean      # 清理容器

# 其他
make clean            # 清理缓存
make docs             # 生成文档
make security-check   # 安全检查
```

### 环境变量配置

主要环境变量说明（详见 `.env.example`）：

```bash
# 应用配置
APP_NAME="HSHS Server"
APP_VERSION="1.0.0"
DEBUG=false
ENVIRONMENT="production"

# 数据库配置
DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/hshs"

# Redis 配置
REDIS_URL="redis://localhost:6379/0"

# JWT 配置
SECRET_KEY="your-secret-key"
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 文件存储配置
UPLOAD_DIR="./uploads"
MAX_FILE_SIZE=104857600  # 100MB
```

## 🧪 测试

项目包含完整的测试套件：

```bash
# 运行所有测试
pytest

# 运行特定类型的测试
pytest -m unit          # 单元测试
pytest -m integration   # 集成测试
pytest -m api          # API 测试

# 生成覆盖率报告
pytest --cov=app --cov-report=html

# 运行性能测试
pytest -m performance
```

## 📚 API 文档

启动服务后，可以通过以下地址访问 API 文档：

- **Swagger UI**：<http://localhost:8000/docs>
- **ReDoc**：<http://localhost:8000/redoc>
- **OpenAPI JSON**：<http://localhost:8000/openapi.json>

### 主要 API 端点

#### 认证相关

- `POST /api/v1/auth/register` - 用户注册
- `POST /api/v1/auth/login` - 用户登录
- `POST /api/v1/auth/refresh` - 刷新令牌
- `POST /api/v1/auth/logout` - 用户登出

#### 用户管理

- `GET /api/v1/users/me` - 获取当前用户信息
- `PUT /api/v1/users/me` - 更新用户资料
- `GET /api/v1/users` - 获取用户列表
- `GET /api/v1/users/{id}` - 获取用户详情

#### 角色权限

- `GET /api/v1/roles` - 获取角色列表
- `POST /api/v1/roles` - 创建角色
- `GET /api/v1/permissions` - 获取权限列表

#### 剧本管理

- `POST /api/v1/dramas` - 创建剧本
- `GET /api/v1/dramas` - 获取剧本列表
- `GET /api/v1/dramas/{id}` - 获取剧本详情
- `PUT /api/v1/dramas/{id}` - 更新剧本

#### 音频管理

- `POST /api/v1/dramas/{id}/audios` - 上传音频文件
- `GET /api/v1/audios` - 获取音频列表
- `GET /api/v1/audios/{id}` - 获取音频详情
- `PUT /api/v1/audios/{id}/status` - 更新音频状态

## 🚀 部署

### 生产环境部署

1. **准备生产环境配置**

```bash
cp .env.example .env.prod
# 编辑生产环境配置
```

2. **使用 Docker Compose 部署**

```bash
# 构建生产镜像
docker-compose -f docker-compose.prod.yml build

# 启动生产服务
docker-compose -f docker-compose.prod.yml up -d
```

3. **运行数据库迁移**

```bash
docker-compose -f docker-compose.prod.yml exec app alembic upgrade head
```

### 性能优化建议

- 使用 Nginx 作为反向代理
- 配置 Redis 集群用于缓存
- 使用 CDN 加速静态资源
- 配置数据库连接池
- 启用 Gzip 压缩
- 配置日志轮转

## 🔧 故障排除

### 常见问题

1. **数据库连接失败**
   - 检查数据库服务是否启动
   - 验证连接字符串配置
   - 确认网络连接

2. **Redis 连接失败**
   - 检查 Redis 服务状态
   - 验证 Redis URL 配置

3. **文件上传失败**
   - 检查上传目录权限
   - 验证文件大小限制
   - 确认磁盘空间

4. **测试失败**
   - 确保测试数据库配置正确
   - 检查测试依赖是否安装

### 日志查看

```bash
# Docker 环境日志
docker-compose logs -f app

# 本地开发日志
tail -f logs/app.log
```

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 代码规范

- 遵循 PEP 8 代码风格
- 使用 Black 进行代码格式化
- 添加类型注解
- 编写单元测试
- 更新相关文档

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 联系方式

- 项目主页：<https://github.com/your-username/hshs-server>
- 问题反馈：<https://github.com/your-username/hshs-server/issues>
- 邮箱：<your-email@example.com>

## 🙏 致谢

感谢以下开源项目：

- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的 Python Web 框架
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL 工具包
- [PostgreSQL](https://www.postgresql.org/) - 强大的开源数据库
- [Redis](https://redis.io/) - 内存数据结构存储
- [Pydantic](https://pydantic-docs.helpmanual.io/) - 数据验证库

---

⭐ 如果这个项目对你有帮助，请给个 Star！
