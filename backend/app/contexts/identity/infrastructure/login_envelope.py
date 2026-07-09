"""Secure login hybrid encryption envelope."""

from __future__ import annotations

import base64
import json
import os
import time
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from ....core.security_settings import get_login_private_key_pem, get_login_public_key_id
from ....shared.replay_nonce_store import login_nonce_store


LOGIN_ENVELOPE_TTL_SECONDS = 300


class LoginEnvelopeError(ValueError):
    pass


class LoginEnvelopeReplayError(LoginEnvelopeError):
    pass


@dataclass(frozen=True, slots=True)
class LoginEnvelopeContext:
    key_id: str
    aes_key: bytes
    nonce: str
    timestamp: int

    @property
    def aad(self) -> bytes:
        return f"{self.key_id}:{self.timestamp}:{self.nonce}".encode("utf-8")


class LoginEnvelopeService:
    def __init__(self, private_key_pem: str | None = None, key_id: str | None = None) -> None:
        self.key_id = key_id or get_login_public_key_id()
        pem = (private_key_pem or get_login_private_key_pem()).encode("utf-8")
        self.private_key = serialization.load_pem_private_key(pem, password=None)

    def decrypt_request(self, envelope: Any) -> tuple[dict[str, Any], LoginEnvelopeContext]:
        key_id = envelope.key_id
        if key_id != self.key_id:
            raise LoginEnvelopeError("未知的登录公钥")

        timestamp = int(envelope.timestamp)
        now_ms = int(time.time() * 1000)
        if abs(now_ms - timestamp) > LOGIN_ENVELOPE_TTL_SECONDS * 1000:
            raise LoginEnvelopeError("登录请求已过期")

        aes_key = self.private_key.decrypt(
            base64.b64decode(envelope.encrypted_key),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        if len(aes_key) != 32:
            raise LoginEnvelopeError("登录信封密钥长度无效")

        context = LoginEnvelopeContext(
            key_id=key_id,
            aes_key=aes_key,
            nonce=envelope.nonce,
            timestamp=timestamp,
        )
        try:
            plaintext = AESGCM(aes_key).decrypt(
                base64.b64decode(envelope.iv),
                base64.b64decode(envelope.data),
                context.aad,
            )
        except Exception as exc:
            raise LoginEnvelopeError("登录信封解密失败") from exc

        nonce_key = f"login:{key_id}:{envelope.nonce}"
        if not login_nonce_store.mark_once(nonce_key, LOGIN_ENVELOPE_TTL_SECONDS):
            raise LoginEnvelopeReplayError("登录请求已被使用")

        try:
            payload = json.loads(plaintext.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise LoginEnvelopeError("登录载荷不是有效 JSON") from exc
        if not isinstance(payload, dict):
            raise LoginEnvelopeError("登录载荷格式无效")
        return payload, context

    def encrypt_response(self, payload: dict[str, Any], context: LoginEnvelopeContext) -> dict[str, str]:
        iv = os.urandom(12)
        ciphertext = AESGCM(context.aes_key).encrypt(
            iv,
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
            context.aad,
        )
        return {
            "iv": base64.b64encode(iv).decode("ascii"),
            "data": base64.b64encode(ciphertext).decode("ascii"),
        }
