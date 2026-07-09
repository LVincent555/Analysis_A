#!/usr/bin/env python3
"""测试信号和板块名称"""
import requests
import json

BASE_URL = "http://localhost:8000"

print("=" * 60)
print("测试1: 查询春秋电子的信号")
print("=" * 60)
try:
    response = requests.get(f"{BASE_URL}/api/stock/603890", timeout=10)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 状态码: {response.status_code}")
        print(f"📊 信号列表: {data.get('signals', [])}")
        print(f"📈 信号数量: {len(data.get('signals', []))}")
    else:
        print(f"❌ 状态码: {response.status_code}")
        print(f"错误: {response.text}")
except Exception as e:
    print(f"❌ 请求失败: {e}")

print("\n" + "=" * 60)
print("测试2: 查询板块数据（dc板块）")
print("=" * 60)
try:
    response = requests.get(f"{BASE_URL}/api/sectors/trend?limit=10", timeout=10)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 状态码: {response.status_code}")
        sectors = data.get('sectors', [])
        print(f"📊 板块数量: {len(sectors)}")
        print("\n前10个板块:")
        for i, sector in enumerate(sectors[:10], 1):
            print(f"  {i}. 名称: {sector.get('name')}")
    else:
        print(f"❌ 状态码: {response.status_code}")
        print(f"错误: {response.text}")
except Exception as e:
    print(f"❌ 请求失败: {e}")

print("\n" + "=" * 60)
print("测试3: 检查春秋电子在热点榜中的排名")
print("=" * 60)
try:
    # 查询最新热点榜 - 使用正确的路径
    response = requests.get(f"{BASE_URL}/api/analyze/2?top_n=3000&board_type=main", timeout=30)
    if response.status_code == 200:
        data = response.json()
        stocks = data.get('stocks', [])
        print(f"✅ 热点榜总数: {len(stocks)}")
        
        # 查找春秋电子
        found = False
        for stock in stocks:
            if stock.get('code') == '603890':
                found = True
                print(f"\n找到春秋电子:")
                print(f"  代码: {stock.get('code')}")
                print(f"  名称: {stock.get('name')}")
                print(f"  排名: {stock.get('rank')}")
                print(f"  出现次数: {stock.get('count')}")
                break
        
        if not found:
            print(f"\n❌ 春秋电子不在热点榜TOP3000中")
            print(f"\n显示前10个股票:")
            for i, stock in enumerate(stocks[:10], 1):
                print(f"  {i}. {stock.get('code')} {stock.get('name')} - 排名:{stock.get('rank')} 次数:{stock.get('count')}")
    else:
        print(f"❌ 状态码: {response.status_code}")
        print(f"错误: {response.text}")
except Exception as e:
    print(f"❌ 请求失败: {e}")

print("\n" + "=" * 60)
print("测试4: 查询春秋电子的当日排名")
print("=" * 60)
try:
    # 先获取最新日期
    response = requests.get(f"{BASE_URL}/api/dates", timeout=10)
    if response.status_code == 200:
        dates_data = response.json()
        latest_date = dates_data.get('latest_date')
        print(f"✅ 最新日期: {latest_date}")
        
        # 查询春秋电子在当日的排名
        from datetime import datetime
        date_obj = datetime.strptime(latest_date, '%Y%m%d')
        
        # 从热点榜缓存查询
        response2 = requests.get(f"{BASE_URL}/api/hot-spots/full?date={latest_date}", timeout=10)
        if response2.status_code == 200:
            hot_data = response2.json()
            stocks = hot_data.get('stocks', [])
            print(f"✅ 热点榜总数: {len(stocks)}")
            
            found = False
            for stock in stocks:
                if stock.get('code') == '603890':
                    found = True
                    print(f"\n找到春秋电子在 {latest_date} 的数据:")
                    print(f"  排名: {stock.get('rank')}")
                    print(f"  排名标签: {stock.get('rank_label')}")
                    print(f"  14天出现次数: {stock.get('hit_count')}")
                    break
            
            if not found:
                print(f"\n❌ 春秋电子不在当日热点榜中")
        else:
            print(f"❌ 查询热点榜失败: {response2.status_code}")
    else:
        print(f"❌ 获取日期失败: {response.status_code}")
except Exception as e:
    print(f"❌ 请求失败: {e}")

print("\n" + "=" * 60)
