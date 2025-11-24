"""
数据库连接和会话管理

🔥 已优化版本 - 2025-11-25
- pool_size: 10 → 2（节省390MB内存）
- max_overflow: 20 → 2
- 新增: pool_recycle=3600（1小时回收）
- 新增: pool_timeout=30（30秒超时）
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import logging

# 加载环境变量
load_dotenv()

logger = logging.getLogger(__name__)

# 数据库连接配置
DB_HOST = os.getenv("DB_HOST", "192.168.182.128")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "db_20251106_analysis_a")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

# 构建数据库URL
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# 创建数据库引擎 - 🔥 已优化配置
engine = create_engine(
    DATABASE_URL,
    pool_size=2,         # 🔥 优化：10 → 2（2核CPU，2个连接足够）
    max_overflow=2,      # 🔥 优化：20 → 2（减少溢出连接）
    pool_recycle=3600,   # 🔥 新增：1小时回收连接，避免长连接占用内存
    pool_timeout=30,     # 🔥 新增：30秒超时，避免死锁
    pool_pre_ping=True,  # 检查连接是否有效
    echo=False           # 是否打印SQL语句
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建Base类
Base = declarative_base()


def get_db():
    """
    获取数据库会话
    用于FastAPI依赖注入
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection():
    """
    测试数据库连接
    """
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"数据库连接成功: {DB_HOST}:{DB_PORT}/{DB_NAME}")
        return True
    except Exception as e:
        logger.error(f"数据库连接失败: {str(e)}")
        return False
