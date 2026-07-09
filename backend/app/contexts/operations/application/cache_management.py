"""Cache management use cases."""

from __future__ import annotations

from .commands import ClearCacheCommand
from .ports import CacheManagementPort


def _combine_region_stats(region_specs: dict, unified_stats: dict) -> dict:
    regions = {}
    for name, spec in region_specs.items():
        regions[name] = {
            "registered": name in unified_stats,
            "spec": spec,
            "stats": unified_stats.get(name),
        }

    for name, stats in unified_stats.items():
        if name not in regions:
            regions[name] = {
                "registered": True,
                "spec": None,
                "stats": stats,
            }

    return regions


def _region_warning(name: str, region: dict) -> str | None:
    stats = region.get("stats") or {}
    if not region.get("registered"):
        return f"region {name} is not registered at runtime"

    metrics = stats.get("metrics") or {}
    error_count = (
        metrics.get("loader_errors", 0)
        + metrics.get("persister_errors", 0)
        + metrics.get("operation_errors", 0)
    )
    if error_count:
        return f"region {name} has {error_count} cache errors"

    if metrics.get("recoveries", 0):
        return f"region {name} has disk cache recoveries"

    max_entries = stats.get("max_entries")
    active = stats.get("active")
    if isinstance(max_entries, int) and max_entries > 0 and isinstance(active, int):
        if active / max_entries >= 0.9:
            return f"region {name} is above 90% capacity"

    dirty = stats.get("dirty")
    if isinstance(dirty, int) and dirty > 1000:
        return f"region {name} has dirty backlog: {dirty}"

    return None


class GetCacheStatsUseCase:
    def __init__(self, cache_manager: CacheManagementPort) -> None:
        self.cache_manager = cache_manager

    def execute(self) -> dict:
        numpy_stats = self.cache_manager.get_numpy_stats()
        hotspots_stats = self.cache_manager.get_hotspots_stats()
        unified_stats = self.cache_manager.get_unified_stats()
        region_specs = self.cache_manager.get_region_specs()

        return {
            "numpy_cache": {
                "total_mb": numpy_stats["total_mb"],
                "stocks_count": numpy_stats["stocks_count"],
                "daily_records": numpy_stats["daily_data"]["n_records"],
                "sector_records": numpy_stats["sector_data"]["n_records"],
            },
            "hotspots_cache": {
                "cached_dates": len(hotspots_stats["cached_dates"]),
                "memory_kb": hotspots_stats["memory_usage_kb"],
            },
            "unified_cache": unified_stats,
            "region_specs": region_specs,
            "cache_regions": _combine_region_stats(region_specs, unified_stats),
        }


class ClearCacheUseCase:
    def __init__(self, cache_manager: CacheManagementPort) -> None:
        self.cache_manager = cache_manager

    def execute(self, command: ClearCacheCommand) -> dict:
        cache_type = command.cache_type.strip()
        cleared: dict[str, str] = {}

        if cache_type == "all_disposable":
            specs = self.cache_manager.get_region_specs()
            if "hot_spots" not in specs:
                self.cache_manager.clear_hotspots_cache()
                cleared["hotspots_cache"] = "已清理"

            for name, spec in specs.items():
                if spec.get("disposable") and spec.get("clearable"):
                    self.cache_manager.clear_region(name)
                    cleared[f"region:{name}"] = "已清理"

            return {
                "success": True,
                "cleared": cleared,
            }

        if cache_type.startswith("region:"):
            region_name = cache_type.split(":", 1)[1].strip()
            if not region_name:
                raise ValueError("region cache_type requires a region name")

            specs = self.cache_manager.get_region_specs()
            spec = specs.get(region_name)
            if spec is None:
                raise ValueError(f"Unknown cache region: {region_name}")
            if not spec.get("clearable"):
                raise ValueError(f"Cache region is not clearable: {region_name}")

            self.cache_manager.clear_region(region_name)
            return {
                "success": True,
                "cleared": {f"region:{region_name}": "已清理"},
            }

        if cache_type in ["hotspots", "all"]:
            self.cache_manager.clear_hotspots_cache()
            cleared["hotspots_cache"] = "已清理"

        if cache_type in ["api", "all"]:
            self.cache_manager.clear_api_cache()
            cleared["api_cache"] = "已清理"

        if cache_type in ["report", "all"]:
            self.cache_manager.clear_report_cache()
            cleared["report_cache"] = "已清理"

        return {
            "success": True,
            "cleared": cleared,
        }


class ReloadAllCacheUseCase:
    def __init__(self, cache_manager: CacheManagementPort) -> None:
        self.cache_manager = cache_manager

    def execute(self, target: str = "all") -> dict:
        target = target.strip().lower()
        reloaders = {
            "all": self.cache_manager.reload_all,
            "numpy": self.cache_manager.reload_numpy_cache,
            "stock_market": self.cache_manager.reload_numpy_cache,
            "hotspots": self.cache_manager.reload_hotspots_cache,
            "config": self.cache_manager.reload_config_cache,
        }
        reloader = reloaders.get(target)
        if reloader is None:
            raise ValueError(f"Unsupported reload target: {target}")

        reloader()
        return {
            "success": True,
            "target": target,
            "message": "缓存已重新加载" if target != "all" else "所有缓存已重新加载",
        }


class GetCacheHealthUseCase:
    def __init__(self, cache_manager: CacheManagementPort) -> None:
        self.stats_use_case = GetCacheStatsUseCase(cache_manager)

    def execute(self) -> dict:
        stats = self.stats_use_case.execute()
        warnings = [
            warning
            for name, region in stats.get("cache_regions", {}).items()
            if (warning := _region_warning(name, region))
        ]
        return {
            "status": "degraded" if warnings else "healthy",
            "warnings": warnings,
            "numpy_cache_mb": stats["numpy_cache"]["total_mb"],
            "hotspots_dates": stats["hotspots_cache"]["cached_dates"],
            "unified_cache_regions": list(stats.get("unified_cache", {}).keys()),
            "region_count": len(stats.get("cache_regions", {})),
            "regions": {
                name: {
                    "registered": region.get("registered"),
                    "owner": (region.get("spec") or {}).get("owner"),
                    "policy": (region.get("spec") or {}).get("policy"),
                    "active": (region.get("stats") or {}).get("active"),
                    "dirty": (region.get("stats") or {}).get("dirty"),
                    "errors": sum(
                        ((region.get("stats") or {}).get("metrics") or {}).get(key, 0)
                        for key in ("loader_errors", "persister_errors", "operation_errors")
                    ),
                }
                for name, region in stats.get("cache_regions", {}).items()
            },
        }


class TriggerCacheGarbageCollectionUseCase:
    def __init__(self, cache_manager: CacheManagementPort) -> None:
        self.cache_manager = cache_manager

    def execute(self) -> dict:
        return {
            "success": True,
            "result": self.cache_manager.gc(),
        }
