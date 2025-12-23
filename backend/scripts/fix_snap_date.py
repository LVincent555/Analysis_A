#!/usr/bin/env python3
"""
修复 ext_board_daily_snap 中非交易日的快照日期
将周末/节假日的快照日期回退到最近交易日
"""

import os
import sys
from datetime import date

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "192.168.182.128")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "db_20251106_analysis_a")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


def get_latest_trade_date(engine, target_date: date) -> date:
    """从 daily_stock_data 获取 <= target_date 的最近交易日"""
    sql = "SELECT MAX(date) FROM daily_stock_data WHERE rank IS NOT NULL AND date <= :d"
    with engine.connect() as conn:
        row = conn.execute(text(sql), {"d": target_date}).fetchone()
        return row[0] if row and row[0] else None


def main():
    engine = create_engine(DATABASE_URL)
    
    # 1. 查看当前快照日期
    print("=" * 50)
    print("当前 ext_board_daily_snap 日期分布:")
    print("=" * 50)
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT date, COUNT(*) as cnt 
            FROM ext_board_daily_snap 
            GROUP BY date 
            ORDER BY date DESC
        """))
        snap_dates = []
        for row in result:
            snap_dates.append(row[0])
            print(f"  {row[0]}  ({row[1]:,} 条)")
    
    # 2. 检查哪些日期需要修复（非交易日）
    print("\n" + "=" * 50)
    print("检查需要修复的日期:")
    print("=" * 50)
    
    fixes = []
    for snap_date in snap_dates:
        trade_date = get_latest_trade_date(engine, snap_date)
        if trade_date and trade_date != snap_date:
            fixes.append((snap_date, trade_date))
            print(f"  ❌ {snap_date} (非交易日) → 应改为 {trade_date}")
        else:
            print(f"  ✓ {snap_date} (交易日，无需修复)")
    
    if not fixes:
        print("\n✅ 所有日期均为交易日，无需修复！")
        return 0
    
    # 3. 执行修复
    print("\n" + "=" * 50)
    print("执行修复:")
    print("=" * 50)
    
    with engine.connect() as conn:
        for old_date, new_date in fixes:
            # 检查目标日期是否已存在数据
            existing = conn.execute(text(
                "SELECT COUNT(*) FROM ext_board_daily_snap WHERE date = :d"
            ), {"d": new_date}).scalar()
            
            if existing > 0:
                # 目标日期已有数据，删除旧日期的数据
                conn.execute(text(
                    "DELETE FROM ext_board_daily_snap WHERE date = :d"
                ), {"d": old_date})
                print(f"  🗑️ {old_date} → 删除 (目标 {new_date} 已有数据)")
            else:
                # 目标日期无数据，更新日期
                result = conn.execute(text(
                    "UPDATE ext_board_daily_snap SET date = :new WHERE date = :old"
                ), {"new": new_date, "old": old_date})
                print(f"  ✏️ {old_date} → {new_date} (更新 {result.rowcount:,} 条)")
        
        conn.commit()
    
    # 4. 验证结果
    print("\n" + "=" * 50)
    print("修复后 ext_board_daily_snap 日期分布:")
    print("=" * 50)
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT date, COUNT(*) as cnt 
            FROM ext_board_daily_snap 
            GROUP BY date 
            ORDER BY date DESC
        """))
        for row in result:
            print(f"  {row[0]}  ({row[1]:,} 条)")
    
    print("\n🎉 修复完成！")
    return 0


if __name__ == "__main__":
    sys.exit(main())
