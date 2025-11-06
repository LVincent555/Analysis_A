"""清除缓存"""
import sys
sys.path.append('.')

from app.services.analysis_service_db import analysis_service_db

print("清除缓存...")
analysis_service_db.cache.clear()
print("✅ 缓存已清除")
