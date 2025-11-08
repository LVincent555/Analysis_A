"""
清除所有服务的缓存
支持TTL缓存和普通dict缓存
"""
import sys
sys.path.append('.')

from app.services.analysis_service_db import analysis_service_db
from app.services.industry_service_db import industry_service_db
from app.services.sector_service_db import sector_service_db
from app.services.stock_service_db import stock_service_db
from app.services.rank_jump_service_db import rank_jump_service_db
from app.services.steady_rise_service_db import steady_rise_service_db

print("🧹 开始清除所有缓存...")
print("=" * 60)

services = [
    ("AnalysisService", analysis_service_db),
    ("IndustryService", industry_service_db),
    ("SectorService", sector_service_db),
    ("StockService", stock_service_db),
    ("RankJumpService", rank_jump_service_db),
    ("SteadyRiseService", steady_rise_service_db)
]

total_cleared = 0
for service_name, service in services:
    try:
        if hasattr(service.cache, 'clear'):
            # TTL缓存
            count = service.cache.clear()
            print(f"✅ {service_name}: 清除 {count} 个缓存项")
            total_cleared += count
        else:
            # 普通dict缓存
            count = len(service.cache)
            service.cache.clear()
            print(f"✅ {service_name}: 清除 {count} 个缓存项")
            total_cleared += count
    except Exception as e:
        print(f"❌ {service_name}: 清除失败 - {e}")

print("=" * 60)
print(f"🎉 缓存清除完成！共清除 {total_cleared} 个缓存项")
