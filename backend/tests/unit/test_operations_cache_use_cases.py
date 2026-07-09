from __future__ import annotations

from app.contexts.operations.application.cache_management import (
    ClearCacheUseCase,
    GetCacheHealthUseCase,
    GetCacheStatsUseCase,
    ReloadAllCacheUseCase,
    TriggerCacheGarbageCollectionUseCase,
)
from app.contexts.operations.application.commands import ClearCacheCommand


class FakeCacheManager:
    def __init__(self) -> None:
        self.cleared: list[str] = []
        self.reload_count = 0
        self.reload_targets: list[str] = []
        self.gc_count = 0
        self.unified_stats = {
            "api_response": {"entries": 3},
            "reports": {"entries": 1},
            "session_keys": {"active": 0, "metrics": {}},
            "stock_market": {"type": "vector", "total_mb": 12.5},
            "hot_spots": {"type": "logical_hotspots", "total_dates": 2},
        }
        self.region_specs = {
            "api_response": {
                "name": "api_response",
                "owner": "platform",
                "store_type": "FileStore",
                "policy": "DiskCache TTL",
                "ttl_seconds": 86400,
                "max_entries": None,
                "consistency": "stale reads allowed",
                "disposable": True,
                "clearable": True,
                "description": "API response cache.",
            },
            "reports": {
                "name": "reports",
                "owner": "platform",
                "store_type": "FileStore",
                "policy": "DiskCache TTL",
                "ttl_seconds": 86400,
                "max_entries": None,
                "consistency": "stale reads allowed",
                "disposable": True,
                "clearable": True,
                "description": "Report cache.",
            },
            "session_keys": {
                "name": "session_keys",
                "owner": "identity/security",
                "store_type": "ObjectStore",
                "policy": "WriteThroughPolicy",
                "ttl_seconds": 0,
                "max_entries": 10000,
                "consistency": "process-local strong",
                "disposable": False,
                "clearable": False,
                "description": "Runtime secure session keys.",
            },
            "stock_market": {
                "name": "stock_market",
                "owner": "market_data/analysis",
                "store_type": "VectorStore",
                "policy": "ReadOnly NumpyCache",
                "ttl_seconds": 0,
                "max_entries": None,
                "consistency": "read model snapshot",
                "disposable": True,
                "clearable": False,
                "description": "Logical market data read model.",
            },
            "hot_spots": {
                "name": "hot_spots",
                "owner": "analysis",
                "store_type": "HotSpotsStore",
                "policy": "HotSpotsCache TTL",
                "ttl_seconds": 90000,
                "max_entries": 30,
                "consistency": "stale reads allowed",
                "disposable": True,
                "clearable": True,
                "description": "Logical hot-spots cache.",
            },
        }

    def get_numpy_stats(self) -> dict:
        return {
            "total_mb": 12.5,
            "stocks_count": 100,
            "daily_data": {"n_records": 2000},
            "sector_data": {"n_records": 300},
        }

    def get_hotspots_stats(self) -> dict:
        return {
            "cached_dates": ["2026-07-07", "2026-07-08"],
            "memory_usage_kb": 64,
        }

    def get_unified_stats(self) -> dict:
        return self.unified_stats

    def get_region_specs(self) -> dict:
        return self.region_specs

    def clear_hotspots_cache(self) -> None:
        self.cleared.append("hotspots")

    def clear_api_cache(self) -> None:
        self.cleared.append("api")

    def clear_report_cache(self) -> None:
        self.cleared.append("report")

    def clear_region(self, region_name: str) -> None:
        self.cleared.append(f"region:{region_name}")

    def reload_all(self) -> None:
        self.reload_count += 1
        self.reload_targets.append("all")

    def reload_numpy_cache(self) -> None:
        self.reload_targets.append("numpy")

    def reload_hotspots_cache(self) -> None:
        self.reload_targets.append("hotspots")

    def reload_config_cache(self) -> None:
        self.reload_targets.append("config")

    def gc(self) -> dict:
        self.gc_count += 1
        return {"collected": 7}


def test_cache_stats_normalizes_platform_stats() -> None:
    result = GetCacheStatsUseCase(FakeCacheManager()).execute()

    assert result["numpy_cache"]["total_mb"] == 12.5
    assert result["numpy_cache"]["daily_records"] == 2000
    assert result["hotspots_cache"]["cached_dates"] == 2
    assert result["unified_cache"]["api_response"]["entries"] == 3
    assert result["region_specs"]["api_response"]["owner"] == "platform"
    assert result["cache_regions"]["api_response"]["registered"] is True
    assert result["cache_regions"]["session_keys"]["registered"] is True
    assert result["cache_regions"]["stock_market"]["registered"] is True
    assert result["cache_regions"]["hot_spots"]["spec"]["owner"] == "analysis"


