from __future__ import annotations

import pytest

from app.contexts.operations.infrastructure import policy_engine
from app.contexts.operations.infrastructure.policy_engine import CachedPolicyProvider


class FakeCache:
    def __init__(self, values: dict) -> None:
        self.values = values

    def get_config(self, key: str):
        return self.values.get(key)


class UserWithDeviceLimit:
    allowed_devices = 9


def test_cached_policy_provider_reads_cache_and_user_override(monkeypatch) -> None:
    monkeypatch.setattr(
        policy_engine,
        "cache",
        FakeCache(
            {
                "login_max_attempts": "4",
                "login_lockout_minutes": "12",
                "session_max_devices": "3",
                "session_access_token_hours": "2",
                "session_refresh_token_days": "11",
            }
        ),
    )

    assert CachedPolicyProvider.get_login_policy() == {
        "max_attempts": 4,
        "lockout_minutes": 12,
    }
    assert CachedPolicyProvider.get_session_policy(UserWithDeviceLimit()) == {
        "max_devices": 9,
        "access_token_hours": 2,
        "refresh_token_days": 11,
    }


def test_cached_policy_provider_validates_password(monkeypatch) -> None:
    monkeypatch.setattr(
        policy_engine,
        "cache",
        FakeCache(
            {
                "password_min_length": "8",
                "password_require_digit": True,
                "password_require_upper": True,
                "password_require_lower": True,
                "password_require_special": True,
            }
        ),
    )

    with pytest.raises(ValueError) as exc:
        CachedPolicyProvider.validate_password("abcdefg")

    message = str(exc.value)
    assert "密码长度不能少于 8 位" in message
    assert "密码必须包含数字" in message
    assert "密码必须包含大写字母" in message
    assert "密码必须包含特殊字符" in message

    CachedPolicyProvider.validate_password("Abcdef1!")
