"""
应用启动时的初始化操作
"""
import logging
from ..services.numpy_cache_middleware import numpy_cache
from ..services.hot_spots_cache import HotSpotsCache
from ..services.api_cache import api_cache

logger = logging.getLogger(__name__)


def preload_cache():
    """加载全量数据到内存缓存"""
    logger.info("🚀 启动 Numpy 缓存中间件...")
    
    try:
        # 1. 加载 Numpy 一级缓存
        logger.info("=" * 60)
        logger.info("📦 加载 Numpy 缓存...")
        numpy_cache.reload(days=30)
        numpy_stats = numpy_cache.get_memory_stats()
        logger.info(f"   ✅ Numpy缓存: {numpy_stats['total_mb']:.2f} MB")
        logger.info(f"   📊 股票: {numpy_stats['stocks_count']} 只")
        logger.info(f"   📊 日数据: {numpy_stats['daily_data']['n_records']} 条")
        logger.info(f"   📊 板块数据: {numpy_stats['sector_data']['n_records']} 条")
        logger.info("=" * 60)
        
        # 2. 清理二级缓存
        logger.info("🧹 清理API二级缓存...")
        HotSpotsCache.clear_cache()
        api_cache.invalidate()
        cache_stats = api_cache.stats()
        logger.info(f"   ✅ 已清理API二级缓存")
        logger.info(f"   💾 缓存模式: {cache_stats['mode']}")
        if cache_stats.get('size_mb'):
            logger.info(f"   📊 缓存大小: {cache_stats['size_mb']:.2f} MB")
        
        # 3. 预加载热点榜缓存（最近21天）
        logger.info("🔥 预加载热点榜缓存（最近21天）...")
        HotSpotsCache.preload_recent_dates(days=21)  # 与股票数据天数一致
        
        hot_stats = HotSpotsCache.get_cache_stats()
        logger.info("=" * 60)
        logger.info("✅ 热点榜缓存已就绪")
        logger.info(f"   📅 已缓存日期: {', '.join(hot_stats['cached_dates'][:5])}")
        logger.info(f"   📊 缓存天数: {hot_stats['total_dates']}")
        logger.info(f"   💾 内存占用: {hot_stats['memory_usage_kb']} KB")
        logger.info(f"   ⚡ 查询性能: O(1)")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ 内存缓存加载失败: {e}")
        raise
