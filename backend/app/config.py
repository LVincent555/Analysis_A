"""
应用配置文件
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 数据目录
DATA_DIR = BASE_DIR.parent / "data"

# API配置
API_V1_PREFIX = "/api"
PROJECT_NAME = "股票分析系统"
VERSION = "0.2.6"  # 全局信号配置系统

# 数据源配置
USE_DATABASE = os.getenv("USE_DATABASE", "true").lower() == "true"  # 是否使用数据库

# CORS配置
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:3002",
    "http://127.0.0.1:12701",  # IDE内置浏览器代理
    "*",  # 开发环境允许所有来源
]

# 缓存配置
CACHE_ENABLED = True

# 数据加载配置
DEFAULT_MAX_STOCKS = 100  # 默认加载的股票数量
TOP_N_STOCKS = 1000  # 行业分析的股票数量

# 文件名模式（支持多种模式）
# 注意：主文件已包含北交所数据，_bjs文件是重复的，不导入
FILE_PATTERNS = [
    "*_data_sma_feature_color.xlsx",      # 主板+双创板+北交所（全部数据）
    # "*_data_sma_feature_color_bjs.xlsx"   # 北交所单独文件（已注释，避免重复）
]
FILE_PATTERN = "*_data_sma_feature_color.xlsx"  # 向后兼容
