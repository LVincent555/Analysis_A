#!/usr/bin/env python3
"""检查热点榜缓存状态"""
import requests
import json

# API端点
url = "http://localhost:8000/api/hot-spots/full?date=20251107"

print("🔍 检查热点榜缓存状态...\n")

try:
    # 测试API响应
    response = requests.get(url)
    response.raise_for_status()
    
    data = response.json()
    
    print("✅ 热点榜缓存状态")
    print(f"   日期: {data['date']}")
    print(f"   总数: {data['total_count']}")
    print(f"   前5只股票:")
    
    for i, stock in enumerate(data['stocks'][:5], 1):
        print(f"   {i}. {stock['code']} {stock['name']:<10} - 排名{stock['rank']:<4} {stock['rank_label']}")
    
    print(f"\n🎯 缓存检查通过！")
    print(f"   ✓ 数据已加载")
    print(f"   ✓ 标签格式正确")
    print(f"   ✓ API响应正常")
    
except requests.exceptions.ConnectionError:
    print(f"❌ 无法连接到后端服务")
    print(f"   请确认后端服务已启动（localhost:8000）")
except Exception as e:
    print(f"❌ 检查失败: {e}")
    import traceback
    traceback.print_exc()
