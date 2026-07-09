import json
from datetime import timedelta

import pytest

from app.contexts.identity.application.commands import (
    BatchAdminUsersCommand,
    CreateAdminUserCommand,
    DeleteAdminUserCommand,
    ResetAdminUserPasswordCommand,
    ToggleAdminUserStatusCommand,
    UnlockAdminUserCommand,
    UpdateAdminUserCommand,
)
from app.contexts.identity.application.user_commands import (
    BatchAdminUsersUseCase,
    CreateAdminUserUseCase,
    DeleteAdminUserUseCase,
    ResetAdminUserPasswordUseCase,
    ToggleAdminUserStatusUseCase,
    UnlockAdminUserUseCase,
    UpdateAdminUserUseCase,
)
from app.contexts.identity.infrastructure.repositories import (
    SqlAlchemyIdentityAuditLogRepository,
    SqlAlchemyIdentityUserCommandRepository,
)
from app.db_models import OperationLog, Role, User, UserSession, user_roles
from app.shared.errors import AppError, ErrorCode
from app.shared.time import utc_now_naive


class FastPasswordHasher:
    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, password: str, hashed: str) -> bool:
        return hashed == f"hashed:{password}"


class FakeCryptoProvider:
    def generate_key(self) -> bytes:
        return b"user-key"

    def encrypt_user_key(self, user_key: bytes) -> str:
        return f"encrypted:{user_key.decode()}"

    def encrypt_session_key_with_password(self, password: str, session_key: bytes) -> str:
        return "encrypted-session-key"


def _user(username: str, *, role: str = "user", token_version: int = 1) -> User:
    return User(
        username=username,
        password_hash="hashed",
        user_key_encrypted="encrypted-key",
        role=role,
        is_active=True,
        token_version=token_version,
    )


def _role(name: str) -> Role:
    return Role(
        name=name,
        display_name=name.title(),
        description=f"{name} role",
        permissions="[]",
        is_active=True,
        is_system=False,
    )


def _session(user_id: int, device_id: str, *, is_revoked: bool = False) -> UserSession:
    now = utc_now_naive()
    return UserSession(
        user_id=user_id,
        device_id=device_id,
        session_key_encrypted=f"{device_id}-key",
        refresh_token=f"{device_id}-refresh",
        expires_at=now + timedelta(days=1),
        is_revoked=is_revoked,
    )


def _components(db_session):
    return (
        SqlAlchemyIdentityUserCommandRepository(db_session),
        SqlAlchemyIdentityAuditLogRepository(db_session),
    )


def test_create_admin_user_maps_role_syncs_user_roles_and_records_audit(db_session):
    operator = _user("operator", role="admin")
    super_admin = _role("super_admin")
    db_session.add_all([operator, super_admin])
    db_session.commit()
    db_session.refresh(operator)
    users, audit_logs = _components(db_session)

    result = CreateAdminUserUseCase(
        users=users,
        audit_logs=audit_logs,
        password_hasher=FastPasswordHasher(),
        crypto=FakeCryptoProvider(),
    ).execute(
        CreateAdminUserCommand(
            username="alice",
            password="secret123",
            operator_id=operator.id,
            operator_name=operator.username,
            role="super_admin",
        )
    )

    created = result.user
    assert created.role == "admin"
    assert created.password_hash == "hashed:secret123"
    assert created.user_key_encrypted == "encrypted:user-key"
    assert db_session.query(user_roles).filter_by(user_id=created.id, role_id=super_admin.id).count() == 1
    log = db_session.query(OperationLog).filter_by(action="user_create").one()
    assert json.loads(log.new_value)["mapped_role"] == "admin"


def test_create_admin_user_rejects_duplicate_username(db_session):
    operator = _user("operator", role="admin")
    existing = _user("alice")
    db_session.add_all([operator, existing])
    db_session.commit()
    db_session.refresh(operator)
    users, audit_logs = _components(db_session)

    with pytest.raises(AppError) as exc:
        CreateAdminUserUseCase(
            users=users,
            audit_logs=audit_logs,
            password_hasher=FastPasswordHasher(),
            crypto=FakeCryptoProvider(),
        ).execute(
            CreateAdminUserCommand(
                username="alice",
                password="secret123",
                operator_id=operator.id,
                operator_name=operator.username,
            )
        )

    assert exc.value.code == ErrorCode.CONFLICT


def test_update_admin_user_role_syncs_role_table_and_records_audit(db_session):
    operator = _user("operator", role="admin")
    target = _user("alice", role="user")
    readonly = _role("readonly")
    db_session.add_all([operator, target, readonly])
    db_session.commit()
    db_session.refresh(operator)
    db_session.refresh(target)
    users, audit_logs = _components(db_session)

    result = UpdateAdminUserUseCase(users=users, audit_logs=audit_logs).execute(
        UpdateAdminUserCommand(
            user_id=target.id,
            operator_id=operator.id,
            operator_name=operator.username,
            updates={"role": "readonly", "nickname": "Alice"},
        )
    )

    assert result.user.role == "user"
    assert result.user.nickname == "Alice"
    assert db_session.query(user_roles).filter_by(user_id=target.id, role_id=readonly.id).count() == 1
    log = db_session.query(OperationLog).filter_by(action="user_update").one()
    assert json.loads(log.new_value)["role"] == "readonly"


