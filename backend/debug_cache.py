"""调试脚本：检查内存缓存状态"""
import sys
sys.path.insert(0, '.')

from app.services.memory_cache import memory_cache

print("内存缓存状态：")
print(f"  stocks数量: {len(memory_cache.stocks)}")
print(f"  daily_data_by_date数量: {len(memory_cache.daily_data_by_date)}")
print(f"  dates数量: {len(memory_cache.dates)}")

if memory_cache.stocks:
    # 显示前5个股票
    print("\n前5个股票信息：")
    for i, (code, stock) in enumerate(list(memory_cache.stocks.items())[:5]):
        print(f"  {i+1}. {stock.stock_code} - {stock.stock_name} - 行业: {stock.industry}")
    
    # 统计行业
    industries = {}
    for stock in memory_cache.stocks.values():
        if stock.industry:
            industries[stock.industry] = industries.get(stock.industry, 0) + 1
    
    print(f"\n行业统计（前20个）：")
    sorted_industries = sorted(industries.items(), key=lambda x: x[1], reverse=True)[:20]
    for ind, count in sorted_industries:
        print(f"  {ind}: {count}只")
    
    # 查找通信相关
    print("\n包含'通'字的行业：")
    for ind in sorted(industries.keys()):
        if '通' in ind:
            print(f"  - {ind} ({industries[ind]}只)")
else:
    print("  ⚠️  内存缓存为空！")
