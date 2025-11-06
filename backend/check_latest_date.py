"""检查数据库最新日期"""
import sys
sys.path.append('.')

from app.database import SessionLocal
from app.db_models import DailyStockData
from sqlalchemy import desc

db = SessionLocal()
try:
    # 获取最近5个日期
    dates = db.query(DailyStockData.date)\
        .distinct()\
        .order_by(desc(DailyStockData.date))\
        .limit(5)\
        .all()
    
    print("\n数据库最近5个日期：")
    for i, (date,) in enumerate(dates, 1):
        date_str = date.strftime('%Y年%m月%d日')
        
        # 统计这天有多少条数据
        count = db.query(DailyStockData)\
            .filter(DailyStockData.date == date)\
            .count()
        
        print(f"{i}. {date_str} - {count}条数据")
    
finally:
    db.close()
