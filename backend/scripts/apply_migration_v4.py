import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "192.168.182.128")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "db_20251106_analysis_a")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

def run_migration():
    print(f"Connecting to {DATABASE_URL}...")
    engine = create_engine(DATABASE_URL)
    
    with open(r"d:\ProgramLanguage\py\Test\大A数据\2025年11月\stock_analysis_app\backend\migrations\006_board_signal_v4.sql", "r", encoding="utf-8") as f:
        sql_content = f.read()
    
    # Split by statements if possible, but the SQL provided is mostly DDL which can run in blocks.
    # However, Python drivers sometimes don't like multiple statements.
    # The file has comments and multiple statements.
    
    print("Executing migration...")
    with engine.connect() as conn:
        with conn.begin():
            conn.execute(text(sql_content))
    print("Migration completed successfully.")

if __name__ == "__main__":
    run_migration()
