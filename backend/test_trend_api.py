"""测试行业趋势API"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

print("\n" + "=" * 60)
print("测试行业趋势API")
print("=" * 60 + "\n")

try:
    r = requests.get(f"{BASE_URL}/industry/trend?period=3&top_n=100", timeout=10)
    if r.status_code == 200:
        data = r.json()
        
        print(f"✅ 状态码: 200")
        print(f"📊 数据结构:")
        print(f"   - data: {len(data.get('data', []))}条日期记录")
        print(f"   - industries: {len(data.get('industries', []))}个行业")
        
        if data.get('data'):
            print(f"\n前2天的数据:")
            for i, date_data in enumerate(data['data'][:2], 1):
                print(f"\n{i}. 日期: {date_data['date']}")
                industry_counts = date_data.get('industry_counts', {})
                total = sum(industry_counts.values())
                print(f"   总股票数: {total}只")
                print(f"   行业数量: {len(industry_counts)}个")
                
                # 显示前5个行业
                sorted_industries = sorted(industry_counts.items(), key=lambda x: x[1], reverse=True)
                print(f"   前5个行业:")
                for industry, count in sorted_industries[:5]:
                    print(f"      {industry}: {count}只")
        
        print(f"\n✅ API返回数据结构正确！")
    else:
        print(f"❌ 状态码: {r.status_code}")
        print(f"错误: {r.text}")
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "=" * 60)
