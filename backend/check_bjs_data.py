"""检查数据库中的北交所数据"""
import sys
sys.path.append('.')

from app.database import SessionLocal
from app.db_models import DailyStockData, Stock

db = SessionLocal()

try:
    # 统计920开头的数据
    count = db.query(DailyStockData).filter(DailyStockData.stock_code.like('920%')).count()
    print(f"\n数据库中920开头的股票数据: {count}条\n")
    
    if count > 0:
        print("样例数据:")
        samples = db.query(DailyStockData.stock_code, DailyStockData.date)\
            .filter(DailyStockData.stock_code.like('920%'))\
            .order_by(DailyStockData.date.desc())\
            .limit(10)\
            .all()
        
        for code, date in samples:
            print(f"  {code} - {date}")
        
        # 统计每个日期的920数据
        print("\n每日920数据统计:")
        from sqlalchemy import func
        daily_counts = db.query(
            DailyStockData.date,
            func.count(DailyStockData.stock_code).label('count')
        ).filter(DailyStockData.stock_code.like('920%'))\
         .group_by(DailyStockData.date)\
         .order_by(DailyStockData.date.desc())\
         .all()
        
        for date, cnt in daily_counts:
            print(f"  {date}: {cnt}只股票")
    else:
        print("✅ 数据库中没有920开头的数据，可以安全导入北交所文件")
        
finally:
    db.close()
