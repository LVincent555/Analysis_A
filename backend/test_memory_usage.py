"""
测试全量内存缓存的内存占用
"""
import sys
import os
import psutil
import logging

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from app.services.memory_cache import memory_cache

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_memory_mb():
    """获取当前进程内存使用（MB）"""
    process = psutil.Process()
    return process.memory_info().rss / 1024 / 1024

def main():
    print("=" * 80)
    print("📊 全量内存缓存测试")
    print("=" * 80)
    
    # 1. 初始内存
    initial_memory = get_memory_mb()
    print(f"\n🔹 初始内存: {initial_memory:.2f} MB")
    
    # 2. 加载数据
    print(f"\n{'=' * 80}")
    print("开始加载数据...")
    print(f"{'=' * 80}\n")
    
    memory_cache.load_all_data()
    
    # 3. 加载后内存
    after_load_memory = get_memory_mb()
    memory_used = after_load_memory - initial_memory
    
    print(f"\n{'=' * 80}")
    print("📊 内存使用统计")
    print(f"{'=' * 80}")
    print(f"  初始内存: {initial_memory:.2f} MB")
    print(f"  加载后内存: {after_load_memory:.2f} MB")
    print(f"  💾 数据占用: {memory_used:.2f} MB")
    
    # 4. 数据统计
    stats = memory_cache.get_memory_stats()
    print(f"\n{'=' * 80}")
    print("📈 数据统计")
    print(f"{'=' * 80}")
    print(f"  股票数量: {stats['stocks_count']:,}")
    print(f"  交易日数: {stats['dates_count']:,}")
    print(f"  数据记录: {stats['daily_data_count']:,}")
    print(f"  日期索引: {stats['date_index_keys']:,}")
    print(f"  股票索引: {stats['stock_index_keys']:,}")
    
    # 5. 平均每条记录占用
    if stats['daily_data_count'] > 0:
        bytes_per_record = (memory_used * 1024 * 1024) / stats['daily_data_count']
        print(f"\n  平均每条记录: {bytes_per_record:.2f} bytes")
    
    # 6. 性能测试
    print(f"\n{'=' * 80}")
    print("⚡ 性能测试")
    print(f"{'=' * 80}")
    
    import time
    
    # 测试获取日期
    start = time.time()
    dates = memory_cache.get_available_dates()
    elapsed = (time.time() - start) * 1000
    print(f"  获取所有日期: {elapsed:.2f} ms ({len(dates)} 个)")
    
    # 测试获取TOP 100
    if memory_cache.dates:
        latest_date = memory_cache.dates[0]
        start = time.time()
        top_stocks = memory_cache.get_top_n_stocks(latest_date, 100)
        elapsed = (time.time() - start) * 1000
        print(f"  获取TOP 100: {elapsed:.2f} ms ({len(top_stocks)} 条)")
    
    # 测试获取股票历史
    if memory_cache.stocks and memory_cache.dates:
        stock_code = list(memory_cache.stocks.keys())[0]
        start = time.time()
        history = memory_cache.get_stock_history(stock_code, memory_cache.dates[:10])
        elapsed = (time.time() - start) * 1000
        print(f"  获取股票10天历史: {elapsed:.2f} ms ({len(history)} 条)")
    
    print(f"\n{'=' * 80}")
    print("✅ 测试完成！")
    print(f"{'=' * 80}\n")
    
    # 7. 建议
    print("💡 建议:")
    if memory_used < 500:
        print(f"  ✅ 内存占用 {memory_used:.0f}MB，可以全量缓存")
    elif memory_used < 1000:
        print(f"  ⚠️  内存占用 {memory_used:.0f}MB，建议服务器至少2GB内存")
    else:
        print(f"  ❌ 内存占用 {memory_used:.0f}MB，可能需要考虑分页或懒加载")
    
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
