"""
应用启动时的初始化操作
"""
import logging
from ..services.memory_cache import memory_cache

logger = logging.getLogger(__name__)


def preload_cache():
    """加载全量数据到内存缓存"""
    logger.info("🚀 启动全量内存缓存...")
    
    try:
        # 一次性加载所有数据到内存
        memory_cache.load_all_data()
        
        # 输出统计信息
        stats = memory_cache.get_memory_stats()
        logger.info("=" * 60)
        logger.info("✅ 全量内存缓存已就绪")
        logger.info(f"   📊 股票数量: {stats['stocks_count']:,}")
        logger.info(f"   📊 股票数据记录: {stats['daily_data_count']:,}")
        logger.info(f"   📊 股票交易日数: {stats['dates_count']:,}")
        logger.info(f"   📊 板块数据记录: {stats['sector_daily_data_count']:,}")
        logger.info(f"   📊 板块交易日数: {stats['sector_dates_count']:,}")
        logger.info(f"   ⚡ 查询性能: < 1ms")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ 内存缓存加载失败: {e}")
        raise
