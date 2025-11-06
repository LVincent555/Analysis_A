"""
应用配置文件
"""
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据目录
DATA_DIR = BASE_DIR.parent / "data"

# API配置
API_V1_PREFIX = "/api"
PROJECT_NAME = "股票分析系统"
VERSION = "0.1.1"

# CORS配置
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
]

# 缓存配置
CACHE_ENABLED = True

# 数据加载配置
DEFAULT_MAX_STOCKS = 100  # 默认加载的股票数量
TOP_N_STOCKS = 1000  # 行业分析的股票数量

# 文件名模式
FILE_PATTERN = "*_data_sma_feature_color.xlsx"
