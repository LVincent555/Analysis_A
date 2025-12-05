"""
应用启动时的初始化操作

v0.5.0: 使用统一缓存系统，预加载3天热点榜数据
"""
import logging
from ..services.numpy_cache_middleware import numpy_cache
from ..services.hot_spots_cache import HotSpotsCache
from .caching import cache

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
        
        # 2. v0.5.0: 预加载最近3天热点榜到统一缓存系统
        logger.info("🔥 预加载热点榜缓存（最近3天）...")
        _preload_hotspots(days=3)
        logger.info("✅ 统一缓存系统已就绪")
        
    except Exception as e:
        logger.error(f"❌ 内存缓存加载失败: {e}")
        raise


def _preload_hotspots(days: int = 3):
    """预加载热点榜数据到统一缓存系统"""
    try:
        # 获取最近N天日期
        recent_dates = numpy_cache.get_dates_range(days)
        if not recent_dates:
            logger.warning("无可用日期，跳过热点榜预加载")
            return
        
        date_strs = [d.strftime('%Y%m%d') for d in recent_dates]
        logger.info(f"   预加载日期: {date_strs}")
        
        for date_str in date_strs:
            # 使用 HotSpotsCache 加载数据
            stocks = HotSpotsCache.get_full_data(date_str)
            
            # 存入统一缓存系统 (TTL=25小时)
            cache_key = f"hotspots_full_{date_str}"
            cache.set_api_cache("hotspots", cache_key, {
                "date": date_str,
                "total_count": len(stocks),
                "stocks": stocks
            }, ttl=90000)
            
            logger.info(f"   ✅ {date_str}: {len(stocks)} 只股票")
        
        logger.info(f"   📊 热点榜预加载完成: {len(date_strs)} 天")
        
    except Exception as e:
        logger.error(f"热点榜预加载失败: {e}")
