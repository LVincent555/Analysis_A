"""清除缓存后测试"""
import sys
sys.path.append('.')

from app.services.analysis_service_db import analysis_service_db

# 清除缓存
print("清除缓存...")
analysis_service_db.cache.clear()
print("✅ 缓存已清除\n")

# 测试
result = analysis_service_db.analyze_period(period=2, filter_stocks=True)

print("前3只股票的行业字段类型检查：\n")
for i, stock in enumerate(result.stocks[:3], 1):
    print(f"{i}. {stock.code} - {stock.name}")
    print(f"   行业: {stock.industry}")
    print(f"   行业类型: {type(stock.industry)}")
    print()
