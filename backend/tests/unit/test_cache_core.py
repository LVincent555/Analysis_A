from __future__ import annotations

import time
import tempfile
import shutil
from pathlib import Path

import pytest

from app.core.caching import cache
from app.core.caching.bootstrap import init_default_cache_regions
from app.core.caching.entry import CacheEntry
from app.core.caching.facade import KeyBuilder, safe_cache_call
from app.core.caching.manager import UnifiedCache
from app.core.caching.policies import CacheAsidePolicy, WriteBehindPolicy, WriteThroughPolicy
from app.core.caching.registry import default_region_names, default_region_specs_by_name
from app.core.caching.store import FileStore, HotSpotsStore, ObjectStore
from app.core.caching.syncer import DatabaseSyncer


@pytest.fixture(autouse=True)
def reset_unified_cache():
    UnifiedCache._regions.clear()
    UnifiedCache._initialized = False
    yield
    UnifiedCache._regions.clear()
    UnifiedCache._initialized = False


def test_cache_entry_ttl_dirty_and_slots() -> None:
    entry = CacheEntry("value", ttl=1, version=2)

    assert entry.value == "value"
    assert entry.version == 2
    assert not entry.is_expired()
    assert not entry.is_dirty
    assert not entry.is_stale(2)
    assert entry.is_stale(3)

    entry.mark_dirty()
    assert entry.is_dirty
    entry.clear_dirty()
    assert not entry.is_dirty

    with pytest.raises(AttributeError):
        entry.random_attr = "not allowed"  # type: ignore[attr-defined]


def test_write_behind_policy_tracks_dirty_keys() -> None:
    policy = WriteBehindPolicy(ttl=60)
    store = {}

    policy.set("k1", "v1", store)
    policy.set("k2", "v2", store)

    assert store["k1"].is_dirty
    assert policy.has_dirty()
    assert policy.peek_dirty_keys() == {"k1", "k2"}
    assert policy.get_dirty_keys() == {"k1", "k2"}
    assert policy.has_dirty()

    policy.ack_dirty_keys({"k1"})
    assert policy.peek_dirty_keys() == {"k2"}

    policy.requeue_dirty_keys({"k1"})
    assert policy.peek_dirty_keys() == {"k1", "k2"}

    policy.ack_dirty_keys({"k1", "k2"})
    assert not policy.has_dirty()


def test_write_through_persister_failure_does_not_mutate_cache() -> None:
    store = ObjectStore("config", WriteThroughPolicy(ttl=0))
    store.set("theme", "old")

    def broken_persister(value):
        raise RuntimeError("database unavailable")

    with pytest.raises(RuntimeError, match="database unavailable"):
        store.set("theme", "new", persister=broken_persister)

    assert store.get("theme") == "old"
    stats = store.stats()
    assert stats["metrics"]["sets"] == 1
    assert stats["metrics"]["persister_errors"] == 1
    assert stats["metrics"]["operation_errors"] == 1


def test_write_through_persister_success_updates_cache_after_persisting() -> None:
    store = ObjectStore("config", WriteThroughPolicy(ttl=0))
    persisted = []

    def persister(value):
        assert store.size() == 0
        persisted.append(value)

    store.set("theme", "new", persister=persister)

    assert persisted == ["new"]
    assert store.get("theme") == "new"


def test_cache_aside_loader_failure_records_metrics_and_returns_none() -> None:
    store = ObjectStore("users", CacheAsidePolicy(ttl=60))

    def broken_loader():
        raise RuntimeError("source failed")

    assert store.get("42", loader=broken_loader) is None

    stats = store.stats()
    assert stats["metrics"]["misses"] == 1
    assert stats["metrics"]["loader_errors"] == 1
    assert stats["metrics"]["operation_errors"] == 0


def test_database_syncer_keeps_session_dirty_keys_when_bulk_update_fails(monkeypatch) -> None:
    store = ObjectStore("sessions", WriteBehindPolicy(ttl=0))
    UnifiedCache.register("sessions", store)
    store.set("1", {"last_active": time.time(), "status": 1, "ip_address": "127.0.0.1"})

    syncer = DatabaseSyncer(sync_interval=1)
    monkeypatch.setattr(syncer, "_bulk_update_sessions", lambda mappings: False)

    syncer._sync_sessions()

    policy = store.policy
    assert isinstance(policy, WriteBehindPolicy)
    assert policy.peek_dirty_keys() == {"1"}
    assert store.store["1"].is_dirty


def test_database_syncer_acks_session_dirty_keys_after_bulk_update_success(monkeypatch) -> None:
    store = ObjectStore("sessions", WriteBehindPolicy(ttl=0))
    UnifiedCache.register("sessions", store)
    store.set("1", {"last_active": time.time(), "status": 2, "ip_address": "127.0.0.1"})
    captured_mappings = []

    def bulk_update(mappings):
        captured_mappings.extend(mappings)
        return True

    syncer = DatabaseSyncer(sync_interval=1)
    monkeypatch.setattr(syncer, "_bulk_update_sessions", bulk_update)

    syncer._sync_sessions()

    policy = store.policy
    assert isinstance(policy, WriteBehindPolicy)
    assert captured_mappings[0]["id"] == 1
    assert captured_mappings[0]["current_status"] == "idle"
    assert not policy.has_dirty()
    assert not store.store["1"].is_dirty


def test_cache_aside_policy_loads_and_invalidates() -> None:
    policy = CacheAsidePolicy(ttl=60)
    store = {}
    calls = 0

    def loader():
        nonlocal calls
        calls += 1
        return "loaded"

    assert policy.get("key", store, loader=loader) == "loaded"
    assert policy.get("key", store, loader=lambda: "changed") == "loaded"
    assert calls == 1

    policy.set("key", "new", store)
    assert "key" not in store


