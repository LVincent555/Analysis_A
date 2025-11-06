"""
测试修复后的API
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

print("\n" + "=" * 60)
print("测试修复后的API")
print("=" * 60 + "\n")

# 1. 测试热点分析 - 最新排名
print("1️⃣  测试热点分析 - 最新排名锚定")
try:
    r = requests.get(f"{BASE_URL}/analyze/3", timeout=10)
    if r.status_code == 200:
        data = r.json()
        stocks = data.get('stocks', [])
        if stocks:
            first = stocks[0]
            print(f"   ✅ 第一只股票: {first.get('code')} - {first.get('name')}")
            print(f"   ✅ 最新排名: {first.get('rank')} (应该有值)")
            print(f"   ✅ 出现次数: {first.get('count')}次")
            date_rank_info = first.get('date_rank_info', [])
            if date_rank_info:
                print(f"   ✅ 最新日期: {date_rank_info[0].get('date')}")
                print(f"   ✅ 日期排序: {[d.get('date') for d in date_rank_info[:3]]}")
    else:
        print(f"   ❌ 状态码: {r.status_code}")
except Exception as e:
    print(f"   ❌ 错误: {e}")

# 2. 测试排名跳变 - 连字符路径
print("\n2️⃣  测试排名跳变 - 连字符路径 /api/rank-jump")
try:
    r = requests.get(f"{BASE_URL}/rank-jump?jump_threshold=2000&sigma_multiplier=0.15", timeout=10)
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ 状态码: {r.status_code}")
        print(f"   ✅ 跳变股票: {data.get('total_count')}只")
        print(f"   ✅ σ范围内股票: {len(data.get('sigma_stocks', []))}只")
    else:
        print(f"   ❌ 状态码: {r.status_code}, 响应: {r.text[:200]}")
except Exception as e:
    print(f"   ❌ 错误: {e}")

# 3. 测试行业趋势 - /industry/trend
print("\n3️⃣  测试行业趋势 - /api/industry/trend")
try:
    r = requests.get(f"{BASE_URL}/industry/trend", timeout=10)
    if r.status_code == 200:
        data = r.json()
        print(f"   ✅ 状态码: {r.status_code}")
        print(f"   ✅ 行业数: {len(data) if isinstance(data, list) else 0}")
        if isinstance(data, list) and data:
            print(f"   ✅ TOP3行业: {[d.get('industry') for d in data[:3]]}")
    else:
        print(f"   ❌ 状态码: {r.status_code}")
except Exception as e:
    print(f"   ❌ 错误: {e}")

print("\n" + "=" * 60)
print("✅ 测试完成")
print("=" * 60 + "\n")
