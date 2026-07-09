#!/usr/bin/env python3
"""
分析"原神启动"信号特征
核心：指标快速下杀但股价相对坚挺 + 缩量
"""
import json
import requests
from datetime import datetime

BASE_URL = "http://localhost:8000"

# 要分析的股票
STOCKS = [
    {"code": "002046", "name": "国机精工", "关键日期": "11/19前后"},
    {"code": "002279", "name": "久其软件", "关键日期": "11/14前后"},
    {"code": "000070", "name": "特发信息", "关键日期": "11/19前后"},
    {"code": "600343", "name": "航天动力", "关键日期": "11/19前后"},
]

def calculate_position_indicator(daily_data, n=5):
    """
    计算位置指标（模拟原神启动的短期线）
    = 100 * (收盘 - N天最低) / (N天最高 - N天最低)
    """
    if len(daily_data) < n:
        return None
    
    recent_n = daily_data[:n]
    
    # 获取N天内的最高和最低
    lows = [d.get('low_price', 0) for d in recent_n if d.get('low_price')]
    highs = [d.get('high_price', 0) for d in recent_n if d.get('high_price')]
    
    if not lows or not highs:
        return None
    
    llv = min(lows)
    hhv = max(highs)
    current_close = daily_data[0].get('close_price', 0)
    
    if hhv == llv:
        return 50.0  # 避免除零
    
    position = 100 * (current_close - llv) / (hhv - llv)
    return position

def analyze_stock_pattern(stock_code, stock_name):
    """分析单只股票的原神启动特征"""
    print(f"\n{'='*100}")
    print(f"分析股票: {stock_name} ({stock_code})")
    print(f"{'='*100}")
    
    # 获取数据
    try:
        response = requests.get(f"{BASE_URL}/api/stock/search", params={"q": stock_code}, timeout=10)
        if response.status_code != 200:
            print(f"❌ 查询失败")
            return
        
        data = response.json()
        if not data:
            print(f"❌ 无数据")
            return
        
        stock_data = data[0]
        daily_data = stock_data.get('daily_data', [])
        
        if not daily_data:
            print(f"❌ 无历史数据")
            return
        
        print(f"\n📊 共 {len(daily_data)} 条历史数据\n")
        
        # 分析每一天
        print(f"{'日期':<12} {'排名':<8} {'涨跌幅':<10} {'换手率':<10} {'成交量':<12} "
              f"{'波动率':<10} {'短期位置':<10} {'MACD':<10} {'RSI':<10}")
        print("-" * 110)
        
        patterns = []
        
        for i, day in enumerate(daily_data):
            date = day.get('date', 'N/A')
            rank = day.get('rank', 0)
            price_change = day.get('price_change', 0)
            turnover = day.get('turnover_rate_percent', 0)
            volume = day.get('volume', 0)
            volatility = day.get('volatility', 0)
            macd = day.get('histgram', 0)
            rsi = day.get('rsi', 0)
            
            # 计算位置指标
            position_5 = calculate_position_indicator(daily_data[i:], n=5)
            position_10 = calculate_position_indicator(daily_data[i:], n=10)
            
            print(f"{date:<12} {rank:<8} {price_change:>8.2f}% {turnover:>8.2f}% {volume:>10,} "
                  f"{volatility:>8.4f} {position_5:>8.1f}% {macd:>8.4f} {rsi:>8.2f}")
            
            # 检测原神启动信号
            if position_5 and position_10:
                # 信号1: 短期位置低（指标下杀）但涨跌幅不大（股价坚挺）
                if position_5 < 30 and abs(price_change) < 5:
                    patterns.append({
                        'date': date,
                        'signal': '指标下杀+股价坚挺',
                        'position_5': position_5,
                        'price_change': price_change,
                        'turnover': turnover,
                        'volume': volume,
                        'next_day': daily_data[i-1] if i > 0 else None
                    })
                
                # 信号2: 短期极低位 + 缩量
                if position_5 < 20 and turnover < 10:
                    patterns.append({
                        'date': date,
                        'signal': '极低位+缩量',
                        'position_5': position_5,
                        'turnover': turnover,
                        'next_day': daily_data[i-1] if i > 0 else None
                    })
        
        # 输出关键信号
        if patterns:
            print(f"\n🎯 发现 {len(patterns)} 个关键信号点：")
            print("-" * 110)
            
            for p in patterns:
                print(f"\n📅 日期: {p['date']}")
                print(f"   信号类型: {p['signal']}")
                print(f"   短期位置: {p.get('position_5', 0):.1f}%")
                print(f"   涨跌幅: {p.get('price_change', 0):.2f}%")
                print(f"   换手率: {p.get('turnover', 0):.2f}%")
                print(f"   成交量: {p.get('volume', 0):,}")
                
                next_day = p.get('next_day')
                if next_day:
                    print(f"   ➡️  次日: {next_day.get('date')} "
                          f"涨跌幅={next_day.get('price_change', 0):.2f}% "
                          f"排名={next_day.get('rank', 0)}")
        else:
            print(f"\n⚠️  未发现明显的原神启动信号")
            
    except Exception as e:
        print(f"❌ 分析失败: {e}")

def main():
    print("\n" + "="*100)
    print("原神启动信号分析工具")
    print("核心特征：指标快速下杀 + 股价相对坚挺 + 缩量")
    print("="*100)
    
    for stock in STOCKS:
        analyze_stock_pattern(stock['code'], stock['name'])
    
    print(f"\n{'='*100}")
    print("✅ 分析完成")
    print(f"{'='*100}\n")

if __name__ == "__main__":
    main()