def test_clear_cache_all_calls_each_cache_region() -> None:
    cache = FakeCacheManager()

    result = ClearCacheUseCase(cache).execute(ClearCacheCommand(cache_type="all"))

    assert result["success"] is True
    assert cache.cleared == ["hotspots", "api", "report"]
    assert result["cleared"] == {
        "hotspots_cache": "已清理",
        "api_cache": "已清理",
        "report_cache": "已清理",
    }


def test_clear_cache_keeps_legacy_empty_success_for_unknown_type() -> None:
    cache = FakeCacheManager()

    result = ClearCacheUseCase(cache).execute(ClearCacheCommand(cache_type="unknown"))

    assert result == {"success": True, "cleared": {}}
    assert cache.cleared == []


def test_clear_cache_region_clears_clearable_registered_region() -> None:
    cache = FakeCacheManager()

    result = ClearCacheUseCase(cache).execute(ClearCacheCommand(cache_type="region:api_response"))

    assert result == {"success": True, "cleared": {"region:api_response": "已清理"}}
    assert cache.cleared == ["region:api_response"]


def test_clear_cache_region_rejects_non_clearable_region() -> None:
    cache = FakeCacheManager()

    try:
        ClearCacheUseCase(cache).execute(ClearCacheCommand(cache_type="region:session_keys"))
    except ValueError as exc:
        assert "not clearable" in str(exc)
    else:
        raise AssertionError("Expected non-clearable region to be rejected")

    assert cache.cleared == []


def test_clear_cache_all_disposable_uses_registry() -> None:
    cache = FakeCacheManager()

    result = ClearCacheUseCase(cache).execute(ClearCacheCommand(cache_type="all_disposable"))

    assert result["success"] is True
    assert cache.cleared == ["region:api_response", "region:reports", "region:hot_spots"]
    assert "region:session_keys" not in result["cleared"]
    assert "region:stock_market" not in result["cleared"]


def test_cache_health_degrades_when_region_metrics_have_errors() -> None:
    cache = FakeCacheManager()
    cache.unified_stats = {
        "api_response": {
            "active": 1,
            "metrics": {
                "loader_errors": 0,
                "persister_errors": 0,
                "operation_errors": 1,
                "recoveries": 0,
            },
        },
        "reports": {"active": 0, "metrics": {}},
        "session_keys": {"active": 0, "metrics": {}},
        "stock_market": {"type": "vector"},
        "hot_spots": {"type": "logical_hotspots"},
    }

    result = GetCacheHealthUseCase(cache).execute()

    assert result["status"] == "degraded"
    assert result["warnings"] == ["region api_response has 1 cache errors"]
    assert result["regions"]["api_response"]["errors"] == 1


def test_reload_cache_supports_specific_targets() -> None:
    cache = FakeCacheManager()

    assert ReloadAllCacheUseCase(cache).execute(target="numpy")["target"] == "numpy"
    assert ReloadAllCacheUseCase(cache).execute(target="hotspots")["target"] == "hotspots"
    assert ReloadAllCacheUseCase(cache).execute(target="config")["target"] == "config"

    assert cache.reload_targets == ["numpy", "hotspots", "config"]


def test_reload_cache_rejects_unknown_target() -> None:
    cache = FakeCacheManager()

    try:
        ReloadAllCacheUseCase(cache).execute(target="unknown")
    except ValueError as exc:
        assert "Unsupported reload target" in str(exc)
    else:
        raise AssertionError("Expected unknown reload target to be rejected")

    assert cache.reload_targets == []


def test_reload_health_and_gc_use_platform_adapter_port() -> None:
    cache = FakeCacheManager()

    reload_result = ReloadAllCacheUseCase(cache).execute()
    health_result = GetCacheHealthUseCase(cache).execute()
    gc_result = TriggerCacheGarbageCollectionUseCase(cache).execute()

    assert reload_result["success"] is True
    assert reload_result["target"] == "all"
    assert cache.reload_count == 1
    assert cache.reload_targets == ["all"]
    assert health_result["status"] == "healthy"
    assert health_result["unified_cache_regions"] == [
        "api_response",
        "reports",
        "session_keys",
        "stock_market",
        "hot_spots",
    ]
    assert gc_result == {"success": True, "result": {"collected": 7}}
    assert cache.gc_count == 1
