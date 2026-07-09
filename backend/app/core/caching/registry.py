"""Cache region ownership and runtime registration metadata."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CacheRegionSpec:
    name: str
    owner: str
    store_type: str
    policy: str
    ttl_seconds: int
    max_entries: int | None
    consistency: str
    disposable: bool
    clearable: bool
    description: str


DEFAULT_REGION_SPECS: tuple[CacheRegionSpec, ...] = (
    CacheRegionSpec(
        name="sessions",
        owner="identity",
        store_type="ObjectStore",
        policy="WriteBehindPolicy",
        ttl_seconds=0,
        max_entries=10000,
        consistency="eventual",
        disposable=True,
        clearable=True,
        description="Session heartbeat runtime state synced by the database syncer.",
    ),
    CacheRegionSpec(
        name="session_keys",
        owner="identity/security",
        store_type="ObjectStore",
        policy="WriteThroughPolicy",
        ttl_seconds=0,
        max_entries=10000,
        consistency="process-local strong",
        disposable=False,
        clearable=False,
        description="Runtime AES session keys used by /api/secure, keyed by user_id:device_id.",
    ),
    CacheRegionSpec(
        name="users",
        owner="identity",
        store_type="ObjectStore",
        policy="CacheAsidePolicy",
        ttl_seconds=3600,
        max_entries=10000,
        consistency="short stale reads allowed",
        disposable=True,
        clearable=True,
        description="User read cache with one-hour TTL.",
    ),
    CacheRegionSpec(
        name="config",
        owner="operations",
        store_type="ObjectStore",
        policy="WriteThroughPolicy",
        ttl_seconds=0,
        max_entries=1000,
        consistency="process-local strong",
        disposable=True,
        clearable=True,
        description="System config cache preloaded from the database and refreshed after config writes.",
    ),
    CacheRegionSpec(
        name="api_response",
        owner="platform",
        store_type="FileStore",
        policy="DiskCache TTL",
        ttl_seconds=86400,
        max_entries=None,
        consistency="stale reads allowed",
        disposable=True,
        clearable=True,
        description="Disk-backed API response cache, size-limited by FileStore.",
    ),
    CacheRegionSpec(
        name="reports",
        owner="platform",
        store_type="FileStore",
        policy="DiskCache TTL",
        ttl_seconds=86400,
        max_entries=None,
        consistency="stale reads allowed",
        disposable=True,
        clearable=True,
        description="Disk-backed generated report cache, size-limited by FileStore.",
    ),
    CacheRegionSpec(
        name="stock_market",
        owner="market_data/analysis",
        store_type="VectorStore",
        policy="ReadOnly NumpyCache",
        ttl_seconds=0,
        max_entries=None,
        consistency="read model snapshot, reload from database import data",
        disposable=True,
        clearable=False,
        description="Logical read-only region wrapping the legacy Numpy market data cache.",
    ),
    CacheRegionSpec(
        name="hot_spots",
        owner="analysis",
        store_type="HotSpotsStore",
        policy="HotSpotsCache TTL",
        ttl_seconds=90000,
        max_entries=30,
        consistency="stale reads allowed",
        disposable=True,
        clearable=True,
        description="Logical region wrapping the legacy 14-day aggregated hot-spots cache.",
    ),
)


def default_region_names() -> list[str]:
    return [spec.name for spec in DEFAULT_REGION_SPECS]


def default_region_specs_by_name() -> dict[str, CacheRegionSpec]:
    return {spec.name: spec for spec in DEFAULT_REGION_SPECS}
