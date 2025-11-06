"""
最终测试脚本 - 验证所有修复
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

print("\n" + "=" * 60)
print("最终修复验证测试")
print("=" * 60 + "\n")

# 1. 测试排名跳变（只有向前跳）
print("1️⃣  测试排名跳变 - 验证没有负值")
try:
    r = requests.get(f"{BASE_URL}/rank-jump?jump_threshold=2000", timeout=10)
    if r.status_code == 200:
        data = r.json()
        stocks = data.get('stocks', [])
        has_negative = any(s.get('rank_change', 0) < 0 for s in stocks)
        has_indicators = stocks[0].get('price_change') is not None if stocks else False
        
        print(f"   ✅ 状态码: 200")
        print(f"   ✅ 总股票数: {len(stocks)}只")
        print(f"   ✅ 没有负值: {not has_negative}")
        print(f"   ✅ 技术指标: {has_indicators}")
        
        if stocks:
            first = stocks[0]
            print(f"   示例: {first.get('code')} - {first.get('name')}")
            print(f"         排名跳变: +{first.get('rank_change')}")
            print(f"         涨跌幅: {first.get('price_change')}%")
            print(f"         换手率: {first.get('turnover_rate')}%")
    else:
        print(f"   ❌ 状态码: {r.status_code}")
except Exception as e:
    print(f"   ❌ 错误: {e}")

# 2. 测试行业top1000（验证数据结构）
print("\n2️⃣  测试行业TOP1000 - 验证数据结构")
try:
    r = requests.get(f"{BASE_URL}/industry/top1000", timeout=10)
    if r.status_code == 200:
        data = r.json()
        has_date = 'date' in data
        has_stats = 'stats' in data
        has_total = 'total_stocks' in data
        
        print(f"   ✅ 状态码: 200")
        print(f"   ✅ 包含date字段: {has_date}")
        print(f"   ✅ 包含stats字段: {has_stats}")
        print(f"   ✅ 包含total_stocks字段: {has_total}")
        
        if has_date and has_stats:
            print(f"   日期: {data.get('date')}")
            print(f"   总股票数: {data.get('total_stocks')}")
            print(f"   行业数: {len(data.get('stats', []))}")
            
            if data.get('stats'):
                first_stat = data['stats'][0]
                print(f"   TOP1行业: {first_stat.get('industry')} - {first_stat.get('count')}只 ({first_stat.get('percentage')}%)")
    else:
        print(f"   ❌ 状态码: {r.status_code}")
except Exception as e:
    print(f"   ❌ 错误: {e}")

# 3. 测试热点分析（验证过滤1次）
print("\n3️⃣  测试热点分析 - 验证过滤1次出现")
try:
    r = requests.get(f"{BASE_URL}/analyze/3", timeout=10)
    if r.status_code == 200:
        data = r.json()
        stocks = data.get('stocks', [])
        has_single = any(s.get('count', 0) == 1 for s in stocks)
        
        print(f"   ✅ 状态码: 200")
        print(f"   ✅ 总股票数: {len(stocks)}只")
        print(f"   ✅ 没有1次股票: {not has_single}")
        
        if stocks:
            min_count = min(s.get('count', 0) for s in stocks)
            max_count = max(s.get('count', 0) for s in stocks)
            print(f"   最少出现次数: {min_count}次")
            print(f"   最多出现次数: {max_count}次")
    else:
        print(f"   ❌ 状态码: {r.status_code}")
except Exception as e:
    print(f"   ❌ 错误: {e}")

print("\n" + "=" * 60)
print("✅ 测试完成")
print("=" * 60 + "\n")
