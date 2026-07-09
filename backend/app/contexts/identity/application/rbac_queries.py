"""RBAC query-side use cases for the Identity context."""

from typing import Any

from ....shared.errors import AppError, ErrorCode
from ..domain.permissions import ALL_PERMISSIONS, permission_matches
from .ports import IdentityRoleQueryRepository
from .queries import CheckUserPermissionQuery, GetRoleDetailQuery, GetUserPermissionsQuery, ListRolesQuery


def _not_found(message: str) -> AppError:
    return AppError(ErrorCode.NOT_FOUND, message)


def _role_to_dict(role: Any) -> dict:
    return {
        "id": role.id,
        "name": role.name,
        "display_name": role.display_name,
        "description": role.description,
        "permissions": role.get_permissions(),
        "is_system": role.is_system,
        "is_active": role.is_active,
        "created_at": role.created_at.isoformat() if role.created_at else None,
        "updated_at": role.updated_at.isoformat() if role.updated_at else None,
    }


class GetPermissionsCatalogUseCase:
    def execute(self) -> dict:
        return {"permissions": ALL_PERMISSIONS}


class ListRolesUseCase:
    def __init__(self, *, roles: IdentityRoleQueryRepository) -> None:
        self.roles = roles

    def execute(self, query: ListRolesQuery) -> dict:
        rows = []
        for role in self.roles.list_roles(query.include_inactive):
            role_dict = _role_to_dict(role)
            role_dict["user_count"] = self.roles.count_users_for_role(role.id)
            rows.append(role_dict)
        return {"roles": rows}


class GetRoleDetailUseCase:
    def __init__(self, *, roles: IdentityRoleQueryRepository) -> None:
        self.roles = roles

    def execute(self, query: GetRoleDetailQuery) -> dict:
        role = self.roles.get_role_by_id(query.role_id)
        if not role:
            raise _not_found("角色不存在")

        role_dict = _role_to_dict(role)
        role_dict["users"] = [
            {
                "id": user.id,
                "username": user.username,
                "nickname": user.nickname,
            }
            for user in role.users
        ]
        return role_dict


class GetUserPermissionsUseCase:
    def __init__(self, *, roles: IdentityRoleQueryRepository) -> None:
        self.roles = roles

    def execute(self, query: GetUserPermissionsQuery) -> list[str]:
        user = self.roles.get_user_with_roles(query.user_id)
        if not user:
            return []

        if user.role == "admin":
            return ["*"]

        permissions: set[str] = set()
        for role in user.roles:
            if not role.is_active:
                continue
            role_permissions = role.get_permissions()
            if "*" in role_permissions:
                return ["*"]
            permissions.update(role_permissions)

        return list(permissions)


class CheckUserPermissionUseCase:
    def __init__(self, *, roles: IdentityRoleQueryRepository) -> None:
        self.roles = roles

    def execute(self, query: CheckUserPermissionQuery) -> bool:
        permissions = GetUserPermissionsUseCase(roles=self.roles).execute(
            GetUserPermissionsQuery(user_id=query.user_id)
        )
        return permission_matches(permissions, query.permission)