def test_update_admin_user_invalid_role_does_not_dirty_user(db_session):
    operator = _user("operator", role="admin")
    target = _user("alice", role="user")
    db_session.add_all([operator, target])
    db_session.commit()
    db_session.refresh(target)
    users, audit_logs = _components(db_session)

    with pytest.raises(AppError) as exc:
        UpdateAdminUserUseCase(users=users, audit_logs=audit_logs).execute(
            UpdateAdminUserCommand(
                user_id=target.id,
                operator_id=operator.id,
                operator_name=operator.username,
                updates={"role": "missing_role"},
            )
        )

    assert exc.value.code == ErrorCode.VALIDATION_ERROR
    assert target.role == "user"
    assert db_session.query(OperationLog).count() == 0


def test_delete_admin_user_soft_deletes_revokes_sessions_and_records_audit(db_session):
    operator = _user("operator", role="admin")
    target = _user("alice")
    db_session.add_all([operator, target])
    db_session.commit()
    db_session.refresh(operator)
    db_session.refresh(target)
    session = _session(target.id, "desktop")
    db_session.add(session)
    db_session.commit()
    users, audit_logs = _components(db_session)

    DeleteAdminUserUseCase(users=users, audit_logs=audit_logs).execute(
        DeleteAdminUserCommand(
            user_id=target.id,
            operator_id=operator.id,
            operator_name=operator.username,
        )
    )
    db_session.refresh(target)
    db_session.refresh(session)

    assert target.deleted_at is not None
    assert target.is_active is False
    assert session.is_revoked is True
    assert db_session.query(OperationLog).filter_by(action="user_delete").count() == 1


def test_toggle_admin_user_status_rejects_self_operation(db_session):
    operator = _user("operator", role="admin")
    db_session.add(operator)
    db_session.commit()
    db_session.refresh(operator)
    users, audit_logs = _components(db_session)

    with pytest.raises(AppError) as exc:
        ToggleAdminUserStatusUseCase(users=users, audit_logs=audit_logs).execute(
            ToggleAdminUserStatusCommand(
                user_id=operator.id,
                operator_id=operator.id,
                operator_name=operator.username,
                is_active=False,
            )
        )

    assert exc.value.code == ErrorCode.VALIDATION_ERROR


def test_reset_admin_user_password_force_logout_revokes_sessions_and_logs(db_session):
    operator = _user("operator", role="admin")
    target = _user("alice", token_version=2)
    db_session.add_all([operator, target])
    db_session.commit()
    db_session.refresh(operator)
    db_session.refresh(target)
    session = _session(target.id, "desktop")
    db_session.add(session)
    db_session.commit()
    users, audit_logs = _components(db_session)

    result = ResetAdminUserPasswordUseCase(
        users=users,
        audit_logs=audit_logs,
        password_hasher=FastPasswordHasher(),
    ).execute(
        ResetAdminUserPasswordCommand(
            user_id=target.id,
            operator_id=operator.id,
            operator_name=operator.username,
            new_password="new-secret",
            force_logout=True,
        )
    )
    db_session.refresh(session)

    assert result.user.password_hash == "hashed:new-secret"
    assert result.user.token_version == 3
    assert session.is_revoked is True
    assert db_session.query(OperationLog).filter_by(action="password_reset").count() == 1


def test_unlock_admin_user_missing_returns_not_found(db_session):
    users, audit_logs = _components(db_session)

    with pytest.raises(AppError) as exc:
        UnlockAdminUserUseCase(users=users, audit_logs=audit_logs).execute(
            UnlockAdminUserCommand(
                user_id=404,
                operator_id=1,
                operator_name="admin",
            )
        )

    assert exc.value.code == ErrorCode.NOT_FOUND


def test_batch_admin_users_excludes_operator_and_records_audit(db_session):
    operator = _user("operator", role="admin")
    target = _user("alice")
    db_session.add_all([operator, target])
    db_session.commit()
    db_session.refresh(operator)
    db_session.refresh(target)
    db_session.add(_session(target.id, "desktop"))
    db_session.commit()
    users, audit_logs = _components(db_session)

    result = BatchAdminUsersUseCase(users=users, audit_logs=audit_logs).execute(
        BatchAdminUsersCommand(
            user_ids=[operator.id, target.id],
            action="disable",
            operator_id=operator.id,
            operator_name=operator.username,
        )
    )
    db_session.refresh(operator)
    db_session.refresh(target)

    assert result.affected == 1
    assert operator.is_active is True
    assert target.is_active is False
    assert db_session.query(OperationLog).filter_by(action="batch_disable").count() == 1
