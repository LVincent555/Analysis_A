"""
快速测试API端点
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

print("\n" + "=" * 60)
print("测试所有API端点")
print("=" * 60 + "\n")

# 1. 测试获取日期
print("1️⃣  测试 GET /api/dates")
try:
    r = requests.get(f"{BASE_URL}/dates", timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ 状态码: {r.status_code}")
        print(f"   ✅ 日期数: {len(data.get('dates', []))}")
    else:
        print(f"   ❌ 状态码: {r.status_code}")
except Exception as e:
    print(f"   ❌ 错误: {e}")

# 2. 测试热点分析
print("\n2️⃣  测试 GET /api/analyze/3")
try:
    r = requests.get(f"{BASE_URL}/analyze/3", timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ 状态码: {r.status_code}")
        print(f"   ✅ 股票数: {data.get('total_stocks', 0)}")
    else:
        print(f"   ❌ 状态码: {r.status_code}")
except Exception as e:
    print(f"   ❌ 错误: {e}")

# 3. 测试股票查询
print("\n3️⃣  测试 GET /api/stock/000001")
try:
    r = requests.get(f"{BASE_URL}/stock/000001", timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ 状态码: {r.status_code}")
        print(f"   ✅ 股票: {data.get('code')} - {data.get('name')}")
        print(f"   ✅ 历史数据: {data.get('appears_count')}天")
    else:
        print(f"   ❌ 状态码: {r.status_code}, 响应: {r.text[:100]}")
except Exception as e:
    print(f"   ❌ 错误: {e}")

# 4. 测试排名跳变
print("\n4️⃣  测试 GET /api/rank_jump")
try:
    r = requests.get(f"{BASE_URL}/rank_jump?jump_threshold=2500", timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ 状态码: {r.status_code}")
        print(f"   ✅ 跳变股票: {data.get('total_count', 0)}只")
    else:
        print(f"   ❌ 状态码: {r.status_code}")
except Exception as e:
    print(f"   ❌ 错误: {e}")

# 5. 测试稳步上升
print("\n5️⃣  测试 GET /api/steady-rise")
try:
    r = requests.get(f"{BASE_URL}/steady-rise?period=3", timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ 状态码: {r.status_code}")
        print(f"   ✅ 上升股票: {data.get('total_count', 0)}只")
    else:
        print(f"   ❌ 状态码: {r.status_code}")
except Exception as e:
    print(f"   ❌ 错误: {e}")

# 6. 测试行业统计
print("\n6️⃣  测试 GET /api/industry/stats")
try:
    r = requests.get(f"{BASE_URL}/industry/stats?period=3", timeout=5)
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ 状态码: {r.status_code}")
        print(f"   ✅ 行业数: {len(data) if isinstance(data, list) else 0}")
    else:
        print(f"   ❌ 状态码: {r.status_code}")
except Exception as e:
    print(f"   ❌ 错误: {e}")

print("\n" + "=" * 60)
print("✅ API测试完成")
print("=" * 60 + "\n")
