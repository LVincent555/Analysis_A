
import sys
import os
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import date

# Add backend directory to path
sys.path.append(os.path.join(os.getcwd(), 'stock_analysis_app', 'backend'))

from scripts.task_board_heat import BoardHeatCalculator
from app.core.config_loader import ConfigLoader

def test_load_data():
    # Setup DB connection
    # Assuming connection string is standard
    db_url = "postgresql://postgres:password@localhost:5432/stock_analysis" 
    engine = create_engine(db_url)
    
    config = ConfigLoader(engine)
    calculator = BoardHeatCalculator(engine, config)
    
    trade_date = date(2025, 12, 10)
    snap_date = date(2025, 12, 10)
    
    print(f"Testing load_data for {trade_date}...")
    
    try:
        df_snap, df_stock, df_board = calculator._load_data(trade_date, snap_date)
        
        print(f"\ndf_stock columns: {df_stock.columns.tolist()}")
        print(f"df_stock shape: {df_stock.shape}")
        
        if 'turnover_rate_percent' in df_stock.columns:
            print("turnover_rate_percent is present.")
            
            # Check specific stock
            target_stock = '603037'
            row = df_stock[df_stock['stock_code'] == target_stock]
            if not row.empty:
                print(f"\nData for {target_stock}:")
                print(row.iloc[0].to_dict())
                
                # Test calculation logic
                stock_row = row.iloc[0]
                raw_turnover = float(stock_row.get('turnover_rate_percent', 0) or 0)
                turnover_score = min(100, max(0, raw_turnover * 5))
                print(f"Calculated turnover_score: {turnover_score}")
                
                raw_vol = float(stock_row.get('volume_days', 0) or 0)
                vol_score = min(100, max(0, 50 + raw_vol * 2.5))
                print(f"Calculated vol_score: {vol_score}")
            else:
                print(f"Stock {target_stock} not found in df_stock")
        else:
            print("ERROR: turnover_rate_percent column MISSING from df_stock")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_load_data()
