"""Runtime security configuration helpers."""

from __future__ import annotations

import base64
import os

from dotenv import load_dotenv

from ..shared.runtime_state_store import get_runtime_state_backend

load_dotenv(encoding="utf-8-sig")


DEV_JWT_SECRET = "dev-only-jwt-secret-change-me-please-32chars"
DEV_MASTER_KEY = b"dev-master-key-32bytes-long!!!!!"
DEV_INTERNAL_GATEWAY_SECRET = "dev-internal-gateway-secret-32bytes!!"
DEV_LOGIN_PUBLIC_KEY_ID = "login-rsa-dev-2026-07"


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def allow_insecure_dev_keys() -> bool:
    return _truthy(os.getenv("ALLOW_INSECURE_DEV_KEYS"))


def require_secure_login() -> bool:
    return _truthy(os.getenv("REQUIRE_SECURE_LOGIN"))


def _normalize_pem(value: str) -> str:
    return value.replace("\\n", "\n").strip()


def _required_env(name: str, *, dev_value: str | None = None) -> str:
    value = os.getenv(name)
    if value:
        return value
    if dev_value is not None and allow_insecure_dev_keys():
        return dev_value
    if dev_value is None:
        raise RuntimeError(f"{name} is required. Set a real value in the runtime environment.")
    raise RuntimeError(
        f"{name} is required. Set a real value or explicitly set "
        "ALLOW_INSECURE_DEV_KEYS=true for local development only."
    )


def get_jwt_secret() -> str:
    secret = _required_env("JWT_SECRET_KEY", dev_value=DEV_JWT_SECRET)
    if len(secret.encode("utf-8")) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be at least 32 bytes.")
    return secret


def get_master_encryption_key() -> bytes:
    raw = os.getenv("MASTER_ENCRYPTION_KEY")
    if not raw:
        if allow_insecure_dev_keys():
            return DEV_MASTER_KEY
        raise RuntimeError(
            "MASTER_ENCRYPTION_KEY is required. It must be base64 for a 32-byte key."
        )

    try:
        key = base64.b64decode(raw)
    except Exception as exc:
        raise RuntimeError("MASTER_ENCRYPTION_KEY must be valid base64.") from exc
    if len(key) != 32:
        raise RuntimeError("MASTER_ENCRYPTION_KEY must decode to exactly 32 bytes.")
    return key


def get_login_private_key_pem() -> str:
    return _normalize_pem(_required_env("LOGIN_PRIVATE_KEY"))


def get_login_public_key_id() -> str:
    return _required_env("LOGIN_PUBLIC_KEY_ID")


def get_internal_gateway_secret() -> str:
    secret = _required_env("INTERNAL_GATEWAY_SECRET", dev_value=DEV_INTERNAL_GATEWAY_SECRET)
    if len(secret.encode("utf-8")) < 32:
        raise RuntimeError("INTERNAL_GATEWAY_SECRET must be at least 32 bytes.")
    return secret


def validate_runtime_security_config() -> None:
    get_jwt_secret()
    get_master_encryption_key()
    get_login_private_key_pem()
    get_login_public_key_id()
    get_internal_gateway_secret()
    backend = get_runtime_state_backend()
    if backend not in {"memory", "diskcache"}:
        raise RuntimeError(
            "EXPERIMENTAL_RUNTIME_STATE_BACKEND must be one of: memory, diskcache."
        )
