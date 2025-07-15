#!/usr/bin/env python3

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings

print(f"DATABASE_URL: {settings.DATABASE_URL}")
print(f"DEBUG: {settings.DEBUG}")
print(f"PROJECT_NAME: {settings.PROJECT_NAME}")

# 检查环境变量
print("\n环境变量:")
for key in os.environ:
    if 'DATABASE' in key.upper():
        print(f"{key}: {os.environ[key]}")