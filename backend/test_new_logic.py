"""直接测试新逻辑（不通过HTTP）"""
import sys
sys.path.append('.')

from app.services.analysis_service_db import analysis_service_db

# 清除缓存
print("清除缓存...")
analysis_service_db.cache.clear()
print("✅ 缓存已清除\n")

# 测试分析
print("=" * 60)
print("测试：只统计最新一天的数据")
print("=" * 60 + "\n")

result = analysis_service_db.analyze_period(period=2, filter_stocks=True)

print(f"📅 日期: {result.start_date}")
print(f"📊 总股票数: {result.total_stocks}只")
print(f"🔢 all_dates: {result.all_dates}")

print("\n前5只股票：")
for i, stock in enumerate(result.stocks[:5], 1):
    print(f"{i}. {stock.code} - {stock.name}")
    print(f"   排名: 第{stock.rank}名")
    print(f"   出现次数: {stock.count}次")
    if stock.date_rank_info:
        for info in stock.date_rank_info:
            date = info.get('date') if isinstance(info, dict) else getattr(info, 'date', None)
            rank = info.get('rank') if isinstance(info, dict) else getattr(info, 'rank', None)
            if date and rank:
                print(f"   {date}(第{rank}名)")

print("\n✅ 验证：所有股票的count都应该是1")
all_count_1 = all(s.count == 1 for s in result.stocks)
print(f"结果: {'✅ 通过' if all_count_1 else '❌ 失败'}")

print("\n✅ 验证：只有一个日期")
one_date = len(result.all_dates) == 1
print(f"结果: {'✅ 通过' if one_date else '❌ 失败'}")

print(f"\n总结：{'✅ 所有测试通过！' if (all_count_1 and one_date) else '❌ 有测试失败'}")
