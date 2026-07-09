from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.dependencies import (
    get_current_user,
    get_session_key_by_user_id,
    set_session_key,
)
from app.auth.jwt_handler import create_access_token
from app.auth.password import hash_password
from app.db_models import User, UserSession
from app.routers.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    get_current_user_info,
    get_user_sessions,
    login,
    logout,
    logout_all_devices,
    change_password,
    refresh_token,
    register,
)


@pytest.fixture()
def active_user(db_session):
    user = User(
        username="auth_ttl_user",
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


@pytest.mark.asyncio
async def test_login_persists_session_for_refresh_lifecycle(
    db_session,
    active_user,
    session_policy,
):
    response = await login(
        LoginRequest(
            username=active_user.username,
            password="secret123",
            device_id="desktop",
            device_name="Desktop",
        ),
        db_session,
    )

    session = db_session.query(UserSession).filter_by(
        user_id=active_user.id,
        device_id="desktop",
    ).one()

    assert response.token
    assert response.refresh_token
    assert datetime.fromisoformat(response.expires_at) < datetime.utcnow() + timedelta(hours=2)
    assert session.expires_at > datetime.utcnow() + timedelta(days=session_policy["refresh_token_days"] - 1)
    assert session.is_revoked is False


@pytest.mark.asyncio
async def test_register_creates_user_with_encrypted_key(db_session):
    response = await register(
        RegisterRequest(username="new_identity_user", password="secret123"),
        db_session,
    )

    user = db_session.query(User).filter_by(username="new_identity_user").one()

    assert response.success is True
    assert response.user_id == user.id
    assert user.password_hash != "secret123"
    assert user.user_key_encrypted


@pytest.mark.asyncio
async def test_register_rejects_duplicate_username(db_session, active_user):
    with pytest.raises(HTTPException) as exc:
        await register(
            RegisterRequest(username=active_user.username, password="secret123"),
            db_session,
        )

    assert exc.value.status_code == 400
    assert exc.value.detail == "用户名已存在"


@pytest.mark.asyncio
async def test_refresh_does_not_shorten_database_session_expiry(
    db_session,
    active_user,
    session_policy,
):
    login_response = await login(
        LoginRequest(
            username=active_user.username,
            password="secret123",
            device_id="desktop",
        ),
        db_session,
    )
    session = db_session.query(UserSession).filter_by(
        user_id=active_user.id,
        device_id="desktop",
    ).one()
    original_session_expiry = session.expires_at

    refresh_response = await refresh_token(
        RefreshRequest(refresh_token=login_response.refresh_token),
        db_session,
    )
    db_session.refresh(session)

    assert refresh_response["token"]
    assert datetime.fromisoformat(refresh_response["expires_at"]) < datetime.utcnow() + timedelta(hours=2)
    assert session.expires_at == original_session_expiry


@pytest.mark.asyncio
async def test_get_current_user_rejects_revoked_session(db_session, active_user):
    session = UserSession(
        user_id=active_user.id,
        device_id="desktop",
        device_name="Desktop",
        session_key_encrypted="encrypted-session-key",
        refresh_token="refresh-token",
        expires_at=datetime.utcnow() + timedelta(days=1),
        is_revoked=True,
    )
    db_session.add(session)
    db_session.commit()

    token = create_access_token(
        active_user.id,
        "desktop",
        expires_hours=1,
        token_version=active_user.token_version,
    )
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials, db_session)

    assert exc.value.status_code == 401
    assert "会话" in exc.value.detail


