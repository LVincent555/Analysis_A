import json

from app.contexts.identity.application.queries import (
    CheckUserPermissionQuery,
    GetRoleDetailQuery,
    GetUserPermissionsQuery,
    ListRolesQuery,
)
from app.contexts.identity.application.rbac_queries import (
    CheckUserPermissionUseCase,
    GetPermissionsCatalogUseCase,
    GetRoleDetailUseCase,
    GetUserPermissionsUseCase,
    ListRolesUseCase,
)
from app.contexts.identity.infrastructure.repositories import SqlAlchemyIdentityRoleQueryRepository
from app.db_models import Role, User, user_roles


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
    is_active: bool = True,
    is_system: bool = False,
) -> Role:
    return Role(
        name=name,
        display_name=name.title(),
        description=f"{name} role",
        permissions=json.dumps(permissions),
        is_active=is_active,
        is_system=is_system,
    )


def _repo(db_session):
    return SqlAlchemyIdentityRoleQueryRepository(db_session)


def test_permissions_catalog_exposes_permission_definitions():
    result = GetPermissionsCatalogUseCase().execute()

    assert result["permissions"]["*"] == "所有权限"
    assert "role:view" in result["permissions"]


def test_list_roles_excludes_inactive_by_default_and_counts_users(db_session):
    user = _user("alice")
    active_role = _role("analyst", ["query:*"])
    inactive_role = _role("disabled", ["data:view"], is_active=False)
    db_session.add_all([user, active_role, inactive_role])
    db_session.commit()
    db_session.execute(user_roles.insert().values(user_id=user.id, role_id=active_role.id))
    db_session.commit()

    result = ListRolesUseCase(roles=_repo(db_session)).execute(ListRolesQuery())

    assert [role["name"] for role in result["roles"]] == ["analyst"]
    assert result["roles"][0]["user_count"] == 1


def test_get_role_detail_includes_assigned_users(db_session):
    user = _user("alice")
    role = _role("analyst", ["query:*"])
    db_session.add_all([user, role])
    db_session.commit()
    db_session.execute(user_roles.insert().values(user_id=user.id, role_id=role.id))
    db_session.commit()

    result = GetRoleDetailUseCase(roles=_repo(db_session)).execute(
        GetRoleDetailQuery(role_id=role.id)
    )

    assert result["name"] == "analyst"
    assert result["permissions"] == ["query:*"]
    assert result["users"] == [{"id": user.id, "username": "alice", "nickname": None}]


def test_admin_legacy_role_grants_all_permissions(db_session):
    admin = _user("admin", role="admin")
    db_session.add(admin)
    db_session.commit()

    permissions = GetUserPermissionsUseCase(roles=_repo(db_session)).execute(
        GetUserPermissionsQuery(user_id=admin.id)
    )
    has_permission = CheckUserPermissionUseCase(roles=_repo(db_session)).execute(
        CheckUserPermissionQuery(user_id=admin.id, permission="anything:at-all")
    )

    assert permissions == ["*"]
    assert has_permission is True


def test_user_permissions_support_prefix_wildcards(db_session):
    user = _user("alice")
    active_role = _role("analyst", ["query:*"])
    inactive_role = _role("disabled", ["user:create"], is_active=False)
    db_session.add_all([user, active_role, inactive_role])
    db_session.commit()
    db_session.execute(user_roles.insert().values(user_id=user.id, role_id=active_role.id))
    db_session.execute(user_roles.insert().values(user_id=user.id, role_id=inactive_role.id))
    db_session.commit()

    permissions = GetUserPermissionsUseCase(roles=_repo(db_session)).execute(
        GetUserPermissionsQuery(user_id=user.id)
    )
    can_query_stock = CheckUserPermissionUseCase(roles=_repo(db_session)).execute(
        CheckUserPermissionQuery(user_id=user.id, permission="query:stock")
    )
    can_create_user = CheckUserPermissionUseCase(roles=_repo(db_session)).execute(
        CheckUserPermissionQuery(user_id=user.id, permission="user:create")
    )

    assert permissions == ["query:*"]
    assert can_query_stock is True
    assert can_create_user is False
