from __future__ import annotations

import base64
import json
import os
import time

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException
from starlette.requests import Request

from app.auth.password import hash_password
from app.contexts.identity.api.auth_router import secure_login, secure_refresh_token
from app.contexts.identity.api.schemas import SecureLoginRequest
from app.core import security_settings
from app.db_models import User
from app.middleware.auth_middleware import AuthMiddleware
from app.shared.gateway_signing import build_internal_gateway_headers, verify_internal_gateway_headers
from app.shared.replay_nonce_store import login_nonce_store, secure_nonce_store


DEV_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
DEV_PRIVATE_KEY_PEM = DEV_PRIVATE_KEY.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
).decode("ascii")
DEV_PUBLIC_KEY_PEM = DEV_PRIVATE_KEY.public_key().public_bytes(
    serialization.Encoding.PEM,
    serialization.PublicFormat.SubjectPublicKeyInfo,
)


@pytest.fixture(autouse=True)
def install_dev_login_key(monkeypatch):
    monkeypatch.setenv("LOGIN_PRIVATE_KEY", DEV_PRIVATE_KEY_PEM)
    monkeypatch.setenv("LOGIN_PUBLIC_KEY_ID", security_settings.DEV_LOGIN_PUBLIC_KEY_ID)
    login_nonce_store.clear()
    secure_nonce_store.clear()
    yield
    login_nonce_store.clear()
    secure_nonce_store.clear()


@pytest.fixture()
def secure_user(db_session):
    user = User(
        username="secure_login_user",
        password_hash=hash_password("secret123"),
        user_key_encrypted="test-user-key",
        is_active=True,
        allowed_devices=2,
        token_version=1,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_secure_login_request(payload: dict, *, nonce: str = "nonce-1", timestamp: int | None = None):
    public_key = serialization.load_pem_public_key(DEV_PUBLIC_KEY_PEM)
    aes_key = os.urandom(32)
    iv = os.urandom(12)
    timestamp = timestamp or int(time.time() * 1000)
    key_id = security_settings.DEV_LOGIN_PUBLIC_KEY_ID
    aad = f"{key_id}:{timestamp}:{nonce}".encode("utf-8")
    encrypted_key = public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    encrypted_payload = AESGCM(aes_key).encrypt(
        iv,
        json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        aad,
    )
    return SecureLoginRequest(
        key_id=key_id,
        encrypted_key=base64.b64encode(encrypted_key).decode("ascii"),
        iv=base64.b64encode(iv).decode("ascii"),
        nonce=nonce,
        timestamp=timestamp,
        data=base64.b64encode(encrypted_payload).decode("ascii"),
    ), aes_key, aad


def _decrypt_secure_login_response(response, aes_key: bytes, aad: bytes) -> dict:
    plaintext = AESGCM(aes_key).decrypt(
        base64.b64decode(response.iv),
        base64.b64decode(response.data),
        aad,
    )
    return json.loads(plaintext.decode("utf-8"))


def test_gateway_signature_accepts_internal_request():
    body = b'{"ok":true}'
    headers = build_internal_gateway_headers("POST", "/api/example", body)

    assert verify_internal_gateway_headers(
        method="POST",
        path="/api/example",
        headers=headers,
        body=body,
    )
    assert not verify_internal_gateway_headers(
        method="POST",
        path="/api/example",
        headers=headers,
        body=b'{"ok":false}',
    )


@pytest.mark.asyncio
async def test_auth_middleware_rejects_spoofed_secure_gateway_header(monkeypatch):
    monkeypatch.setattr("app.middleware.auth_middleware.FORCE_SECURE_API", True)
    middleware = AuthMiddleware(app=None)
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/admin/users",
        "headers": [(b"x-secure-gateway", b"1")],
        "query_string": b"",
        "server": ("testserver", 80),
        "scheme": "http",
        "client": ("testclient", 123),
    }
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    request = Request(scope, receive=receive)

    async def call_next(_request):
        raise AssertionError("spoofed gateway request should not pass")

    response = await middleware.dispatch(request, call_next)

    assert response.status_code == 403


def test_security_settings_require_explicit_dev_fallback(monkeypatch):
    monkeypatch.delenv("ALLOW_INSECURE_DEV_KEYS", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError):
        security_settings.get_jwt_secret()

    monkeypatch.setenv("ALLOW_INSECURE_DEV_KEYS", "true")

    assert security_settings.get_jwt_secret() == security_settings.DEV_JWT_SECRET


@pytest.mark.asyncio
async def test_secure_login_returns_encrypted_response(db_session, secure_user, session_policy):
    req, aes_key, aad = _make_secure_login_request(
        {
            "username": secure_user.username,
            "password": "secret123",
            "device_id": "desktop",
            "device_name": "Desktop",
        }
    )

    response = await secure_login(req, db_session)
    data = _decrypt_secure_login_response(response, aes_key, aad)

    assert data["token"]
    assert data["refresh_token"]
    assert data["session_key"]
    assert data["user"]["username"] == secure_user.username


@pytest.mark.asyncio
async def test_secure_login_rejects_replayed_nonce(db_session, secure_user, session_policy):
    req, _, _ = _make_secure_login_request(
        {
            "username": secure_user.username,
            "password": "secret123",
            "device_id": "desktop",
        },
        nonce="repeat-nonce",
    )

    await secure_login(req, db_session)
    with pytest.raises(HTTPException) as exc:
        await secure_login(req, db_session)

    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_secure_refresh_returns_encrypted_access_token(db_session, secure_user, session_policy):
    login_req, login_key, login_aad = _make_secure_login_request(
        {
            "username": secure_user.username,
            "password": "secret123",
            "device_id": "desktop",
        },
        nonce="login-for-refresh",
    )
    login_response = await secure_login(login_req, db_session)
    login_data = _decrypt_secure_login_response(login_response, login_key, login_aad)

    refresh_req, refresh_key, refresh_aad = _make_secure_login_request(
        {"refresh_token": login_data["refresh_token"]},
        nonce="refresh-nonce",
    )
    refresh_response = await secure_refresh_token(refresh_req, db_session)
    refresh_data = _decrypt_secure_login_response(refresh_response, refresh_key, refresh_aad)

    assert refresh_data["token"]
    assert refresh_data["expires_at"]
