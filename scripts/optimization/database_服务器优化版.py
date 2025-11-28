"""
数据库连接和会话管理 - 服务器优化版

🔥 优化配置（2025-11-25）：
- pool_size: 10 → 2（节省390MB内存）
- max_overflow: 20 → 2
- pool_recycle: 3600（保持）
- pool_timeout: 30（新增）

适用于：2核2G服务器
"""
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql://postgres:3.1415926@localhost:5432/db_20251106_analysis_a"

# 🔥 优化后的数据库引擎配置
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,      # 检查连接有效性
    pool_size=2,             # 🔥 优化：10 → 2（2核CPU足够）
    max_overflow=2,          # 🔥 优化：20 → 2（减少溢出）
    pool_recycle=3600,       # 1小时回收连接
    pool_timeout=30,         # 🔥 新增：30秒超时
    echo=False               # 不打印SQL
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_connection():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"数据库连接失败: {e}")
        return False
