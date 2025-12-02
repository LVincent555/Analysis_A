"""
缓存管理API
提供缓存统计、清理等管理功能

重构后：统一使用 api_cache 二级缓存
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

from ..services.api_cache import api_cache
from ..services.numpy_cache_middleware import numpy_cache
from ..services.hot_spots_cache import HotSpotsCache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cache", tags=["cache"])


@router.get("/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """
    获取缓存统计信息
    
    Returns:
        缓存统计
    """
    try:
        # API二级缓存统计
        api_stats = api_cache.stats()
        
        # Numpy一级缓存统计
        numpy_stats = numpy_cache.get_memory_stats()
        
        # 热点榜缓存统计
        hotspots_stats = HotSpotsCache.get_cache_stats()
        
        return {
            "api_cache": {
                "mode": api_stats['mode'],
                "hits": api_stats['hits'],
                "misses": api_stats['misses'],
                "hit_rate": api_stats['hit_rate'],
                "size_mb": api_stats.get('size_mb', 0),
                "count": api_stats.get('count', 0)
            },
            "numpy_cache": {
                "total_mb": numpy_stats['total_mb'],
                "stocks_count": numpy_stats['stocks_count'],
                "daily_records": numpy_stats['daily_data']['n_records'],
                "sector_records": numpy_stats['sector_data']['n_records']
            },
            "hotspots_cache": {
                "cached_dates": len(hotspots_stats['cached_dates']),
                "memory_kb": hotspots_stats['memory_usage_kb']
            }
        }
    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear")
async def clear_cache(
    cache_type: str = "all",
    pattern: str = None
) -> Dict[str, Any]:
    """
    清除缓存
    
    Args:
        cache_type: 缓存类型 (api/hotspots/all)
        pattern: 模式匹配（仅对api缓存有效）
    
    Returns:
        清除结果
    """
    try:
        cleared = {}
        
        if cache_type in ["api", "all"]:
            api_cache.invalidate(pattern)
            cleared["api_cache"] = "已清理"
        
        if cache_type in ["hotspots", "all"]:
            HotSpotsCache.clear_cache()
            cleared["hotspots_cache"] = "已清理"
        
        logger.info(f"✅ 缓存清理完成: {cleared}")
        
        return {
            "success": True,
            "cleared": cleared,
            "pattern": pattern
        }
    
    except Exception as e:
        logger.error(f"清除缓存失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reload")
async def reload_all_cache() -> Dict[str, Any]:
    """
    重新加载所有缓存（数据导入后调用）
    
    Returns:
        重载结果
    """
    try:
        from ..core.startup import preload_cache
        
        logger.info("🔄 开始重新加载所有缓存...")
        preload_cache()
        
        return {
            "success": True,
            "message": "所有缓存已重新加载"
        }
    
    except Exception as e:
        logger.error(f"重载缓存失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def cache_health_check() -> Dict[str, Any]:
    """
    缓存健康检查
    
    Returns:
        健康状态
    """
    try:
        stats = await get_cache_stats()
        
        # 简单的健康评估
        status = "healthy"
        api_hit_rate = float(stats["api_cache"]["hit_rate"].rstrip('%'))
        
        if api_hit_rate < 30:
            status = "warning"  # 命中率过低
        
        return {
            "status": status,
            "api_cache": stats["api_cache"],
            "numpy_cache_mb": stats["numpy_cache"]["total_mb"],
            "hotspots_dates": stats["hotspots_cache"]["cached_dates"]
        }
    
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
