"""Bootstrap helpers for the default project cache regions."""

from __future__ import annotations

from pathlib import Path

from .manager import UnifiedCache
from .policies import CacheAsidePolicy, WriteBehindPolicy, WriteThroughPolicy
from .registry import default_region_names, default_region_specs_by_name
from .store import FileStore, HotSpotsStore, ObjectStore, VectorStore


def init_default_cache_regions(base_dir: str | Path | None = None) -> list[str]:
    """Register the default process-local cache regions.

    Args:
        base_dir: Backend app directory. Defaults to ``backend/app``.

    Returns:
        Registered region names in runtime order.
    """

    app_dir = Path(base_dir) if base_dir is not None else Path(__file__).resolve().parents[2]
    specs = default_region_specs_by_name()

    UnifiedCache.register(
        "sessions",
        ObjectStore(
            "sessions",
            WriteBehindPolicy(ttl=0, sync_interval=10),
            max_entries=specs["sessions"].max_entries,
        ),
    )
    UnifiedCache.register(
        "session_keys",
        ObjectStore(
            "session_keys",
            WriteThroughPolicy(ttl=0),
            max_entries=specs["session_keys"].max_entries,
        ),
    )
    UnifiedCache.register(
        "users",
        ObjectStore(
            "users",
            CacheAsidePolicy(ttl=3600),
            max_entries=specs["users"].max_entries,
        ),
    )
    UnifiedCache.register(
        "config",
        ObjectStore(
            "config",
            WriteThroughPolicy(ttl=0),
            max_entries=specs["config"].max_entries,
        ),
    )
    UnifiedCache.register(
        "api_response",
        FileStore("api_response", cache_dir=str(app_dir / ".cache" / "api"), size_limit_gb=0.2),
    )
    UnifiedCache.register(
        "reports",
        FileStore("reports", cache_dir=str(app_dir / ".cache" / "reports"), size_limit_gb=0.5),
    )
    from ...services.hot_spots_cache import HotSpotsCache
    from ...services.numpy_cache_middleware import numpy_cache

    UnifiedCache.register(
        "stock_market",
        VectorStore(numpy_cache, name="stock_market"),
    )
    UnifiedCache.register(
        "hot_spots",
        HotSpotsStore(HotSpotsCache, name="hot_spots"),
    )

    registered = UnifiedCache.region_names()
    expected = default_region_names()
    if registered != expected:
        raise RuntimeError(f"Cache region registration drifted: expected={expected}, actual={registered}")
    return registered
