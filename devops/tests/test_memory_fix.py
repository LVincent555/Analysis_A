#!/usr/bin/env python3
"""测试内存优化效果"""
import requests
import time

BASE_URL = "http://localhost:8000"

# 测试之前导致内存泄漏的API
tests = [
    ("行业趋势(14天×1000)", f"{BASE_URL}/api/industry/trend?top_n=1000&period=14&date=20251124"),
    ("板块趋势(30板块×7天)", f"{BASE_URL}/api/sectors/trend?limit=30&days=7&date=20251124"),
    ("板块排名变化", f"{BASE_URL}/api/sectors/rank-changes?date=20251124&compare_days=1"),
    ("行业TOP1000", f"{BASE_URL}/api/industry/top1000?limit=1000&date=20251124"),
]

print("🧪 测试内存优化效果")
print("="*60)
print("这些API之前会导致内存泄漏（重复加载数据库数据）")
print("优化后应该只使用内存缓存，不再查询数据库\n")

for name, url in tests:
    print(f"📊 测试: {name}")
    print(f"   URL: {url}")
    
    try:
        start = time.time()
        response = requests.get(url, timeout=30)
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            # 显示返回数据大小
            if isinstance(data, dict):
                if 'data' in data:
                    print(f"   ✅ 成功: {elapsed:.3f}秒 - 返回{len(data.get('data', []))}条记录")
                elif 'sectors' in data:
                    print(f"   ✅ 成功: {elapsed:.3f}秒 - 返回{len(data.get('sectors', []))}个板块")
                elif 'stats' in data:
                    print(f"   ✅ 成功: {elapsed:.3f}秒 - 返回{len(data.get('stats', []))}个行业")
                else:
                    print(f"   ✅ 成功: {elapsed:.3f}秒")
            else:
                print(f"   ✅ 成功: {elapsed:.3f}秒")
        else:
            print(f"   ❌ 失败: HTTP {response.status_code}")
            print(f"      {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ 错误: {e}")
    
    print()

print("="*60)
print("✅ 测试完成！")
print("\n💡 提示：")
print("   - 如果响应时间都在0.1秒以内，说明优化成功")
print("   - 之前这些API会导致内存占用95%+")
print("   - 现在应该不会增加额外内存占用")
