"""测试只统计最新一天的修复"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

print("\n" + "=" * 60)
print("测试：只统计最新一天的数据")
print("=" * 60 + "\n")

# 测试热点分析
print("1️⃣  测试热点分析（周期=2天）")
try:
    r = requests.get(f"{BASE_URL}/analyze/2?filter_stocks=true", timeout=10)
    if r.status_code == 200:
        data = r.json()
        
        print(f"   ✅ 状态码: 200")
        print(f"   📅 日期: {data['start_date']}")
        print(f"   📊 总股票数: {data['total_stocks']}只")
        print(f"   🔢 all_dates: {data['all_dates']}")
        
        print("\n   前5只股票：")
        for i, stock in enumerate(data['stocks'][:5], 1):
            print(f"   {i}. {stock['code']} - {stock['name']}")
            print(f"      排名: 第{stock['rank']}名")
            print(f"      出现次数: {stock['count']}次")
            if stock.get('date_rank_info'):
                for info in stock['date_rank_info']:
                    print(f"      {info['date']}(第{info['rank']}名)")
        
        print("\n   ✅ 验证：所有股票的count都应该是1")
        all_count_1 = all(s['count'] == 1 for s in data['stocks'])
        print(f"   结果: {all_count_1}")
        
    else:
        print(f"   ❌ 状态码: {r.status_code}")
        print(f"   错误: {r.text}")
except Exception as e:
    print(f"   ❌ 错误: {e}")

print("\n" + "=" * 60)
print("✅ 测试完成")
print("=" * 60 + "\n")
