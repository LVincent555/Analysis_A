#!/usr/bin/env python3
"""
测试 91HTTP 代理 IP 的实际可用请求次数
"""
import requests
import time

# 91HTTP 配置
PROXY_API = "http://api.91http.com/v1/get-ip"
TRADE_NO = "B200987778609"
SECRET = "7GJdQkL6G93PcR9o"

# 东财测试接口
TEST_URL = "https://push2.eastmoney.com/api/qt/clist/get"
TEST_PARAMS = {'pn': '1', 'pz': '5', 'fs': 'b:BK0475', 'fields': 'f12,f14'}
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Connection": "close"
}

def get_proxy():
    """获取一个代理 IP"""
    params = {
        'trade_no': TRADE_NO,
        'secret': SECRET,
        'num': 1,
        'protocol': 1,
        'format': 'text',
        'sep': 1,
        'filter': 1,
        'auto_white': 1
    }
    r = requests.get(PROXY_API, params=params, timeout=10)
    return r.text.strip()

def test_proxy_limit():
    """测试单个代理 IP 的请求次数限制"""
    print("=" * 50)
    print("91HTTP 代理 IP 请求次数测试")
    print("=" * 50)
    
    # 获取代理
    proxy_ip = get_proxy()
    print(f"\n代理 IP: {proxy_ip}")
    print(f"开始时间: {time.strftime('%H:%M:%S')}")
    print("-" * 50)
    
    proxies = {
        'http': f'http://{proxy_ip}',
        'https': f'http://{proxy_ip}'
    }
    
    success_count = 0
    fail_count = 0
    start_time = time.time()
    
    # 持续请求直到失败
    while True:
        try:
            r = requests.get(TEST_URL, params=TEST_PARAMS, headers=HEADERS, 
                           proxies=proxies, timeout=15)
            data = r.json()
            diff = data.get('data', {}).get('diff', [])
            
            if diff:
                success_count += 1
                elapsed = time.time() - start_time
                print(f"[{success_count:3d}] 成功 - 返回 {len(diff)} 条 - 耗时 {elapsed:.1f}s")
            else:
                fail_count += 1
                print(f"[{success_count:3d}] 空数据")
                if fail_count >= 3:
                    print("连续空数据，停止测试")
                    break
            
            # 间隔 0.5 秒
            time.sleep(0.5)
            
        except Exception as e:
            fail_count += 1
            elapsed = time.time() - start_time
            print(f"[{success_count:3d}] 失败 - {type(e).__name__}: {str(e)[:50]} - 耗时 {elapsed:.1f}s")
            
            if fail_count >= 3:
                print("连续失败，停止测试")
                break
            
            time.sleep(1)
    
    # 统计
    total_time = time.time() - start_time
    print("-" * 50)
    print(f"测试结果:")
    print(f"  成功请求: {success_count} 次")
    print(f"  失败请求: {fail_count} 次")
    print(f"  总耗时: {total_time:.1f} 秒")
    print(f"  平均速度: {success_count / total_time * 60:.1f} 次/分钟")
    print("=" * 50)
    
    return success_count

if __name__ == '__main__':
    test_proxy_limit()
