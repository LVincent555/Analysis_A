"""
验证股票代码格式
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from app.database import SessionLocal
from app.db_models import Stock
from sqlalchemy import func, text

def main():
    """验证股票代码格式"""
    db = SessionLocal()
    
    print("=" * 60)
    print("股票代码格式验证")
    print("=" * 60)
    
    # 查询所有股票代码
    stocks = db.query(Stock).order_by(Stock.stock_code).limit(20).all()
    
    print("\n前20只股票代码:")
    for i, stock in enumerate(stocks, 1):
        code_len = len(stock.stock_code)
        status = "✅" if code_len == 6 else "❌"
        print(f"{i:2d}. {status} {stock.stock_code} ({code_len}位) - {stock.stock_name}")
    
    # 统计代码长度分布
    print("\n" + "=" * 60)
    print("股票代码长度统计:")
    print("=" * 60)
    
    length_stats = db.execute(text("""
        SELECT 
            LENGTH(stock_code) as code_length,
            COUNT(*) as count
        FROM stocks
        GROUP BY LENGTH(stock_code)
        ORDER BY code_length
    """)).fetchall()
    
    for length, count in length_stats:
        print(f"  {length}位代码: {count}只股票")
    
    # 查找特定股票（之前有问题的 57）
    print("\n" + "=" * 60)
    print("验证修复的股票代码:")
    print("=" * 60)
    
    test_codes = ['000057', '57', '00057']
    for code in test_codes:
        stock = db.query(Stock).filter(Stock.stock_code == code).first()
        if stock:
            print(f"✅ 找到: {stock.stock_code} - {stock.stock_name}")
        else:
            print(f"❌ 未找到: {code}")
    
    db.close()

if __name__ == "__main__":
    main()
