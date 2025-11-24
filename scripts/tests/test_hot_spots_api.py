#!/usr/bin/env python3
"""测试热点榜API"""
import requests
import json

# 测试API
url = "http://localhost:8000/api/hot-spots/full?date=20251107"
print(f"🔍 测试API: {url}\n")

try:
    response = requests.get(url)
    response.raise_for_status()
    
    data = response.json()
    
    print(f"✅ API响应成功！")
    print(f"   日期: {data['date']}")
    print(f"   总数: {data['total_count']}")
    print(f"\n📊 前10只股票:")
    print(f"{'排名':<6}{'代码':<10}{'名称':<15}{'标签':<20}{'次数'}")
    print("-" * 80)
    
    for i, stock in enumerate(data['stocks'][:10], 1):
        print(f"{i:<6}{stock['code']:<10}{stock['name']:<15}{stock['rank_label']:<20}{stock['hit_count']}")
    
    print(f"\n🎯 测试通过！")
    
    # 验证标签格式
    print(f"\n🏷️  标签格式测试:")
    for stock in data['stocks'][:5]:
        label = stock['rank_label']
        rank = stock['rank']
        count = stock['hit_count']
        print(f"   排名{rank}: {label} (出现{count}次)")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