@pytest.mark.asyncio
async def test_logout_revokes_current_device_only(db_session, active_user):
    desktop = UserSession(
        user_id=active_user.id,
        device_id="desktop",
        session_key_encrypted="desktop-key",
        refresh_token="desktop-refresh",
        expires_at=datetime.utcnow() + timedelta(days=1),
        is_revoked=False,
    )
    mobile = UserSession(
        user_id=active_user.id,
        device_id="mobile",
        session_key_encrypted="mobile-key",
        refresh_token="mobile-refresh",
        expires_at=datetime.utcnow() + timedelta(days=1),
        is_revoked=False,
    )
    db_session.add_all([desktop, mobile])
    db_session.commit()
    active_user._auth_payload = {"device": "desktop"}
    set_session_key(active_user.id, b"desktop-session", "desktop")
    set_session_key(active_user.id, b"mobile-session", "mobile")

    response = await logout(active_user, db_session)
    db_session.refresh(desktop)
    db_session.refresh(mobile)

    assert response["success"] is True
    assert desktop.is_revoked is True
    assert mobile.is_revoked is False
    assert get_session_key_by_user_id(active_user.id, "desktop") is None
    assert get_session_key_by_user_id(active_user.id, "mobile") == b"mobile-session"


@pytest.mark.asyncio
async def test_logout_all_devices_deletes_sessions_and_keys(db_session, active_user):
    sessions = [
        UserSession(
            user_id=active_user.id,
            device_id=device_id,
            session_key_encrypted=f"{device_id}-key",
            refresh_token=f"{device_id}-refresh",
            expires_at=datetime.utcnow() + timedelta(days=1),
            is_revoked=False,
        )
        for device_id in ("desktop", "mobile")
    ]
    db_session.add_all(sessions)
    db_session.commit()
    set_session_key(active_user.id, b"desktop-session", "desktop")
    set_session_key(active_user.id, b"mobile-session", "mobile")

    response = await logout_all_devices(active_user, db_session)

    assert response["success"] is True
    assert db_session.query(UserSession).filter_by(user_id=active_user.id).count() == 0
    assert get_session_key_by_user_id(active_user.id, "desktop") is None
    assert get_session_key_by_user_id(active_user.id, "mobile") is None


@pytest.mark.asyncio
async def test_change_password_updates_hash_and_clears_sessions(db_session, active_user):
    session = UserSession(
        user_id=active_user.id,
        device_id="desktop",
        session_key_encrypted="desktop-key",
        refresh_token="desktop-refresh",
        expires_at=datetime.utcnow() + timedelta(days=1),
        is_revoked=False,
    )
    db_session.add(session)
    db_session.commit()
    original_hash = active_user.password_hash
    set_session_key(active_user.id, b"desktop-session", "desktop")

    response = await change_password(
        ChangePasswordRequest(old_password="secret123", new_password="new-secret123"),
        active_user,
        db_session,
    )
    db_session.refresh(active_user)

    assert response["success"] is True
    assert active_user.password_hash != original_hash
    assert db_session.query(UserSession).filter_by(user_id=active_user.id).count() == 0
    assert get_session_key_by_user_id(active_user.id, "desktop") is None


@pytest.mark.asyncio
async def test_get_current_user_info_uses_identity_query(db_session, active_user):
    response = await get_current_user_info(active_user, db_session)

    assert response["id"] == active_user.id
    assert response["username"] == active_user.username


@pytest.mark.asyncio
async def test_get_user_sessions_lists_active_sessions(db_session, active_user):
    active = UserSession(
        user_id=active_user.id,
        device_id="desktop",
        device_name="Desktop",
        session_key_encrypted="desktop-key",
        refresh_token="desktop-refresh",
        expires_at=datetime.utcnow() + timedelta(days=1),
        is_revoked=False,
    )
    revoked = UserSession(
        user_id=active_user.id,
        device_id="mobile",
        device_name="Mobile",
        session_key_encrypted="mobile-key",
        refresh_token="mobile-refresh",
        expires_at=datetime.utcnow() + timedelta(days=1),
        is_revoked=True,
    )
    db_session.add_all([active, revoked])
    db_session.commit()

    response = await get_user_sessions(active_user, db_session)

    assert response["total"] == 1
    assert response["limit"] == active_user.allowed_devices
    assert response["sessions"][0]["device_id"] == "desktop"
