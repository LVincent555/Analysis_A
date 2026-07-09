#!/usr/bin/env python3
"""详细测试春秋电子的信号计算"""
import sys
import os

# 添加backend目录到路径
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_dir)

from datetime import datetime
from app.services.signal_calculator import SignalCalculator, SignalThresholds
from app.services.memory_cache import memory_cache
from app.services.hot_spots_cache import HotSpotsCache
from app.database import SessionLocal

print("=" * 60)
print("初始化数据")
print("=" * 60)

# 加载内存缓存
if not memory_cache.is_loaded():
    print("加载内存缓存...")
    memory_cache.load_all_data()
    print(f"✅ 已加载 {len(memory_cache.stocks)} 只股票")

# 加载热点榜缓存
print("加载热点榜缓存...")
HotSpotsCache.load_all()
print("✅ 热点榜缓存已加载")

print("\n" + "=" * 60)
print("测试春秋电子 (603890) 的信号计算")
print("=" * 60)

stock_code = '603890'
latest_date = memory_cache.get_latest_date()
date_str = latest_date.strftime('%Y%m%d')

print(f"日期: {date_str}")

# 获取股票当日数据
current_data = memory_cache.get_daily_data_by_stock(stock_code, latest_date)
if not current_data:
    print(f"❌ 未找到股票数据")
    sys.exit(1)

print(f"排名: {current_data.rank}")
print(f"涨跌幅: {current_data.price_change}%")
print(f"换手率: {current_data.turnover_rate_percent}%")

# 查询热点榜数据
print("\n" + "=" * 60)
print("热点榜数据")
print("=" * 60)

result = HotSpotsCache.get_rank(stock_code, date_str)
if result:
    rank, hit_count, tier_counts = result
    print(f"排名: {rank}")
    print(f"总出现次数: {hit_count}")
    print(f"各档位统计: {tier_counts}")
else:
    print("❌ 不在热点榜中")

# 测试信号计算
print("\n" + "=" * 60)
print("信号计算（frequent模式）")
print("=" * 60)

thresholds = SignalThresholds(hot_list_mode="frequent", hot_list_version="v2")
calculator = SignalCalculator(thresholds)

# 计算信号
signals_data = calculator.calculate_signals(
    stock_code=stock_code,
    current_date=latest_date,
    current_data=current_data,
    history_days=7
)

print(f"信号列表: {signals_data['signals']}")
print(f"信号数量: {signals_data['signal_count']}")
print(f"信号强度: {signals_data['signal_strength']:.3f}")
print(f"在热点榜: {signals_data['in_hot_list']}")
print(f"在跳变榜: {signals_data['in_rank_jump']}")
print(f"在稳步上升: {signals_data['in_steady_rise']}")
print(f"在涨幅榜: {signals_data['in_price_surge']}")
print(f"在成交量榜: {signals_data['in_volume_surge']}")

# 单独测试热点信号计算
print("\n" + "=" * 60)
print("单独测试热点信号计算")
print("=" * 60)

hot_signal = calculator.calculate_hot_spot_signal(stock_code, date_str)
if hot_signal:
    print(f"✅ 热点信号:")
    print(f"   标签: {hot_signal['label']}")
    print(f"   分数: {hot_signal['score']:.4f}")
    print(f"   排名: {hot_signal['rank']}")
    print(f"   出现次数: {hot_signal['hit_count']}")
    print(f"   主档位: {hot_signal['main_tier']}")
    print(f"   档位统计: {hot_signal['tier_counts']}")
else:
    print("❌ 无热点信号")

print("\n" + "=" * 60)
