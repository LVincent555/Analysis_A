"""测试API返回的数据结构"""
import requests
import json

BASE_URL = "http://127.0.0.1:8000/api"

print("\n" + "=" * 60)
print("测试API返回的数据结构")
print("=" * 60 + "\n")

try:
    r = requests.get(f"{BASE_URL}/analyze/2?filter_stocks=true", timeout=10)
    if r.status_code == 200:
        data = r.json()
        
        print(f"✅ 状态码: 200")
        print(f"📊 总股票数: {data.get('total_stocks')}只")
        print(f"📅 日期范围: {data.get('start_date')} ~ {data.get('end_date')}")
        
        # 检查行业分布
        stocks = data.get('stocks', [])
        if stocks:
            print(f"\n行业分布统计:")
            industry_count = {}
            for stock in stocks:
                industry = stock.get('industry', '未知')
                industry_count[industry] = industry_count.get(industry, 0) + 1
            
            for industry, count in sorted(industry_count.items(), key=lambda x: x[1], reverse=True):
                print(f"  {industry}: {count}只")
            
            print(f"\n前3只股票详情:")
            for i, stock in enumerate(stocks[:3], 1):
                print(f"\n{i}. {stock['code']} - {stock['name']}")
                print(f"   行业: {stock.get('industry', '未知')}")
                print(f"   排名: 第{stock.get('rank')}名")
                print(f"   出现次数: {stock.get('count')}次")
                if stock.get('date_rank_info'):
                    print(f"   历史数据: {len(stock['date_rank_info'])}条")
        else:
            print("❌ 没有股票数据")
    else:
        print(f"❌ 状态码: {r.status_code}")
        print(f"错误: {r.text}")
except Exception as e:
    print(f"❌ 错误: {e}")

print("\n" + "=" * 60)
