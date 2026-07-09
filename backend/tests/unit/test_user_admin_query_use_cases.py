from datetime import timedelta

import pytest

from app.contexts.identity.application.queries import GetAdminUserDetailQuery, ListAdminUsersQuery
from app.contexts.identity.application.user_queries import GetAdminUserDetailUseCase, ListAdminUsersUseCase
from app.contexts.identity.infrastructure.repositories import SqlAlchemyIdentityUserQueryRepository
from app.db_models import User, UserSession
from app.shared.errors import AppError, ErrorCode
from app.shared.time import utc_now_naive


def _user(username: str, *, role: str = "user", deleted: bool = False) -> User:
    now = utc_now_naive()
    return User(
        username=username,
        password_hash="hashed",
        user_key_encrypted="encrypted-key",
        role=role,
        is_active=True,
        nickname=username.title(),
        email=f"{username}@example.test",
        deleted_at=now if deleted else None,
    )


def _session(
    user_id: int,
    device_id: str,
    *,
    last_active_delta: timedelta = timedelta(seconds=0),
    is_revoked: bool = False,
) -> UserSession:
    now = utc_now_naive()
    return UserSession(
        user_id=user_id,
        device_id=device_id,
        device_name=device_id.title(),
        session_key_encrypted=f"{device_id}-key",
        refresh_token=f"{device_id}-refresh",
        expires_at=now + timedelta(days=1),
        last_active=now - last_active_delta,
        is_revoked=is_revoked,
    )


def _repo(db_session):
    return SqlAlchemyIdentityUserQueryRepository(db_session)


def test_list_admin_users_excludes_deleted_and_counts_unrevoked_sessions(db_session):
    active = _user("alice", role="admin")
    deleted = _user("deleted", deleted=True)
    db_session.add_all([active, deleted])
    db_session.commit()
    db_session.refresh(active)
    db_session.add_all([
        _session(active.id, "desktop"),
        _session(active.id, "mobile", is_revoked=True),
    ])
    db_session.commit()

    result = ListAdminUsersUseCase(users=_repo(db_session)).execute(
        ListAdminUsersQuery(search="ali", role="admin")
    )

    assert result["total"] == 1
    assert result["items"][0]["username"] == "alice"
    assert result["items"][0]["active_sessions"] == 1


def test_get_admin_user_detail_returns_unrevoked_sessions_ordered_by_last_active(db_session):
    user = _user("alice")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    older = _session(user.id, "older", last_active_delta=timedelta(minutes=5))
    newer = _session(user.id, "newer", last_active_delta=timedelta(minutes=1))
    revoked = _session(user.id, "revoked", is_revoked=True)
    db_session.add_all([older, newer, revoked])
    db_session.commit()

    result = GetAdminUserDetailUseCase(users=_repo(db_session)).execute(
        GetAdminUserDetailQuery(user_id=user.id)
    )

    assert result["username"] == "alice"
    assert [session["device_id"] for session in result["sessions"]] == ["newer", "older"]


def test_get_admin_user_detail_missing_user_raises_not_found(db_session):
    with pytest.raises(AppError) as exc:
        GetAdminUserDetailUseCase(users=_repo(db_session)).execute(
            GetAdminUserDetailQuery(user_id=404)
        )

    assert exc.value.code == ErrorCode.NOT_FOUND
