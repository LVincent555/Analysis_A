"""测试锚定逻辑"""
import sys
sys.path.append('.')

from app.services.analysis_service_db import analysis_service_db

# 清除缓存
print("清除缓存...")
analysis_service_db.cache.clear()
print("✅ 缓存已清除\n")

# 测试分析
print("=" * 60)
print("测试：锚定最新日期，回溯统计重复次数")
print("=" * 60 + "\n")

result = analysis_service_db.analyze_period(period=3, filter_stocks=True)

print(f"📅 开始日期: {result.start_date}")
print(f"📅 结束日期: {result.end_date}")
print(f"📊 总股票数: {result.total_stocks}只")
print(f"🔢 所有日期: {result.all_dates}")

print("\n前10只股票（按出现次数排序）：")
for i, stock in enumerate(result.stocks[:10], 1):
    print(f"\n{i}. {stock.code} - {stock.name} ({stock.industry})")
    print(f"   最新排名: 第{stock.rank}名")
    print(f"   出现次数: {stock.count}次")
    print(f"   出现详情:")
    if stock.date_rank_info:
        for info in stock.date_rank_info:
            date = info.get('date') if isinstance(info, dict) else getattr(info, 'date', None)
            rank = info.get('rank') if isinstance(info, dict) else getattr(info, 'rank', None)
            if date and rank:
                # 标注是否是最新日期
                is_latest = date == result.all_dates[0]
                marker = "🔥" if is_latest else "  "
                print(f"      {marker} {date}(第{rank}名)")

print("\n✅ 验证逻辑：")
print(f"1. 所有股票都在最新日期({result.all_dates[0]})出现: ", end="")
all_in_latest = all(
    any(
        (info.get('date') if isinstance(info, dict) else getattr(info, 'date', None)) == result.all_dates[0]
        for info in stock.date_rank_info
    )
    for stock in result.stocks
)
print("✅ 通过" if all_in_latest else "❌ 失败")

print(f"2. 所有股票出现次数 >= 2: ", end="")
all_count_gte_2 = all(s.count >= 2 for s in result.stocks)
print("✅ 通过" if all_count_gte_2 else "❌ 失败")

print(f"\n总结：{'✅ 所有测试通过！' if (all_in_latest and all_count_gte_2) else '❌ 有测试失败'}")
