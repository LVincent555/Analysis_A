"""Identity query DTOs."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GetUserProfileQuery:
    user_id: int


@dataclass(frozen=True, slots=True)
class ListUserSessionsQuery:
    user_id: int


@dataclass(frozen=True, slots=True)
class ListAdminSessionsQuery:
    page: int = 1
    page_size: int = 20
    user_id: int | None = None
    username: str | None = None
    status: str | None = None
    include_expired: bool = False
    include_revoked: bool = False


@dataclass(frozen=True, slots=True)
class GetAdminSessionDetailQuery:
    session_id: int


@dataclass(frozen=True, slots=True)
class ListRolesQuery:
    include_inactive: bool = False


@dataclass(frozen=True, slots=True)
class GetRoleDetailQuery:
    role_id: int


@dataclass(frozen=True, slots=True)
class GetUserPermissionsQuery:
    user_id: int


@dataclass(frozen=True, slots=True)
class CheckUserPermissionQuery:
    user_id: int
    permission: str


@dataclass(frozen=True, slots=True)
class ListAdminUsersQuery:
    page: int = 1
    page_size: int = 20
    search: str | None = None
    role: str | None = None
    status: str | None = None
    sort_by: str = "created_at"
    sort_order: str = "desc"
    include_deleted: bool = False


@dataclass(frozen=True, slots=True)
class GetAdminUserDetailQuery:
    user_id: int


@dataclass(frozen=True, slots=True)
class GetLoginHistoryQuery:
    pass
