#!/usr/bin/env python3
"""快速API测试"""
import requests
import time

BASE_URL = "http://localhost:8000"

# 测试API列表
tests = [
    ("行业TOP1000", f"{BASE_URL}/api/industry/top1000?limit=1000&date=20251120"),
    ("行业加权", f"{BASE_URL}/api/industry/weighted?k=1&metric=B1&date=20251120"),
]

print("🧪 开始API测试\n")

for name, url in tests:
    print(f"测试: {name}")
    print(f"URL: {url}")
    
    # 测试3次
    times = []
    for i in range(3):
        start = time.time()
        try:
            response = requests.get(url, timeout=30)
            elapsed = time.time() - start
            
            if response.status_code == 200:
                times.append(elapsed)
                print(f"  第{i+1}次: ✅ {elapsed:.3f}秒")
            else:
                print(f"  第{i+1}次: ❌ HTTP {response.status_code}")
        except Exception as e:
            print(f"  第{i+1}次: ❌ {e}")
    
    if times:
        print(f"  平均: {sum(times)/len(times):.3f}秒")
        print(f"  最快: {min(times):.3f}秒")
        print(f"  最慢: {max(times):.3f}秒")
    print()
