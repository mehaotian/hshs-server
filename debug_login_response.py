#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试登录响应
"""

import requests
import json

# 测试配置
BASE_URL = "http://localhost:8000"
LOGIN_URL = f"{BASE_URL}/api/v1/auth/login"

# 测试用户凭据
test_credentials = {
    "username": "admin",
    "password": "admin123"
}

def debug_login():
    print("=== 调试登录响应 ===")
    
    try:
        # 发送登录请求
        print(f"发送登录请求到: {LOGIN_URL}")
        print(f"请求数据: {json.dumps(test_credentials, indent=2)}")
        
        response = requests.post(LOGIN_URL, json=test_credentials)
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        try:
            response_data = response.json()
            print(f"响应数据: {json.dumps(response_data, indent=2, ensure_ascii=False)}")
        except:
            print(f"响应文本: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务器，请确保服务器正在运行")
    except Exception as e:
        print(f"❌ 调试过程中发生错误: {e}")

if __name__ == "__main__":
    debug_login()