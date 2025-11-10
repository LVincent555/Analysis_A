#!/usr/bin/env python3
"""测试股票查询API的信号数据"""
import requests
import json

# 测试API
stock_codes = ["300394", "920961"]  # 天孚通信、创远信科

for stock_code in stock_codes:
    url = f"http://localhost:8000/api/stock/{stock_code}"
    print(f"\n🔍 测试股票: {stock_code}")
    print(f"   URL: {url}\n")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        
        print(f"✅ API响应成功！")
        print(f"   代码: {data['code']}")
        print(f"   名称: {data['name']}")
        print(f"   行业: {data['industry']}")
        print(f"   信号数量: {len(data.get('signals', []))}")
        
        if data.get('signals'):
            print(f"\n🏷️  信号列表:")
            for signal in data['signals']:
                print(f"   • {signal}")
        else:
            print(f"\n   ⚠️  无信号数据")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

print(f"\n✅ 测试完成！")
