from datetime import timedelta

import pytest

from app.contexts.identity.application.commands import (
    CleanupExpiredSessionsCommand,
    RevokeAdminSessionCommand,
    RevokeUserSessionsCommand,
)
from app.contexts.identity.application.queries import GetAdminSessionDetailQuery, ListAdminSessionsQuery
from app.contexts.identity.application.session_admin import (
    CleanupExpiredSessionsUseCase,
    GetAdminSessionDetailUseCase,
    ListAdminSessionsUseCase,
    RevokeAdminSessionUseCase,
    RevokeUserSessionsUseCase,
)
from app.contexts.identity.infrastructure.repositories import (
    SqlAlchemyIdentityAuditLogRepository,
    SqlAlchemyIdentitySessionRepository,
    SqlAlchemyIdentityUserRepository,
)
from app.db_models import OperationLog, User, UserSession
from app.shared.errors import AppError, ErrorCode
from app.shared.time import utc_now_naive


def _user(username: str, *, role: str = "user", token_version: int = 1) -> User:
    return User(
        username=username,
        password_hash="hashed",
        user_key_encrypted="encrypted-key",
        role=role,
        is_active=True,
        token_version=token_version,
    )


def _session(
    user_id: int,
    device_id: str,
    *,
    expires_delta: timedelta = timedelta(days=1),
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
        expires_at=now + expires_delta,
        last_active=now - last_active_delta,
        is_revoked=is_revoked,
        current_status="online",
    )


def _repositories(db_session):
    return (
        SqlAlchemyIdentityUserRepository(db_session),
        SqlAlchemyIdentitySessionRepository(db_session),
        SqlAlchemyIdentityAuditLogRepository(db_session),
    )


def test_list_admin_sessions_keeps_legacy_response_shape(db_session):
    user = _user("alice")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    db_session.add(_session(user.id, "desktop"))
    db_session.commit()

    _, sessions, _ = _repositories(db_session)
    result = ListAdminSessionsUseCase(sessions=sessions).execute(
        ListAdminSessionsQuery(page=1, page_size=20, username="ali")
    )

    assert result["total"] == 1
    assert result["page"] == 1
    assert result["page_size"] == 20
    assert result["items"][0]["username"] == "alice"
    assert result["items"][0]["status"] == "active"


def test_get_admin_session_detail_missing_raises_not_found(db_session):
    _, sessions, _ = _repositories(db_session)

    with pytest.raises(AppError) as exc:
        GetAdminSessionDetailUseCase(sessions=sessions).execute(
            GetAdminSessionDetailQuery(session_id=404)
        )

    assert exc.value.code == ErrorCode.NOT_FOUND


def test_revoke_admin_session_marks_session_and_records_audit(db_session):
    admin = _user("admin", role="admin")
    target = _user("target")
    db_session.add_all([admin, target])
    db_session.commit()
    db_session.refresh(admin)
    db_session.refresh(target)
    session = _session(target.id, "desktop")
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    _, sessions, audit_logs = _repositories(db_session)
    result = RevokeAdminSessionUseCase(
        sessions=sessions,
        audit_logs=audit_logs,
    ).execute(
        RevokeAdminSessionCommand(
            session_id=session.id,
            operator_id=admin.id,
            operator_name=admin.username,
            ip_address="127.0.0.1",
        )
    )
    db_session.refresh(session)

    assert result.success is True
    assert result.session_id == session.id
    assert session.is_revoked is True
    assert session.revoked_by == admin.id
    log = db_session.query(OperationLog).filter_by(action="session_revoke").one()
    assert log.target_id == session.id
    assert log.operator_id == admin.id


def test_revoke_user_sessions_exclude_current_preserves_current_session(db_session):
    admin = _user("admin", role="admin", token_version=3)
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    current = _session(admin.id, "desktop")
    other = _session(admin.id, "mobile")
    db_session.add_all([current, other])
    db_session.commit()
    db_session.refresh(current)
    db_session.refresh(other)

    users, sessions, audit_logs = _repositories(db_session)
    result = RevokeUserSessionsUseCase(
        users=users,
        sessions=sessions,
        audit_logs=audit_logs,
    ).execute(
        RevokeUserSessionsCommand(
            user_id=admin.id,
            operator_id=admin.id,
            operator_name=admin.username,
            exclude_current=True,
            current_session_id=current.id,
        )
    )
    db_session.refresh(admin)
    db_session.refresh(current)
    db_session.refresh(other)

    assert result.affected == 1
    assert current.is_revoked is False
    assert other.is_revoked is True
    assert admin.token_version == 3


def test_revoke_user_sessions_exclude_current_requires_current_session_id(db_session):
    admin = _user("admin", role="admin")
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    users, sessions, audit_logs = _repositories(db_session)
    with pytest.raises(AppError) as exc:
        RevokeUserSessionsUseCase(
            users=users,
            sessions=sessions,
            audit_logs=audit_logs,
        ).execute(
            RevokeUserSessionsCommand(
                user_id=admin.id,
                operator_id=admin.id,
                operator_name=admin.username,
                exclude_current=True,
                current_session_id=None,
            )
        )

    assert exc.value.code == ErrorCode.VALIDATION_ERROR


def test_cleanup_expired_sessions_deletes_only_old_rows(db_session):
    user = _user("alice")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    old_expired = _session(user.id, "old", expires_delta=timedelta(days=-45))
    recent_expired = _session(user.id, "recent", expires_delta=timedelta(days=-2))
    active = _session(user.id, "active")
    db_session.add_all([old_expired, recent_expired, active])
    db_session.commit()

    _, sessions, _ = _repositories(db_session)
    deleted = CleanupExpiredSessionsUseCase(sessions=sessions).execute(
        CleanupExpiredSessionsCommand(days=30)
    )

    remaining_devices = {
        row.device_id
        for row in db_session.query(UserSession).filter_by(user_id=user.id).all()
    }
    assert deleted == 1
    assert remaining_devices == {"recent", "active"}
