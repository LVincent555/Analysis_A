"""Session key storage adapter."""

from collections.abc import Iterable

from ....shared.runtime_state_store import get_runtime_state_store


SESSION_KEY_NAMESPACE = "session_keys"


def _cache_key(user_id: int, device_id: str = "default") -> str:
    return f"{user_id}:{device_id or 'default'}"


def _get_unified_cache_region():
    try:
        from ....core.caching.manager import UnifiedCache

        if UnifiedCache.has_region("session_keys"):
            return UnifiedCache.get_region("session_keys")
    except ImportError:
        pass
    return None


class UnifiedCacheSessionKeyStore:
    def __init__(self) -> None:
        self._fallback: dict[tuple[int, str], bytes] = {}

    @property
    def fallback(self) -> dict[tuple[int, str], bytes]:
        return self._fallback

    def _external_store(self):
        store = get_runtime_state_store()
        return store if store.is_external else None

    def set(self, user_id: int, session_key: bytes, device_id: str = "default") -> None:
        normalized_device_id = device_id or "default"
        runtime_store = self._external_store()
        if runtime_store is not None:
            runtime_store.set(SESSION_KEY_NAMESPACE, _cache_key(user_id, normalized_device_id), session_key)
            return

        store = _get_unified_cache_region()
        if store:
            store.set(_cache_key(user_id, normalized_device_id), {"session_key": session_key})
            return

        self._fallback[(user_id, normalized_device_id)] = session_key

    def get(self, user_id: int, device_id: str = "default") -> bytes | None:
        normalized_device_id = device_id or "default"
        runtime_store = self._external_store()
        if runtime_store is not None:
            value = runtime_store.get(SESSION_KEY_NAMESPACE, _cache_key(user_id, normalized_device_id))
            return value if isinstance(value, bytes) else None

        store = _get_unified_cache_region()
        if store:
            data = store.get(_cache_key(user_id, normalized_device_id))
            if data and isinstance(data, dict):
                return data.get("session_key")

        return self._fallback.get((user_id, normalized_device_id))

    def remove(self, user_id: int, device_id: str | None = None) -> None:
        runtime_store = self._external_store()
        if runtime_store is not None:
            if device_id is not None:
                runtime_store.delete(SESSION_KEY_NAMESPACE, _cache_key(user_id, device_id))
            else:
                runtime_store.delete_prefix(SESSION_KEY_NAMESPACE, f"{user_id}:")
            return

        store = _get_unified_cache_region()
        if store:
            if device_id is not None:
                store.delete(_cache_key(user_id, device_id))
            elif hasattr(store, "keys"):
                self._remove_user_keys_from_region(user_id, store.keys(), store.delete)

        if device_id is not None:
            self._fallback.pop((user_id, device_id or "default"), None)
            return

        for key in list(self._fallback.keys()):
            if key[0] == user_id:
                self._fallback.pop(key, None)

    @staticmethod
    def _remove_user_keys_from_region(user_id: int, keys: Iterable[str], delete) -> None:
        prefix = f"{user_id}:"
        for key in list(keys):
            if key.startswith(prefix):
                delete(key)


session_key_store = UnifiedCacheSessionKeyStore()
