"""Replay nonce stores backed by the runtime state store."""

from __future__ import annotations

from .runtime_state_store import get_runtime_state_store


class InMemoryReplayNonceStore:
    """Backward-compatible replay nonce facade.

    The default runtime state backend is still process-local memory. When
    EXPERIMENTAL_RUNTIME_STATE_BACKEND=diskcache, this facade becomes a
    same-host shared replay store.
    """

    def __init__(self, namespace: str = "replay_nonce") -> None:
        self.namespace = namespace

    def clear(self) -> None:
        get_runtime_state_store().clear_namespace(self.namespace)

    def mark_once(self, key: str, ttl_seconds: int) -> bool:
        return get_runtime_state_store().mark_once(self.namespace, key, ttl_seconds)


login_nonce_store = InMemoryReplayNonceStore("login_nonce")
secure_nonce_store = InMemoryReplayNonceStore("secure_nonce")
