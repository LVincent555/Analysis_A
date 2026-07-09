"""Cache management adapter for platform cache implementations."""

from __future__ import annotations

from dataclasses import asdict

from ....core.caching import cache as unified_cache
from ....core.caching.manager import UnifiedCache
from ....core.caching.registry import default_region_specs_by_name
from ....core.startup import _preload_hotspots, preload_cache
from ....services.hot_spots_cache import HotSpotsCache
from ....services.numpy_cache_middleware import numpy_cache


class PlatformCacheManagementAdapter:
    def get_numpy_stats(self) -> dict:
        return numpy_cache.get_memory_stats()

    def get_hotspots_stats(self) -> dict:
        return HotSpotsCache.get_cache_stats()

    def get_unified_stats(self) -> dict:
        return unified_cache.stats()

    def get_region_specs(self) -> dict:
        return {name: asdict(spec) for name, spec in default_region_specs_by_name().items()}

    def clear_hotspots_cache(self) -> None:
        HotSpotsCache.clear_cache()

    def clear_api_cache(self) -> None:
        unified_cache.clear_api_cache()

    def clear_report_cache(self) -> None:
        unified_cache.clear_report_cache()

    def clear_region(self, region_name: str) -> None:
        region = UnifiedCache.get_region(region_name)
        clear = getattr(region, "clear", None)
        if not callable(clear):
            raise ValueError(f"Cache region '{region_name}' does not support clear")
        clear()

    def reload_all(self) -> None:
        preload_cache()

    def reload_numpy_cache(self) -> None:
        numpy_cache.reload(days=30)

    def reload_hotspots_cache(self) -> None:
        HotSpotsCache.clear_cache()
        _preload_hotspots(days=3)

    def reload_config_cache(self) -> None:
        from ....database import SessionLocal

        db = SessionLocal()
        try:
            unified_cache.reload_configs(db)
        finally:
            db.close()

    def gc(self) -> dict:
        return unified_cache.gc()
