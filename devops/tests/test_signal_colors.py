#!/usr/bin/env python3
"""测试信号返回格式和颜色映射"""
import requests
import json

# 测试股票
stock_code = "300394"  # 天孚通信

print("🎨 测试信号标签和颜色映射\n")

# 测试总分TOP模式
print("1️⃣ 总分TOP模式")
print("-" * 60)
response = requests.get(f"http://localhost:8000/api/stock/{stock_code}?hot_list_mode=instant")
data = response.json()
signals = data.get('signals', [])

print(f"信号列表:")
for i, signal in enumerate(signals, 1):
    # 判断颜色
    if '热点榜' in signal or 'TOP' in signal:
        color = '绿色 🟢'
    elif '跳变' in signal:
        color = '蓝色 🔵'
    elif '稳步上升' in signal:
        color = '紫色 🟣'
    elif '涨幅' in signal:
        color = '橙色 🟠'
    elif '换手率' in signal:
        color = '红色 🔴'
    elif '波动率' in signal:
        color = '靛蓝 🟦'
    else:
        color = '灰色 ⚫'
    
    print(f"  {i}. {signal:<25} → {color}")

# 测试最新热点TOP模式
print("\n2️⃣ 最新热点TOP模式")
print("-" * 60)
response = requests.get(f"http://localhost:8000/api/stock/{stock_code}?hot_list_mode=frequent")
data = response.json()
signals = data.get('signals', [])

print(f"信号列表:")
for i, signal in enumerate(signals, 1):
    # 判断颜色
    if '热点榜' in signal or 'TOP' in signal:
        color = '绿色 🟢'
    elif '跳变' in signal:
        color = '蓝色 🔵'
    elif '稳步上升' in signal:
        color = '紫色 🟣'
    elif '涨幅' in signal:
        color = '橙色 🟠'
    elif '换手率' in signal:
        color = '红色 🔴'
    elif '波动率' in signal:
        color = '靛蓝 🟦'
    else:
        color = '灰色 ⚫'
    
    print(f"  {i}. {signal:<25} → {color}")

print("\n" + "=" * 60)
print("✅ 测试完成！")
print("\n📝 颜色映射规则:")
print("  • 热点榜/TOP → 绿色")
print("  • 跳变 → 蓝色")
print("  • 稳步上升 → 紫色")
print("  • 涨幅 → 橙色")
print("  • 换手率 → 红色")
print("  • 波动率 → 靛蓝")
