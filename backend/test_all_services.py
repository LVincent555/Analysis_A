"""
测试所有数据库服务
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from app.services.analysis_service_db import analysis_service_db
from app.services.stock_service_db import stock_service_db
from app.services.rank_jump_service_db import rank_jump_service_db
from app.services.steady_rise_service_db import steady_rise_service_db
from app.services.industry_service_db import industry_service_db

print("\n" + "=" * 60)
print("测试所有数据库服务")
print("=" * 60 + "\n")

# 1. 测试AnalysisService
print("1️⃣  测试热点分析服务...")
try:
    dates = analysis_service_db.get_available_dates()
    print(f"   ✅ 可用日期: {len(dates)}天 - {dates[:3]}")
    
    result = analysis_service_db.analyze_period(period=3, max_count=20)
    print(f"   ✅ 3天分析: {result.total_stocks}只股票")
except Exception as e:
    print(f"   ❌ 错误: {e}")

# 2. 测试StockService  
print("\n2️⃣  测试股票查询服务...")
try:
    stock = stock_service_db.search_stock("平安银行")
    if stock:
        print(f"   ✅ 找到: {stock.code} - {stock.name}")
        print(f"   ✅ 历史数据: {stock.appears_count}天")
    else:
        print("   ⚠️  未找到股票")
except Exception as e:
    print(f"   ❌ 错误: {e}")

# 3. 测试RankJumpService
print("\n3️⃣  测试排名跳变服务...")
try:
    result = rank_jump_service_db.analyze_rank_jump(jump_threshold=2500)
    print(f"   ✅ 跳变股票: {result.total_count}只")
    print(f"   ✅ 均值: {result.mean_rank_change:.0f}, 标准差: {result.std_rank_change:.0f}")
except Exception as e:
    print(f"   ❌ 错误: {e}")

# 4. 测试SteadyRiseService
print("\n4️⃣  测试稳步上升服务...")
try:
    result = steady_rise_service_db.analyze_steady_rise(period=3, min_rank_improvement=100)
    print(f"   ✅ 稳步上升: {result.total_count}只")
    print(f"   ✅ 均值提升: {result.mean_improvement:.0f}")
except Exception as e:
    print(f"   ❌ 错误: {e}")

# 5. 测试IndustryService
print("\n5️⃣  测试行业趋势服务...")
try:
    trends = industry_service_db.analyze_industry(period=3, top_n=20)
    print(f"   ✅ 热门行业: {len(trends)}个")
    if trends:
        print(f"   ✅ TOP3: {[t.industry for t in trends[:3]]}")
except Exception as e:
    print(f"   ❌ 错误: {e}")

print("\n" + "=" * 60)
print("✅ 所有服务测试完成")
print("=" * 60 + "\n")
