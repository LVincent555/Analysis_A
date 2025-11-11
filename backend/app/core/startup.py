"""
应用启动时的初始化操作
"""
import logging
from ..services.memory_cache import memory_cache
from ..services.hot_spots_cache import HotSpotsCache
from ..services.industry_detail_service import industry_detail_service
from ..services.stock_service_db import stock_service_db
from ..services.analysis_service_db import analysis_service_db
from ..services.industry_service_db import industry_service_db
from ..services.sector_service_db import sector_service_db

logger = logging.getLogger(__name__)


def preload_cache():
    """加载全量数据到内存缓存"""
    logger.info("🚀 启动全量内存缓存...")
    
    try:
        # 1. 加载所有数据到内存
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
        
        # 2. 清理旧缓存（重要：逻辑已更改）
        logger.info("🧹 清理旧缓存...")
        HotSpotsCache.clear_cache()
        
        # 清理所有服务的TTLCache
        industry_detail_count = industry_detail_service.cache.clear()
        stock_count = stock_service_db.cache.clear()
        analysis_count = analysis_service_db.cache.clear()
        industry_count = industry_service_db.cache.clear()
        sector_count = sector_service_db.cache.clear()
        
        total_cleared = industry_detail_count + stock_count + analysis_count + industry_count + sector_count
        logger.info(f"   ✅ 已清理行业详情缓存: {industry_detail_count} 项")
        logger.info(f"   ✅ 已清理个股缓存: {stock_count} 项")
        logger.info(f"   ✅ 已清理分析缓存: {analysis_count} 项")
        logger.info(f"   ✅ 已清理行业统计缓存: {industry_count} 项")
        logger.info(f"   ✅ 已清理板块缓存: {sector_count} 项")
        logger.info(f"   📊 总计清理: {total_cleared} 项")
        
        # 3. 预加载热点榜缓存（最近3天）
        logger.info("🔥 预加载热点榜缓存（最近3天）...")
        HotSpotsCache.preload_recent_dates(days=3)
        
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
