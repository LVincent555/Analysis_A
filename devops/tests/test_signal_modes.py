#!/usr/bin/env python3
"""测试两种热点榜信号模式"""
import requests
import json

# 测试股票代码
stock_code = "300394"  # 天孚通信

print("🔍 测试两种热点榜信号模式\n")
print(f"测试股票: {stock_code}\n")
print("=" * 80)

# 测试模式1：总分TOP信号
print("\n1️⃣ 总分TOP信号模式（instant）")
print("-" * 80)
try:
    url = f"http://localhost:8000/api/stock/{stock_code}?hot_list_mode=instant"
    response = requests.get(url)
    response.raise_for_status()
    
    data = response.json()
    signals = data.get('signals', [])
    
    print(f"✅ 信号数量: {len(signals)}")
    print(f"📋 信号列表:")
    for signal in signals:
        print(f"   • {signal}")
    
    hot_signals = [s for s in signals if '热点榜' in s or 'TOP' in s]
    if hot_signals:
        print(f"\n🔥 热点榜信号: {hot_signals[0]}")
    else:
        print(f"\n⚠️  无热点榜信号")
        
except Exception as e:
    print(f"❌ 测试失败: {e}")

# 测试模式2：最新热点TOP信号
print("\n\n2️⃣ 最新热点TOP信号模式（frequent）")
print("-" * 80)
try:
    url = f"http://localhost:8000/api/stock/{stock_code}?hot_list_mode=frequent"
    response = requests.get(url)
    response.raise_for_status()
    
    data = response.json()
    signals = data.get('signals', [])
    
    print(f"✅ 信号数量: {len(signals)}")
    print(f"📋 信号列表:")
    for signal in signals:
        print(f"   • {signal}")
    
    hot_signals = [s for s in signals if 'TOP' in s and '·' in s]
    if hot_signals:
        print(f"\n🔥 热点榜信号: {hot_signals[0]}")
    else:
        print(f"\n⚠️  无热点榜信号")
        
except Exception as e:
    print(f"❌ 测试失败: {e}")

print("\n" + "=" * 80)
print("\n📊 对比总结:")
print("   • 总分TOP信号: 基于当日排名，格式如'热点榜TOP100'")
print("   • 最新热点TOP信号: 基于14天聚合，格式如'TOP100·5次'")
print("\n✅ 测试完成！")
