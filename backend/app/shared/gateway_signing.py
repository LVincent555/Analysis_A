"""Internal secure gateway request signing."""

from __future__ import annotations

import hashlib
import hmac
import time
from collections.abc import Mapping

from ..core.security_settings import get_internal_gateway_secret


GATEWAY_HEADER = "x-secure-gateway"
GATEWAY_TS_HEADER = "x-secure-gateway-ts"
GATEWAY_SIG_HEADER = "x-secure-gateway-sig"
SIGNATURE_MAX_AGE_MS = 60_000


def body_hash(body: bytes | None) -> str:
    return hashlib.sha256(body or b"").hexdigest()


def gateway_signature(method: str, path: str, timestamp_ms: str, body_sha256: str) -> str:
    message = f"{method.upper()}\n{path}\n{timestamp_ms}\n{body_sha256}".encode("utf-8")
    secret = get_internal_gateway_secret().encode("utf-8")
    return hmac.new(secret, message, hashlib.sha256).hexdigest()


def build_internal_gateway_headers(method: str, path: str, body: bytes | None = None) -> dict[str, str]:
    timestamp_ms = str(int(time.time() * 1000))
    digest = body_hash(body)
    return {
        GATEWAY_HEADER: "1",
        GATEWAY_TS_HEADER: timestamp_ms,
        GATEWAY_SIG_HEADER: gateway_signature(method, path, timestamp_ms, digest),
    }


def verify_internal_gateway_headers(
    *,
    method: str,
    path: str,
    headers: Mapping[str, str],
    body: bytes | None = None,
) -> bool:
    if headers.get(GATEWAY_HEADER) != "1":
        return False

    timestamp_ms = headers.get(GATEWAY_TS_HEADER)
    signature = headers.get(GATEWAY_SIG_HEADER)
    if not timestamp_ms or not signature:
        return False

    try:
        timestamp_value = int(timestamp_ms)
    except ValueError:
        return False

    now_ms = int(time.time() * 1000)
    if abs(now_ms - timestamp_value) > SIGNATURE_MAX_AGE_MS:
        return False

    expected = gateway_signature(method, path, timestamp_ms, body_hash(body))
    return hmac.compare_digest(expected, signature)
