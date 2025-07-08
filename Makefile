# Makefile for HSHS Server
# 提供便捷的开发、测试、部署命令

.PHONY: help install dev test test-unit test-integration test-api test-coverage clean lint format docker-build docker-run docker-stop migrate init-db backup-db

# 默认目标
help:
	@echo "HSHS Server 开发工具"
	@echo ""
	@echo "可用命令:"
	@echo "  install          安装依赖"
	@echo "  dev              启动开发服务器"
	@echo "  test             运行所有测试"
	@echo "  test-unit        运行单元测试"
	@echo "  test-integration 运行集成测试"
	@echo "  test-api         运行API测试"
	@echo "  test-coverage    运行测试并生成覆盖率报告"
	@echo "  lint             代码检查"
	@echo "  format           代码格式化"
	@echo "  clean            清理缓存和临时文件"
	@echo "  docker-build     构建Docker镜像"
	@echo "  docker-run       运行Docker容器"
	@echo "  docker-stop      停止Docker容器"
	@echo "  migrate          运行数据库迁移"
	@echo "  init-db          初始化数据库"
	@echo "  backup-db        备份数据库"

# 安装依赖
install:
	@echo "📦 安装Python依赖..."
	pip install -r requirements.txt
	pip install -r requirements-dev.txt
	@echo "✅ 依赖安装完成"

# 安装开发依赖
install-dev:
	@echo "📦 安装开发依赖..."
	pip install pytest pytest-asyncio pytest-cov pytest-html pytest-xdist
	pip install black isort flake8 mypy
	pip install pre-commit
	pre-commit install
	@echo "✅ 开发依赖安装完成"

# 启动开发服务器
dev:
	@echo "🚀 启动开发服务器..."
	uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 运行所有测试
test:
	@echo "🧪 运行所有测试..."
	python run_tests.py --type all

# 运行单元测试
test-unit:
	@echo "🧪 运行单元测试..."
	python run_tests.py --type unit

# 运行集成测试
test-integration:
	@echo "🧪 运行集成测试..."
	python run_tests.py --type integration

# 运行API测试
test-api:
	@echo "🧪 运行API测试..."
	python run_tests.py --type api

# 运行测试并生成覆盖率报告
test-coverage:
	@echo "📊 运行测试并生成覆盖率报告..."
	python run_tests.py --coverage --html
	@echo "📋 覆盖率报告: htmlcov/index.html"
	@echo "📋 测试报告: test-results/report.html"

# 快速测试（失败时停止）
test-fast:
	@echo "⚡ 快速测试..."
	python run_tests.py --exitfirst

# 只运行失败的测试
test-failed:
	@echo "🔄 重新运行失败的测试..."
	python run_tests.py --lf

# 并行测试
test-parallel:
	@echo "🚀 并行运行测试..."
	python run_tests.py --numprocesses auto

# 代码检查
lint:
	@echo "🔍 代码检查..."
	flake8 app/ tests/ --max-line-length=120 --exclude=migrations
	mypy app/ --ignore-missing-imports
	@echo "✅ 代码检查完成"

# 代码格式化
format:
	@echo "🎨 代码格式化..."
	black app/ tests/ --line-length=120
	isort app/ tests/ --profile black
	@echo "✅ 代码格式化完成"

# 检查代码格式
format-check:
	@echo "🎨 检查代码格式..."
	black app/ tests/ --check --line-length=120
	isort app/ tests/ --check-only --profile black

# 清理缓存和临时文件
clean:
	@echo "🧹 清理缓存和临时文件..."
	python run_tests.py --clean
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	find . -type f -name ".coverage" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf test-results/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	@echo "✅ 清理完成"

# 构建Docker镜像
docker-build:
	@echo "🐳 构建Docker镜像..."
	docker build -t hshs-server:latest .
	@echo "✅ Docker镜像构建完成"

# 运行Docker容器
docker-run:
	@echo "🐳 启动Docker容器..."
	docker-compose up -d
	@echo "✅ Docker容器已启动"
	@echo "🌐 应用地址: http://localhost:8000"
	@echo "📚 API文档: http://localhost:8000/docs"

# 停止Docker容器
docker-stop:
	@echo "🐳 停止Docker容器..."
	docker-compose down
	@echo "✅ Docker容器已停止"

