import json

import pytest

from app.contexts.identity.application.commands import (
    AssignRoleToUserCommand,
    CreateRoleCommand,
    DeleteRoleCommand,
    RemoveRoleFromUserCommand,
    UpdateRoleCommand,
)
from app.contexts.identity.application.rbac_commands import (
    AssignRoleToUserUseCase,
    CreateRoleUseCase,
    DeleteRoleUseCase,
    RemoveRoleFromUserUseCase,
    UpdateRoleUseCase,
)
from app.contexts.identity.infrastructure.repositories import (
    SqlAlchemyIdentityAuditLogRepository,
    SqlAlchemyIdentityRoleQueryRepository,
)
from app.db_models import OperationLog, Role, User, user_roles
from app.shared.errors import AppError, ErrorCode


def _user(username: str, *, role: str = "user") -> User:
    return User(
        username=username,
        password_hash="hashed",
        user_key_encrypted="encrypted-key",
        role=role,
        is_active=True,
    )


def _role(
    name: str,
    permissions: list[str],
    *,
    is_system: bool = False,
) -> Role:
    return Role(
        name=name,
        display_name=name.title(),
        description=f"{name} role",
        permissions=json.dumps(permissions),
        is_active=True,
        is_system=is_system,
    )


def _components(db_session):
    return (
        SqlAlchemyIdentityRoleQueryRepository(db_session),
        SqlAlchemyIdentityAuditLogRepository(db_session),
    )


def test_create_role_persists_role_and_audit_log(db_session):
    roles, audit_logs = _components(db_session)

    result = CreateRoleUseCase(roles=roles, audit_logs=audit_logs).execute(
        CreateRoleCommand(
            name="analyst",
            display_name="Analyst",
            description="Reads analytics",
            permissions=["query:*"],
            operator_id=1,
            operator_name="admin",
            ip_address="127.0.0.1",
        )
    )

    role = db_session.query(Role).filter_by(name="analyst").one()
    log = db_session.query(OperationLog).filter_by(action="role_create").one()
    assert result.role_id == role.id
    assert role.get_permissions() == ["query:*"]
    assert json.loads(log.new_value)["name"] == "analyst"


def test_create_role_rejects_duplicate_name(db_session):
    db_session.add(_role("analyst", ["query:*"]))
    db_session.commit()
    roles, audit_logs = _components(db_session)

    with pytest.raises(AppError) as exc:
        CreateRoleUseCase(roles=roles, audit_logs=audit_logs).execute(
            CreateRoleCommand(
                name="analyst",
                display_name="Analyst",
                description=None,
                permissions=[],
                operator_id=1,
                operator_name="admin",
            )
        )

    assert exc.value.code == ErrorCode.VALIDATION_ERROR


def test_update_role_rejects_system_permission_changes(db_session):
    role = _role("admin", ["*"], is_system=True)
    db_session.add(role)
    db_session.commit()
    roles, audit_logs = _components(db_session)

    with pytest.raises(AppError) as exc:
        UpdateRoleUseCase(roles=roles, audit_logs=audit_logs).execute(
            UpdateRoleCommand(
                role_id=role.id,
                permissions=["role:view"],
                operator_id=1,
                operator_name="admin",
            )
        )

    assert exc.value.code == ErrorCode.VALIDATION_ERROR
    assert db_session.query(OperationLog).count() == 0


def test_delete_role_rejects_assigned_roles(db_session):
    user = _user("alice")
    role = _role("analyst", ["query:*"])
    db_session.add_all([user, role])
    db_session.commit()
    db_session.execute(user_roles.insert().values(user_id=user.id, role_id=role.id))
    db_session.commit()
    roles, audit_logs = _components(db_session)

    with pytest.raises(AppError) as exc:
        DeleteRoleUseCase(roles=roles, audit_logs=audit_logs).execute(
            DeleteRoleCommand(
                role_id=role.id,
                operator_id=1,
                operator_name="admin",
            )
        )

    assert exc.value.code == ErrorCode.VALIDATION_ERROR
    assert db_session.query(Role).filter_by(id=role.id).one()


def test_assign_role_is_idempotent_and_does_not_sync_legacy_user_role(db_session):
    user = _user("alice", role="user")
    role = _role("admin", ["*"])
    db_session.add_all([user, role])
    db_session.commit()
    roles, audit_logs = _components(db_session)

    first = AssignRoleToUserUseCase(roles=roles, audit_logs=audit_logs).execute(
        AssignRoleToUserCommand(
            user_id=user.id,
            role_id=role.id,
            operator_id=1,
            operator_name="admin",
        )
    )
    second = AssignRoleToUserUseCase(roles=roles, audit_logs=audit_logs).execute(
        AssignRoleToUserCommand(
            user_id=user.id,
            role_id=role.id,
            operator_id=1,
            operator_name="admin",
        )
    )
    db_session.refresh(user)

    assert first.success is True
    assert second.message == "用户已拥有该角色"
    assert user.role == "user"
    assert db_session.query(user_roles).filter_by(user_id=user.id, role_id=role.id).count() == 1
    assert db_session.query(OperationLog).filter_by(action="role_assign").count() == 1


def test_remove_role_deletes_link_and_records_audit_log(db_session):
    user = _user("alice")
    role = _role("analyst", ["query:*"])
    db_session.add_all([user, role])
    db_session.commit()
    db_session.execute(user_roles.insert().values(user_id=user.id, role_id=role.id))
    db_session.commit()
    roles, audit_logs = _components(db_session)

    result = RemoveRoleFromUserUseCase(roles=roles, audit_logs=audit_logs).execute(
        RemoveRoleFromUserCommand(
            user_id=user.id,
            role_id=role.id,
            operator_id=1,
            operator_name="admin",
        )
    )

    assert result.success is True
    assert db_session.query(user_roles).filter_by(user_id=user.id, role_id=role.id).count() == 0
    assert db_session.query(OperationLog).filter_by(action="role_remove").count() == 1
