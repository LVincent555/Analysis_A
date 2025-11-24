#!/usr/bin/env python3
"""
测试 industry/trend 接口
"""
import requests
import json

# 测试接口
url = "http://localhost:8000/api/industry/trend?top_n=1000&date=20251124"

print(f"🔍 测试接口: {url}")

try:
    response = requests.get(url, timeout=10)
    print(f"📊 状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 成功!")
        print(f"   数据天数: {len(data.get('data', []))}")
        print(f"   行业数量: {len(data.get('industries', []))}")
    else:
        print(f"❌ 错误: {response.status_code}")
        print(f"   详情: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("❌ 连接失败：服务器未运行")
    print("   请先启动服务器: cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
except Exception as e:
    print(f"❌ 错误: {e}")
    import traceback
    traceback.print_exc()