# 查看Docker日志
docker-logs:
	@echo "📋 查看Docker日志..."
	docker-compose logs -f

# 进入Docker容器
docker-shell:
	@echo "🐚 进入Docker容器..."
	docker-compose exec app bash

# 数据库迁移
migrate:
	@echo "🗃️ 运行数据库迁移..."
	alembic upgrade head
	@echo "✅ 数据库迁移完成"

# 创建新的迁移文件
migrate-create:
	@echo "🗃️ 创建新的迁移文件..."
	@read -p "请输入迁移描述: " desc; \
	alembic revision --autogenerate -m "$$desc"

# 初始化数据库
init-db:
	@echo "🗃️ 初始化数据库..."
	alembic upgrade head
	python -c "from app.core.init_db import init_db; import asyncio; asyncio.run(init_db())"
	@echo "✅ 数据库初始化完成"

# 重置数据库
reset-db:
	@echo "⚠️ 重置数据库..."
	@read -p "确定要重置数据库吗？这将删除所有数据 (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		alembic downgrade base; \
		alembic upgrade head; \
		python -c "from app.core.init_db import init_db; import asyncio; asyncio.run(init_db())"; \
		echo "✅ 数据库重置完成"; \
	else \
		echo "❌ 操作已取消"; \
	fi

# 备份数据库
backup-db:
	@echo "💾 备份数据库..."
	@mkdir -p backups
	@timestamp=$$(date +"%Y%m%d_%H%M%S"); \
	pg_dump $${DATABASE_URL:-postgresql://postgres:password@localhost:5432/hshs_db} > backups/backup_$$timestamp.sql; \
	echo "✅ 数据库备份完成: backups/backup_$$timestamp.sql"

# 恢复数据库
restore-db:
	@echo "📥 恢复数据库..."
	@ls -la backups/
	@read -p "请输入备份文件名: " filename; \
	if [ -f "backups/$$filename" ]; then \
		psql $${DATABASE_URL:-postgresql://postgres:password@localhost:5432/hshs_db} < backups/$$filename; \
		echo "✅ 数据库恢复完成"; \
	else \
		echo "❌ 备份文件不存在"; \
	fi

# 生成API文档
docs:
	@echo "📚 生成API文档..."
	python -c "from main import app; import json; print(json.dumps(app.openapi(), indent=2))" > docs/openapi.json
	@echo "✅ API文档已生成: docs/openapi.json"

# 安全检查
security-check:
	@echo "🔒 安全检查..."
	pip install safety bandit
	safety check
	bandit -r app/ -f json -o security-report.json
	@echo "✅ 安全检查完成"

# 性能测试
perf-test:
	@echo "⚡ 性能测试..."
	pip install locust
	locust -f tests/performance/locustfile.py --host=http://localhost:8000

# 代码质量检查
quality:
	@echo "📊 代码质量检查..."
	pip install radon
	radon cc app/ -a
	radon mi app/
	@echo "✅ 代码质量检查完成"

# 依赖检查
deps-check:
	@echo "📦 检查依赖安全性..."
	pip install pip-audit
	pip-audit
	@echo "✅ 依赖检查完成"

# 更新依赖
deps-update:
	@echo "📦 更新依赖..."
	pip install pip-tools
	pip-compile requirements.in
	pip-compile requirements-dev.in
	@echo "✅ 依赖更新完成"

# 完整的CI检查
ci:
	@echo "🔄 运行CI检查..."
	make format-check
	make lint
	make test-coverage
	make security-check
	@echo "✅ CI检查完成"

# 项目设置
setup:
	@echo "⚙️ 项目初始化设置..."
	make install-dev
	cp .env.example .env
	@echo "📝 请编辑 .env 文件配置环境变量"
	make init-db
	@echo "✅ 项目设置完成"

# 显示项目状态
status:
	@echo "📊 项目状态:"
	@echo "Python版本: $$(python --version)"
	@echo "依赖状态:"
	@pip list | grep -E "(fastapi|sqlalchemy|pydantic|uvicorn)"
	@echo "数据库状态:"
	@alembic current 2>/dev/null || echo "数据库未初始化"
	@echo "Docker状态:"
	@docker-compose ps 2>/dev/null || echo "Docker未运行"