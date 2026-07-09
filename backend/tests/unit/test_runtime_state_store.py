from __future__ import annotations

import pytest

from app.auth.dependencies import get_session_key_by_user_id, remove_session_key, set_session_key
from app.contexts.identity.infrastructure.session_key_store import UnifiedCacheSessionKeyStore
from app.shared.replay_nonce_store import login_nonce_store, secure_nonce_store
from app.shared.runtime_state_store import get_runtime_state_store, reset_runtime_state_store_for_tests


def test_diskcache_runtime_state_is_shared_between_store_instances(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EXPERIMENTAL_RUNTIME_STATE_BACKEND", "diskcache")
    monkeypatch.setenv("RUNTIME_STATE_DIR", str(tmp_path / "runtime-state"))
    reset_runtime_state_store_for_tests()

    try:
        store = get_runtime_state_store()
        store.set("example", "key", {"value": 1})
        assert store.mark_once("nonce", "n1", 300)

        reset_runtime_state_store_for_tests()
        shared_store = get_runtime_state_store()

        assert shared_store.get("example", "key") == {"value": 1}
        assert not shared_store.mark_once("nonce", "n1", 300)
    finally:
        reset_runtime_state_store_for_tests()


def test_session_key_store_uses_experimental_diskcache_backend(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EXPERIMENTAL_RUNTIME_STATE_BACKEND", "diskcache")
    monkeypatch.setenv("RUNTIME_STATE_DIR", str(tmp_path / "runtime-state"))
    reset_runtime_state_store_for_tests()

    try:
        set_session_key(42, b"desktop-key", "desktop")

        assert UnifiedCacheSessionKeyStore().get(42, "desktop") == b"desktop-key"
        assert get_session_key_by_user_id(42, "desktop") == b"desktop-key"

        remove_session_key(42, "desktop")

        assert UnifiedCacheSessionKeyStore().get(42, "desktop") is None
    finally:
        reset_runtime_state_store_for_tests()


def test_replay_nonce_store_uses_namespaced_experimental_backend(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EXPERIMENTAL_RUNTIME_STATE_BACKEND", "diskcache")
    monkeypatch.setenv("RUNTIME_STATE_DIR", str(tmp_path / "runtime-state"))
    reset_runtime_state_store_for_tests()

    try:
        assert login_nonce_store.mark_once("same-nonce", 300)
        assert not login_nonce_store.mark_once("same-nonce", 300)
        assert secure_nonce_store.mark_once("same-nonce", 300)

        reset_runtime_state_store_for_tests()

        assert not login_nonce_store.mark_once("same-nonce", 300)
        assert not secure_nonce_store.mark_once("same-nonce", 300)
    finally:
        reset_runtime_state_store_for_tests()


def test_runtime_state_rejects_unknown_backend(monkeypatch) -> None:
    monkeypatch.setenv("EXPERIMENTAL_RUNTIME_STATE_BACKEND", "redis")
    reset_runtime_state_store_for_tests()

    try:
        with pytest.raises(RuntimeError, match="Unsupported EXPERIMENTAL_RUNTIME_STATE_BACKEND"):
            get_runtime_state_store()
    finally:
        reset_runtime_state_store_for_tests()
