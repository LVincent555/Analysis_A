"""
缓存管理API
提供缓存统计、清理等管理功能

v0.5.0: 使用统一缓存系统，移除旧的api_cache
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

from ..services.numpy_cache_middleware import numpy_cache
from ..services.hot_spots_cache import HotSpotsCache
from ..core.caching import cache as unified_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cache", tags=["cache"])


@router.get("/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """
    获取缓存统计信息
    
    v0.5.0: 使用统一缓存系统
    
    Returns:
        缓存统计
    """
    try:
        # Numpy一级缓存统计
        numpy_stats = numpy_cache.get_memory_stats()
        
        # 热点榜缓存统计
        hotspots_stats = HotSpotsCache.get_cache_stats()
        
        # 统一缓存系统统计
        unified_stats = unified_cache.stats()
        
        return {
            "numpy_cache": {
                "total_mb": numpy_stats['total_mb'],
                "stocks_count": numpy_stats['stocks_count'],
                "daily_records": numpy_stats['daily_data']['n_records'],
                "sector_records": numpy_stats['sector_data']['n_records']
            },
            "hotspots_cache": {
                "cached_dates": len(hotspots_stats['cached_dates']),
                "memory_kb": hotspots_stats['memory_usage_kb']
            },
            "unified_cache": unified_stats
        }
    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear")
async def clear_cache(
    cache_type: str = "all"
) -> Dict[str, Any]:
    """
    清除缓存
    
    v0.5.0: 使用统一缓存系统
    
    Args:
        cache_type: 缓存类型 (hotspots/api/report/all)
    
    Returns:
        清除结果
    """
    try:
        cleared = {}
        
        if cache_type in ["hotspots", "all"]:
            HotSpotsCache.clear_cache()
            cleared["hotspots_cache"] = "已清理"
        
        if cache_type in ["api", "all"]:
            unified_cache.clear_api_cache()
            cleared["api_cache"] = "已清理"
        
        if cache_type in ["report", "all"]:
            unified_cache.clear_report_cache()
            cleared["report_cache"] = "已清理"
        
        logger.info(f"✅ 缓存清理完成: {cleared}")
        
        return {
            "success": True,
            "cleared": cleared
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
    
    v0.5.0: 使用统一缓存系统
    
    Returns:
        健康状态
    """
    try:
        stats = await get_cache_stats()
        
        # 统一缓存系统状态
        unified_regions = list(stats.get("unified_cache", {}).keys())
        
        return {
            "status": "healthy",
            "numpy_cache_mb": stats["numpy_cache"]["total_mb"],
            "hotspots_dates": stats["hotspots_cache"]["cached_dates"],
            "unified_cache_regions": unified_regions
        }
    
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


@router.post("/gc")
async def trigger_gc() -> Dict[str, Any]:
    """
    触发垃圾回收
    
    v0.6.0: 新增接口
    
    Returns:
        GC 结果
    """
    try:
        result = unified_cache.gc()
        logger.info(f"✅ GC 完成: {result}")
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        logger.error(f"GC 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
