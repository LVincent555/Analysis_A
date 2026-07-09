"""Cache management routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from ....auth.dependencies import require_admin
from ....db_models import User
from ..application.cache_management import (
    ClearCacheUseCase,
    GetCacheHealthUseCase,
    GetCacheStatsUseCase,
    ReloadAllCacheUseCase,
    TriggerCacheGarbageCollectionUseCase,
)
from ..application.commands import ClearCacheCommand
from ..infrastructure.cache_management import PlatformCacheManagementAdapter

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/cache",
    tags=["cache"],
)


def _cache_manager() -> PlatformCacheManagementAdapter:
    return PlatformCacheManagementAdapter()


@router.get("/stats")
async def get_cache_stats(admin: User = Depends(require_admin)) -> dict[str, Any]:
    """Get cache statistics."""
    try:
        return GetCacheStatsUseCase(_cache_manager()).execute()
    except Exception as exc:
        logger.error("获取缓存统计失败: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/clear")
async def clear_cache(
    cache_type: str = "all",
    admin: User = Depends(require_admin),
) -> dict[str, Any]:
    """Clear cache by type."""
    try:
        result = ClearCacheUseCase(_cache_manager()).execute(ClearCacheCommand(cache_type=cache_type))
        logger.info("缓存清理完成: %s", result["cleared"])
        return result
    except ValueError as exc:
        logger.warning("缓存清理请求无效: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("清除缓存失败: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/reload")
async def reload_all_cache(
    target: str = "all",
    admin: User = Depends(require_admin),
) -> dict[str, Any]:
    """Reload all preload caches."""
    try:
        logger.info("开始重新加载缓存: %s", target)
        return ReloadAllCacheUseCase(_cache_manager()).execute(target=target)
    except ValueError as exc:
        logger.warning("缓存重载请求无效: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("重载缓存失败: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/health")
async def cache_health_check(admin: User = Depends(require_admin)) -> dict[str, Any]:
    """Check cache health."""
    try:
        return GetCacheHealthUseCase(_cache_manager()).execute()
    except Exception as exc:
        logger.error("健康检查失败: %s", exc)
        return {
            "status": "error",
            "error": str(exc),
        }


@router.post("/gc")
async def trigger_gc(admin: User = Depends(require_admin)) -> dict[str, Any]:
    """Trigger cache garbage collection."""
    try:
        result = TriggerCacheGarbageCollectionUseCase(_cache_manager()).execute()
        logger.info("GC 完成: %s", result["result"])
        return result
    except Exception as exc:
        logger.error("GC 失败: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
