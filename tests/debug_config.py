#!/usr/bin/env python3
"""调试配置加载问题"""

import os
from pathlib import Path

# 设置环境变量
os.environ.setdefault("PYTHONPATH", str(Path(__file__).parent))

try:
    from app.core.config import Settings
    print("✅ 配置加载成功")
    settings = Settings()
    print(f"BACKEND_CORS_ORIGINS: {settings.BACKEND_CORS_ORIGINS}")
    print(f"类型: {type(settings.BACKEND_CORS_ORIGINS)}")
except Exception as e:
    print(f"❌ 配置加载失败: {e}")
    import traceback
    traceback.print_exc()
    
    # 尝试直接读取 .env 文件
    print("\n--- 直接读取 .env 文件 ---")
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file) as f:
            for line_num, line in enumerate(f, 1):
                if "BACKEND_CORS_ORIGINS" in line:
                    print(f"第 {line_num} 行: {line.strip()}")
    else:
        print(".env 文件不存在")