def test_object_store_basic_stats_and_expiration() -> None:
    store = ObjectStore("test", WriteBehindPolicy(ttl=1))

    store.set("k1", "v1")
    assert store.get("k1") == "v1"
    stats = store.stats()
    assert stats["total"] == 1
    assert stats["metrics"]["sets"] == 1
    assert stats["metrics"]["hits"] == 1

    store.store["k1"].expire_at = time.time() - 1
    assert store.get("k1") is None
    assert store.size() == 0
    assert store.stats()["metrics"]["misses"] == 1


def test_object_store_max_entries_evicts_lru_entry() -> None:
    store = ObjectStore("bounded", WriteThroughPolicy(ttl=0), max_entries=2)

    store.set("a", "A")
    time.sleep(0.01)
    store.set("b", "B")
    time.sleep(0.01)
    assert store.get("a") == "A"
    time.sleep(0.01)
    store.set("c", "C")

    assert store.get("a") == "A"
    assert store.get("b") is None
    assert store.get("c") == "C"

    stats = store.stats()
    assert stats["total"] == 2
    assert stats["max_entries"] == 2
    assert stats["eviction_policy"] == "lru"
    assert stats["metrics"]["evictions"] == 1
    assert stats["metrics"]["sets"] == 3


def test_default_cache_bootstrap_matches_registry() -> None:
    registered = init_default_cache_regions(Path("app"))
    specs = default_region_specs_by_name()

    assert registered == default_region_names()
    assert set(registered) == set(specs)
    assert UnifiedCache.has_region("session_keys")
    assert UnifiedCache.has_region("stock_market")
    assert UnifiedCache.has_region("hot_spots")
    assert UnifiedCache.get_region("config").policy.__class__ is WriteThroughPolicy
    assert UnifiedCache.get_region("sessions").max_entries == specs["sessions"].max_entries
    assert UnifiedCache.get_region("config").max_entries == specs["config"].max_entries
    assert UnifiedCache.get_region("stock_market").stats()["type"] == "vector"
    assert UnifiedCache.get_region("hot_spots").stats()["type"] == "logical_hotspots"
    assert UnifiedCache.stats().keys() == specs.keys()


def test_hot_spots_store_wraps_legacy_cache() -> None:
    class FakeHotSpotsCache:
        _ttl = 90000
        _max_days = 30
        _cache = {"20260709": {"data": [{"code": "600000"}]}}
        calls = []

        @classmethod
        def get_full_data(cls, date: str):
            cls.calls.append(f"get:{date}")
            return cls._cache.get(date, {}).get("data", [])

        @classmethod
        def get_cache_stats(cls):
            return {
                "cached_dates": sorted(cls._cache.keys()),
                "total_dates": len(cls._cache),
                "memory_usage_kb": 12.5,
            }

        @classmethod
        def clear_cache(cls):
            cls.calls.append("clear")
            cls._cache.clear()

        @classmethod
        def preload_recent_dates(cls, days: int = 3):
            cls.calls.append(f"reload:{days}")

    store = HotSpotsStore(FakeHotSpotsCache)

    assert store.get("20260709") == [{"code": "600000"}]
    assert store.stats()["total_dates"] == 1
    assert store.delete("20260709") is True
    assert store.delete("20260709") is False

    FakeHotSpotsCache._cache["20260708"] = {"data": []}
    store.clear()
    store.reload(days=5)

    assert FakeHotSpotsCache.calls == ["get:20260709", "clear", "clear", "reload:5"]


def test_public_cache_config_uses_current_write_through_policy() -> None:
    UnifiedCache.register("config", ObjectStore("config", WriteThroughPolicy(ttl=0)))

    cache.set_config("app_name", "StockAnalysis")

    assert cache.get_config("app_name") == "StockAnalysis"


def test_public_cache_user_cache_aside_and_invalidation() -> None:
    UnifiedCache.register("users", ObjectStore("users", CacheAsidePolicy(ttl=60)))

    assert cache.get_user(100, loader=lambda: {"id": 100, "name": "TestUser"}) == {
        "id": 100,
        "name": "TestUser",
    }
    assert cache.get_user(100, loader=lambda: {"id": 100, "name": "Changed"}) == {
        "id": 100,
        "name": "TestUser",
    }

    cache.invalidate_user(100)
    assert cache.get_user(100, loader=lambda: {"id": 100, "name": "Changed"}) == {
        "id": 100,
        "name": "Changed",
    }


def test_file_store_basic_operations() -> None:
    cache_dir = tempfile.mkdtemp(prefix="stock-cache-test-")
    store = FileStore("test_api", cache_dir, size_limit_gb=0.01)

    try:
        store.set("key1", {"data": "value1"}, ttl=60)

        assert store.get("key1") == {"data": "value1"}
        assert store.delete("key1") is True
        assert store.get("key1") is None
        stats = store.stats()
        assert stats["type"] == "disk"
        assert stats["metrics"]["sets"] == 1
        assert stats["metrics"]["hits"] == 1
        assert stats["metrics"]["deletes"] == 1
    finally:
        store.close()
        shutil.rmtree(cache_dir, ignore_errors=True)


def test_key_builder_and_safe_cache_call() -> None:
    assert KeyBuilder.api("daily", "abc123") == "api:daily:abc123"
    assert KeyBuilder.hotspot("2024-01-15") == "hotspot:2024-01-15"

    @safe_cache_call(default_return="fallback")
    def broken():
        raise RuntimeError("cache failed")

    assert broken() == "fallback"
