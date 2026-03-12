#!/usr/bin/env python3
"""
精准测试东财板块列表 API - 对比同步脚本使用的参数
"""
import requests
import time

# 91HTTP 配置
PROXY_API = "http://api.91http.com/v1/get-ip"
TRADE_NO = "B200987778609"
SECRET = "7GJdQkL6G93PcR9o"

# 东财接口
BASE_URL = "https://push2.eastmoney.com/api/qt/clist/get"

# 同步脚本使用的请求头
SYNC_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/center/gridlist.html",
    "Accept": "*/*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "close",
}

# 简化请求头
SIMPLE_HEADERS = {
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
    ip = r.text.strip()
    print(f"获取代理IP: {ip}")
    return {'http': f'http://{ip}', 'https': f'http://{ip}'}


def test_board_list(proxies, headers, name):
    """测试板块列表接口（同步脚本第一步）"""
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"{'='*60}")
    
    # 行业板块参数 - 来自同步脚本
    params = {
        "pn": "1",
        "pz": "100",
        "po": "1",
        "np": "1",
        "ut": "bd1d9ddb04089700cf9c27f6f7426281",
        "fltt": "2",
        "invt": "2",
        "fid": "f3",
        "fs": "m:90+t:2+f:!50",  # 行业板块
        "fields": "f12,f14,f3"
    }
    
    try:
        with requests.Session() as s:
            s.trust_env = False
            r = s.get(BASE_URL, params=params, headers=headers, 
                     proxies=proxies, timeout=15)
            print(f"状态码: {r.status_code}")
            
            data = r.json()
            diff = data.get("data", {}).get("diff") or []
            total = data.get("data", {}).get("total", 0)
            
            print(f"✅ 成功! 返回 {len(diff)}/{total} 个板块")
            if diff:
                print(f"   示例: {diff[0]}")
            return True
            
    except Exception as e:
        print(f"❌ 失败: {type(e).__name__}: {str(e)[:100]}")
        return False


def test_board_cons(proxies, headers, name):
    """测试板块成分股接口（与test_proxy.py相同）"""
    print(f"\n{'='*60}")
    print(f"测试: {name}")
    print(f"{'='*60}")
    
    # 成分股参数 - 来自test_proxy.py
    params = {
        'pn': '1', 
        'pz': '5', 
        'fs': 'b:BK0475',  # 某个板块的成分股
        'fields': 'f12,f14'
    }
    
    try:
        r = requests.get(BASE_URL, params=params, headers=headers, 
                        proxies=proxies, timeout=15)
        print(f"状态码: {r.status_code}")
        
        data = r.json()
        diff = data.get('data', {}).get('diff', [])
        
        print(f"✅ 成功! 返回 {len(diff)} 条成分股")
        if diff:
            print(f"   示例: {diff[0]}")
        return True
        
    except Exception as e:
        print(f"❌ 失败: {type(e).__name__}: {str(e)[:100]}")
        return False


def main():
    print("="*60)
    print("东财 API 连通性测试")
    print("="*60)
    
    # 测试1: 用简化请求头测试成分股（应该成功，与test_proxy.py一致）
    print("\n>>> 获取代理 IP #1")
    proxies1 = get_proxy()
    time.sleep(2)
    test_board_cons(proxies1, SIMPLE_HEADERS, "简化Header + 成分股接口 (baseline)")
    
    # 测试2: 用简化请求头测试板块列表
    print("\n>>> 获取代理 IP #2")
    time.sleep(2)
    proxies2 = get_proxy()
    time.sleep(2)
    test_board_list(proxies2, SIMPLE_HEADERS, "简化Header + 板块列表接口")
    
    # 测试3: 用同步脚本的请求头测试板块列表
    print("\n>>> 获取代理 IP #3")
    time.sleep(2)
    proxies3 = get_proxy()
    time.sleep(2)
    test_board_list(proxies3, SYNC_HEADERS, "同步脚本Header + 板块列表接口")
    
    # 测试4: 用同步脚本的请求头测试成分股
    print("\n>>> 获取代理 IP #4")
    time.sleep(2)
    proxies4 = get_proxy()
    time.sleep(2)
    test_board_cons(proxies4, SYNC_HEADERS, "同步脚本Header + 成分股接口")
    
    print("\n" + "="*60)
    print("测试完成！")
    print("="*60)


if __name__ == '__main__':
    main()
