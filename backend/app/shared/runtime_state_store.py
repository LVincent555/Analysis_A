"""Experimental runtime state stores for multi-worker readiness.

The default backend is process-local memory. The diskcache backend is an
experimental same-host shared store for local multi-worker deployments.
"""

from __future__ import annotations

import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, Protocol


class RuntimeStateStore(Protocol):
    is_external: bool

    def set(self, namespace: str, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        ...

    def get(self, namespace: str, key: str) -> Any | None:
        ...

    def delete(self, namespace: str, key: str) -> None:
        ...

    def delete_prefix(self, namespace: str, prefix: str) -> None:
        ...

    def clear_namespace(self, namespace: str) -> None:
        ...

    def mark_once(self, namespace: str, key: str, ttl_seconds: int) -> bool:
        ...

    def close(self) -> None:
        ...


def get_runtime_state_backend() -> str:
    return os.getenv("EXPERIMENTAL_RUNTIME_STATE_BACKEND", "memory").strip().lower() or "memory"


def get_runtime_state_dir() -> str:
    default_dir = Path(tempfile.gettempdir()) / "stock_analysis_app_runtime_state"
    return os.getenv("RUNTIME_STATE_DIR", str(default_dir)).strip() or str(default_dir)


def _full_key(namespace: str, key: str) -> str:
    return f"{namespace}\x1f{key}"


class InMemoryRuntimeStateStore:
    is_external = False

    def __init__(self) -> None:
        self._items: dict[str, tuple[Any, float | None]] = {}
        self._lock = threading.RLock()

    def set(self, namespace: str, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        expires_at = time.time() + ttl_seconds if ttl_seconds else None
        with self._lock:
            self._purge_expired(time.time())
            self._items[_full_key(namespace, key)] = (value, expires_at)

    def get(self, namespace: str, key: str) -> Any | None:
        now = time.time()
        full_key = _full_key(namespace, key)
        with self._lock:
            self._purge_expired(now)
            item = self._items.get(full_key)
            return item[0] if item else None

    def delete(self, namespace: str, key: str) -> None:
        with self._lock:
            self._items.pop(_full_key(namespace, key), None)

    def delete_prefix(self, namespace: str, prefix: str) -> None:
        full_prefix = _full_key(namespace, prefix)
        with self._lock:
            for key in list(self._items.keys()):
                if key.startswith(full_prefix):
                    self._items.pop(key, None)

    def clear_namespace(self, namespace: str) -> None:
        full_prefix = _full_key(namespace, "")
        with self._lock:
            for key in list(self._items.keys()):
                if key.startswith(full_prefix):
                    self._items.pop(key, None)

    def mark_once(self, namespace: str, key: str, ttl_seconds: int) -> bool:
        now = time.time()
        full_key = _full_key(namespace, key)
        expires_at = now + ttl_seconds
        with self._lock:
            self._purge_expired(now)
            if full_key in self._items:
                return False
            self._items[full_key] = (True, expires_at)
            return True

    def close(self) -> None:
        return None

    def _purge_expired(self, now: float) -> None:
        expired = [
            key
            for key, (_, expires_at) in self._items.items()
            if expires_at is not None and expires_at <= now
        ]
        for key in expired:
            self._items.pop(key, None)


class DiskCacheRuntimeStateStore:
    is_external = True

    def __init__(self, directory: str) -> None:
        from diskcache import Cache

        self.directory = directory
        Path(directory).mkdir(parents=True, exist_ok=True)
        self._cache = Cache(directory=directory)

    def set(self, namespace: str, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        self._cache.set(_full_key(namespace, key), value, expire=ttl_seconds)

    def get(self, namespace: str, key: str) -> Any | None:
        return self._cache.get(_full_key(namespace, key))

    def delete(self, namespace: str, key: str) -> None:
        self._cache.delete(_full_key(namespace, key))

    def delete_prefix(self, namespace: str, prefix: str) -> None:
        full_prefix = _full_key(namespace, prefix)
        for key in list(self._cache.iterkeys()):
            if isinstance(key, str) and key.startswith(full_prefix):
                self._cache.delete(key)

    def clear_namespace(self, namespace: str) -> None:
        self.delete_prefix(namespace, "")

    def mark_once(self, namespace: str, key: str, ttl_seconds: int) -> bool:
        return bool(self._cache.add(_full_key(namespace, key), True, expire=ttl_seconds))

    def close(self) -> None:
        self._cache.close()


_runtime_state_store: RuntimeStateStore | None = None
_runtime_state_signature: tuple[str, str] | None = None


def get_runtime_state_store() -> RuntimeStateStore:
    global _runtime_state_signature, _runtime_state_store

    backend = get_runtime_state_backend()
    directory = get_runtime_state_dir()
    signature = (backend, directory)
    if _runtime_state_store is not None and _runtime_state_signature == signature:
        return _runtime_state_store

    if _runtime_state_store is not None:
        _runtime_state_store.close()

    if backend == "memory":
        _runtime_state_store = InMemoryRuntimeStateStore()
    elif backend == "diskcache":
        _runtime_state_store = DiskCacheRuntimeStateStore(directory)
    else:
        raise RuntimeError(
            "Unsupported EXPERIMENTAL_RUNTIME_STATE_BACKEND: "
            f"{backend}. Supported values: memory, diskcache."
        )
    _runtime_state_signature = signature
    return _runtime_state_store


def reset_runtime_state_store_for_tests() -> None:
    global _runtime_state_signature, _runtime_state_store

    if _runtime_state_store is not None:
        _runtime_state_store.close()
    _runtime_state_store = None
    _runtime_state_signature = None
