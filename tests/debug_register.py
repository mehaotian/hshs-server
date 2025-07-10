#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试注册接口问题
"""

import requests
import json
import random
import string

def generate_random_string(length=8):
    """生成随机字符串"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def debug_register():
    """调试注册接口"""
    
    # 生成随机用户名和邮箱避免重复
    random_suffix = generate_random_string()
    username = f"debuguser{random_suffix}"
    email = f"debug{random_suffix}@example.com"
    
    url = "http://localhost:8000/api/v1/auth/register"
    
    test_data = {
        "username": username,
        "email": email,
        "password": "password123",
        "confirm_password": "password123",
        "full_name": "调试用户"
    }
    
    print("=" * 60)
    print("调试注册接口")
    print("=" * 60)
    print(f"请求URL: {url}")
    print(f"请求数据: {json.dumps(test_data, ensure_ascii=False, indent=2)}")
    print("-" * 40)
    
    try:
        # 发送请求
        response = requests.post(url, json=test_data, timeout=10)
        
        print(f"HTTP状态码: {response.status_code}")
        print(f"响应头: {dict(response.headers)}")
        
        # 尝试解析JSON响应
        try:
            data = response.json()
            print(f"响应数据: {json.dumps(data, indent=2, ensure_ascii=False)}")
        except json.JSONDecodeError:
            print(f"响应内容（非JSON）: {response.text}")
        
        # 检查是否有错误
        if response.status_code != 200:
            print(f"❌ 请求失败，状态码: {response.status_code}")
        else:
            print("✅ 请求成功")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ 请求异常: {e}")
    except Exception as e:
        print(f"❌ 其他异常: {e}")
    
    print("\n" + "=" * 60)
    print("调试完成")
    print("=" * 60)

def test_health_check():
    """测试健康检查"""
    
    url = "http://localhost:8000/health"
    
    print("\n=" * 60)
    print("测试健康检查")
    print("=" * 60)
    
    try:
        response = requests.get(url, timeout=10)
        
        print(f"HTTP状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"响应: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            if data.get('code') == 0:
                print("✅ 健康检查通过")
            else:
                print(f"❌ 健康检查失败: {data.get('message')}")
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            
    except Exception as e:
        print(f"❌ 健康检查异常: {e}")

if __name__ == "__main__":
    test_health_check()
    debug_register()