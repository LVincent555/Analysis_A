"""快速测试修复后的API"""
import requests
import time

print("等待服务启动...")
time.sleep(2)

print("\n测试 /api/industry/通信设备/stocks API:")
url = "http://localhost:8000/api/industry/通信设备/stocks?sort_mode=signal"
print(f"URL: {url}")

try:
    print("发送请求...")
    response = requests.get(url, timeout=10)
    print(f"✅ 状态码: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ 成功！股票数量: {data.get('stock_count')}")
        if data.get('stocks'):
            print(f"前5只股票:")
            for i, stock in enumerate(data['stocks'][:5], 1):
                print(f"  {i}. {stock['stock_name']} ({stock['stock_code']}) - 信号: {stock.get('signal_count', 0)}个")
    else:
        print(f"❌ 失败！")
        print(f"响应: {response.text[:500]}")
        
except requests.exceptions.Timeout:
    print("❌ 请求超时（10秒）- 服务可能卡住了")
except requests.exceptions.ConnectionError:
    print("❌ 连接失败 - 服务可能没有运行")
except Exception as e:
    print(f"❌ 错误: {e}")
