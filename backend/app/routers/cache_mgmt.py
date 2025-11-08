"""
缓存管理API
提供缓存统计、清理等管理功能
"""
from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

from ..services.analysis_service_db import analysis_service_db
from ..services.industry_service_db import industry_service_db
from ..services.sector_service_db import sector_service_db
from ..services.stock_service_db import stock_service_db
from ..services.rank_jump_service_db import rank_jump_service_db
from ..services.steady_rise_service_db import steady_rise_service_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cache", tags=["cache"])


@router.get("/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """
    获取所有服务的缓存统计信息
    
    Returns:
        各服务的缓存统计
    """
    try:
        stats = {
            "analysis": analysis_service_db.cache.stats(),
            "industry": industry_service_db.cache.stats(),
            "sector": sector_service_db.cache.stats(),
            "stock": stock_service_db.cache.stats(),
            "rank_jump": {
                "total": len(rank_jump_service_db.cache),
                "active": len(rank_jump_service_db.cache)
            },
            "steady_rise": {
                "total": len(steady_rise_service_db.cache),
                "active": len(steady_rise_service_db.cache)
            }
        }
        
        # 计算总计
        total_keys = sum(s.get("total", 0) for s in stats.values())
        total_active = sum(s.get("active", 0) for s in stats.values())
        
        return {
            "services": stats,
            "summary": {
                "total_keys": total_keys,
                "active_keys": total_active
            }
        }
    except Exception as e:
        logger.error(f"获取缓存统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear")
async def clear_cache(
    service: str = None,
    pattern: str = None
) -> Dict[str, Any]:
    """
    清除缓存
    
    Args:
        service: 服务名称 (analysis/industry/sector/stock/rank_jump/steady_rise/all)
        pattern: 模式匹配（清除包含该字符串的key）
    
    Returns:
        清除结果
    """
    try:
        cleared = {}
        
        services_map = {
            "analysis": analysis_service_db,
            "industry": industry_service_db,
            "sector": sector_service_db,
            "stock": stock_service_db,
            "rank_jump": rank_jump_service_db,
            "steady_rise": steady_rise_service_db
        }
        
        if service and service != "all":
            # 清除指定服务
            if service not in services_map:
                raise HTTPException(status_code=400, detail=f"未知服务: {service}")
            
            svc = services_map[service]
            if hasattr(svc.cache, 'clear'):
                count = svc.cache.clear(pattern=pattern)
            else:
                # 旧版dict缓存
                if pattern:
                    svc.cache = {k: v for k, v in svc.cache.items() if pattern not in k}
                else:
                    svc.cache.clear()
                count = "unknown"
            
            cleared[service] = count
        else:
            # 清除所有服务
            for svc_name, svc in services_map.items():
                if hasattr(svc.cache, 'clear'):
                    count = svc.cache.clear(pattern=pattern)
                else:
                    if pattern:
                        svc.cache = {k: v for k, v in svc.cache.items() if pattern not in k}
                    else:
                        svc.cache.clear()
                    count = "unknown"
                cleared[svc_name] = count
        
        logger.info(f"✅ 缓存清理完成: {cleared}")
        
        return {
            "success": True,
            "cleared": cleared,
            "pattern": pattern
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清除缓存失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup-expired")
async def cleanup_expired_cache() -> Dict[str, Any]:
    """
    清理所有过期的缓存项
    
    Returns:
        清理结果
    """
    try:
        cleaned = {}
        
        services = [
            ("analysis", analysis_service_db),
            ("industry", industry_service_db),
            ("sector", sector_service_db),
            ("stock", stock_service_db)
        ]
        
        for svc_name, svc in services:
            if hasattr(svc.cache, 'cleanup_expired'):
                count = svc.cache.cleanup_expired()
                cleaned[svc_name] = count
        
        total_cleaned = sum(cleaned.values())
        
        logger.info(f"✅ 过期缓存清理完成: 共清理 {total_cleaned} 个")
        
        return {
            "success": True,
            "cleaned": cleaned,
            "total": total_cleaned
        }
    
    except Exception as e:
        logger.error(f"清理过期缓存失败: {e}")
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
        summary = stats["summary"]
        
        # 简单的健康评估
        status = "healthy"
        if summary["total_keys"] > 10000:
            status = "warning"  # 缓存项过多
        
        return {
            "status": status,
            "total_keys": summary["total_keys"],
            "active_keys": summary["active_keys"],
            "memory_usage": "估计 {}MB".format(summary["total_keys"] * 10 // 1024)
        }
    
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "status": "error",
            "error": str(e)
        }
