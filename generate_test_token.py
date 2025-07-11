#!/usr/bin/env python3
"""
生成测试用的JWT token
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.auth import AuthManager
from datetime import timedelta

def generate_test_token():
    """生成测试token"""
    auth_manager = AuthManager()
    
    # 创建一个测试用户的token数据
    token_data = {
        "sub": "34",  # 使用admin123用户的ID
        "username": "admin123",
        "type": "access"
    }
    
    # 创建token，有效期1小时
    token = auth_manager.create_access_token(
        data=token_data,
        expires_delta=timedelta(hours=1)
    )
    
    print(f"Generated test token: {token}")
    return token

if __name__ == "__main__":
    token = generate_test_token()