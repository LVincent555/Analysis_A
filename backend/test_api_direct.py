"""直接测试通信设备API"""
import requests
import urllib.parse

industry_name = "通信设备"

# URL编码
encoded = urllib.parse.quote(industry_name)
print(f"行业名称: {industry_name}")
print(f"URL编码: {encoded}")

# 测试detail API
print("\n\n测试 detail API:")
url1 = f"http://localhost:8000/api/industry/{encoded}/detail"
print(f"URL: {url1}")
response1 = requests.get(url1)
print(f"状态码: {response1.status_code}")
if response1.status_code == 200:
    data = response1.json()
    print(f"成功！股票数量: {data.get('stock_count')}")
else:
    print(f"失败！响应: {response1.text}")

# 测试stocks API
print("\n\n测试 stocks API:")
url2 = f"http://localhost:8000/api/industry/{encoded}/stocks?sort_mode=signal"
print(f"URL: {url2}")
response2 = requests.get(url2)
print(f"状态码: {response2.status_code}")
if response2.status_code == 200:
    data = response2.json()
    print(f"成功！股票数量: {data.get('stock_count')}")
    if data.get('stocks'):
        print(f"前3只股票:")
        for stock in data['stocks'][:3]:
            print(f"  - {stock['stock_name']} ({stock['stock_code']})")
else:
    print(f"失败！响应: {response2.text}")
