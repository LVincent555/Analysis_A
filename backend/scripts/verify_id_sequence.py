"""
验证ID序列是否从1开始
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.db_models import DailyStockData
from sqlalchemy import text

def main():
    """验证ID序列"""
    db = SessionLocal()
    
    print("=" * 60)
    print("验证ID序列")
    print("=" * 60)
    
    # 查询最小和最大ID
    result = db.execute(text("""
        SELECT 
            MIN(id) as min_id,
            MAX(id) as max_id,
            COUNT(*) as total_count
        FROM daily_stock_data
    """)).fetchone()
    
    min_id, max_id, total_count = result
    
    print(f"\n最小ID: {min_id}")
    print(f"最大ID: {max_id}")
    print(f"总记录数: {total_count}")
    
    if min_id == 1:
        print("\n✅ ID序列正确：从1开始")
    else:
        print(f"\n❌ ID序列异常：从{min_id}开始")
    
    # 查看前5条记录
    print("\n" + "=" * 60)
    print("前5条记录:")
    print("=" * 60)
    
    first_five = db.query(DailyStockData).order_by(DailyStockData.id).limit(5).all()
    for record in first_five:
        print(f"ID: {record.id}, 股票: {record.stock_code}, 日期: {record.date}, 排名: {record.rank}")
    
    db.close()

if __name__ == "__main__":
    main()
