"""通过API查询行业名称"""
import requests
import json

# 调用API
url = "http://localhost:8000/api/industry/top1000?limit=1000"
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    stats = data.get('stats', [])
    
    print(f"找到 {len(stats)} 个行业\n")
    
    print("前20个行业：")
    for i, stat in enumerate(stats[:20]):
        print(f"  {i+1}. {stat['industry']}: {stat['count']}只")
    
    # 查找包含"通"的行业
    print("\n\n包含'通'字的行业：")
    found_tong = []
    for stat in stats:
        if '通' in stat['industry']:
            found_tong.append(stat)
            print(f"  - {stat['industry']}: {stat['count']}只")
    
    if not found_tong:
        print("  （没有找到）")
    
    # 精确查找
    print("\n\n精确匹配：")
    found_exact = False
    for stat in stats:
        if stat['industry'] == '通信设备':
            print(f"  ✅ '通信设备' 存在，有 {stat['count']} 只股票")
            found_exact = True
            break
    
    if not found_exact:
        # 看看是不是"通讯设备"
        for stat in stats:
            if stat['industry'] == '通讯设备':
                print(f"  ⚠️  数据库中是'通讯设备'（讯），有 {stat['count']} 只股票")
                found_exact = True
                break
    
    if not found_exact:
        print(f"  ❌ '通信设备'或'通讯设备' 都不存在")
        print(f"\n  建议：从加权分析图表中点击的行业名称是：")
        # 查找最接近的
        for stat in stats:
            if '通' in stat['industry'] or '信' in stat['industry']:
                print(f"    - {stat['industry']}")
    
else:
    print(f"API调用失败：{response.status_code}")
