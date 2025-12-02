
import sys
import os

# 添加 backend 目录到 sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from app.models.stock import StockDailyFull, StockFullHistory
    from app.services.stock_service_db import StockServiceDB
    from app.routers.stock import search_stock_full
    print("✅ Syntax check passed: Models and Services imported successfully.")
except Exception as e:
    print(f"❌ Syntax check failed: {e}")
    import traceback
    traceback.print_exc()
