"""Cached policy provider owned by Operations."""

from __future__ import annotations

import logging
import time
from typing import Any

from ....core.caching import cache

logger = logging.getLogger(__name__)

_last_miss_log: dict[str, float] = {}


class CachedPolicyProvider:
    """Resolve runtime policies from the unified config cache."""

    @staticmethod
    def _cfg(key: str, default: Any = None) -> Any:
        value = cache.get_config(key)
        if value is not None:
            return value

        now = time.time()
        last_time = _last_miss_log.get(key, 0)
        if now - last_time > 60:
            logger.warning("[PolicyProvider] MISS '%s', using default=%r.", key, default)
            _last_miss_log[key] = now
        return default

    @classmethod
    def get_login_policy(cls) -> dict:
        return {
            "max_attempts": int(cls._cfg("login_max_attempts", 5)),
            "lockout_minutes": int(cls._cfg("login_lockout_minutes", 30)),
        }

    @classmethod
    def get_session_policy(cls, user) -> dict:
        global_max = int(cls._cfg("session_max_devices", 3))
        user_max = None
        if hasattr(user, "allowed_devices") and user.allowed_devices and user.allowed_devices > 0:
            user_max = user.allowed_devices

        return {
            "max_devices": user_max or global_max,
            "access_token_hours": int(cls._cfg("session_access_token_hours", 24)),
            "refresh_token_days": int(cls._cfg("session_refresh_token_days", 7)),
        }

    @classmethod
    def get_password_policy(cls) -> dict:
        return {
            "min_length": int(cls._cfg("password_min_length", 6)),
            "require_digit": cls._cfg("password_require_digit", False),
            "require_upper": cls._cfg("password_require_upper", False),
            "require_lower": cls._cfg("password_require_lower", False),
            "require_special": cls._cfg("password_require_special", False),
        }

    @classmethod
    def validate_password(cls, password: str) -> None:
        policy = cls.get_password_policy()
        errors: list[str] = []

        if len(password) < policy["min_length"]:
            errors.append(f"密码长度不能少于 {policy['min_length']} 位")
        if policy["require_digit"] and not any(char.isdigit() for char in password):
            errors.append("密码必须包含数字")
        if policy["require_upper"] and not any(char.isupper() for char in password):
            errors.append("密码必须包含大写字母")
        if policy["require_lower"] and not any(char.islower() for char in password):
            errors.append("密码必须包含小写字母")
        if policy["require_special"] and not any(not char.isalnum() for char in password):
            errors.append("密码必须包含特殊字符")

        if errors:
            raise ValueError("；".join(errors))
