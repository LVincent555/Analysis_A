#!/usr/bin/env python3
"""测试Numpy优化效果"""
import sys
import os
import time

# 添加backend目录到路径
backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
sys.path.insert(0, backend_dir)

from app.services.memory_cache import memory_cache
from app.services.numpy_cache import numpy_stock_cache

print("=" * 60)
print("Numpy优化效果测试")
print("=" * 60)

# 加载数据
if not memory_cache.is_loaded():
    print("\n加载内存缓存...")
    start_time = time.time()
    memory_cache.load_all_data()
    load_time = time.time() - start_time
    print(f"✅ 加载完成，耗时: {load_time:.2f}秒")

# 获取内存使用情况
print("\n" + "=" * 60)
print("内存占用对比")
print("=" * 60)

numpy_usage = numpy_stock_cache.get_memory_usage()
print(f"\n📊 Numpy缓存:")
print(f"  数组内存: {numpy_usage['array_mb']:.2f} MB")
print(f"  索引内存: {numpy_usage['dict_mb']:.2f} MB")
print(f"  总计: {numpy_usage['total_mb']:.2f} MB")
print(f"  记录数: {numpy_usage['n_records']:,}")
print(f"  股票数: {numpy_usage['n_stocks']:,}")
print(f"  交易日: {numpy_usage['n_dates']}")

# 估算传统Python对象内存占用
# 每条DailyStockData对象约500-1000字节
traditional_mb = numpy_usage['n_records'] * 800 / 1024 / 1024
print(f"\n📦 传统Python对象（估算）:")
print(f"  约 {traditional_mb:.2f} MB")

print(f"\n💾 节省内存: {traditional_mb - numpy_usage['total_mb']:.2f} MB")
print(f"📉 减少: {(1 - numpy_usage['total_mb']/traditional_mb)*100:.1f}%")

# 性能测试
print("\n" + "=" * 60)
print("查询性能测试")
print("=" * 60)

# 获取测试数据
latest_date = memory_cache.get_latest_date()
if latest_date:
    top_stocks = memory_cache.get_top_n_stocks(latest_date, 10)
    test_stock_code = top_stocks[0].stock_code if top_stocks else None
    
    if test_stock_code:
        print(f"\n测试股票: {test_stock_code}")
        print(f"测试日期: {latest_date}")
        
        # 测试1: Numpy查询
        n_queries = 1000
        start_time = time.time()
        for _ in range(n_queries):
            data = numpy_stock_cache.get_data(test_stock_code, latest_date)
        numpy_time = (time.time() - start_time) / n_queries * 1000  # 转换为毫秒
        
        print(f"\n⚡ Numpy查询:")
        print(f"  {n_queries}次查询平均耗时: {numpy_time:.3f} ms")
        print(f"  数据示例: rank={data['rank']}, close_price={data['close_price']:.2f}")
        
        # 测试2: 传统查询（从字典）
        start_time = time.time()
        for _ in range(n_queries):
            data = memory_cache.get_daily_data(test_stock_code, latest_date)
        dict_time = (time.time() - start_time) / n_queries * 1000
        
        print(f"\n📚 传统字典查询:")
        print(f"  {n_queries}次查询平均耗时: {dict_time:.3f} ms")
        
        if numpy_time < dict_time:
            speedup = dict_time / numpy_time
            print(f"\n🚀 Numpy查询快 {speedup:.1f}x")
        
        # 测试3: 批量查询历史
        print("\n" + "=" * 60)
        print("批量历史查询测试")
        print("=" * 60)
        
        start_time = time.time()
        history = numpy_stock_cache.get_stock_history(test_stock_code, days=7)
        numpy_history_time = (time.time() - start_time) * 1000
        
        print(f"\n⚡ Numpy批量查询(7天):")
        print(f"  耗时: {numpy_history_time:.3f} ms")
        print(f"  返回记录数: {len(history)}")
        
        # 测试4: Top N查询
        print("\n" + "=" * 60)
        print("Top N查询测试")
        print("=" * 60)
        
        start_time = time.time()
        top_100 = numpy_stock_cache.get_top_n_by_rank(latest_date, 100)
        numpy_topn_time = (time.time() - start_time) * 1000
        
        print(f"\n⚡ Numpy Top100查询:")
        print(f"  耗时: {numpy_topn_time:.3f} ms")
        print(f"  返回股票数: {len(top_100)}")
        print(f"  前5只: {top_100[:5]}")

print("\n" + "=" * 60)
print("✅ 测试完成")
print("=" * 60)
