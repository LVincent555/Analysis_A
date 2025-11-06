"""检查股票603262的排名情况"""
import sys
sys.path.append('.')

from app.database import SessionLocal
from app.db_models import DailyStockData, Stock
from sqlalchemy import desc

db = SessionLocal()
try:
    stock_code = '603262'
    
    # 获取股票名称
    stock = db.query(Stock).filter(Stock.stock_code == stock_code).first()
    print(f"\n股票：{stock_code} - {stock.stock_name if stock else '未知'}")
    print("=" * 60)
    
    # 获取最近5天的排名
    data = db.query(DailyStockData)\
        .filter(DailyStockData.stock_code == stock_code)\
        .order_by(desc(DailyStockData.date))\
        .limit(5)\
        .all()
    
    print("\n最近5天的排名情况：")
    for d in data:
        date_str = d.date.strftime('%Y年%m月%d日')
        print(f"{date_str}: 第{d.rank}名")
    
    print("\n" + "=" * 60)
    print("分析结论：")
    print("如果设置TOP N为20，那么：")
    for d in data:
        date_str = d.date.strftime('%Y年%m月%d日')
        if d.rank <= 20:
            print(f"✅ {date_str}: 第{d.rank}名 - 会被统计")
        else:
            print(f"❌ {date_str}: 第{d.rank}名 - 不会被统计（超出TOP20）")
    
finally:
    db.close()
