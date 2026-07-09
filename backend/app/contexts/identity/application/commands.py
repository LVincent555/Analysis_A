"""Identity command DTOs."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class RegisterUserCommand:
    username: str
    password: str


@dataclass(frozen=True, slots=True)
class LoginCommand:
    username: str
    password: str
    device_id: str = "default"
    device_name: str | None = None


@dataclass(frozen=True, slots=True)
class RefreshAccessTokenCommand:
    refresh_token: str


@dataclass(frozen=True, slots=True)
class LogoutDeviceCommand:
    user_id: int
    device_id: str


@dataclass(frozen=True, slots=True)
class LogoutAllDevicesCommand:
    user_id: int


@dataclass(frozen=True, slots=True)
class ChangePasswordCommand:
    user_id: int
    old_password: str
    new_password: str


@dataclass(frozen=True, slots=True)
class RevokeAdminSessionCommand:
    session_id: int
    operator_id: int
    operator_name: str
    ip_address: str | None = None


@dataclass(frozen=True, slots=True)
class RevokeUserSessionsCommand:
    user_id: int
    operator_id: int
    operator_name: str
    ip_address: str | None = None
    exclude_current: bool = False
    current_session_id: int | None = None


@dataclass(frozen=True, slots=True)
class CleanupExpiredSessionsCommand:
    days: int = 30


@dataclass(frozen=True, slots=True)
class CreateRoleCommand:
    name: str
    display_name: str
    description: str | None
    permissions: list[str]
    operator_id: int
    operator_name: str
    ip_address: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateRoleCommand:
    role_id: int
    display_name: str | None = None
    description: str | None = None
    permissions: list[str] | None = None
    is_active: bool | None = None
    operator_id: int | None = None
    operator_name: str | None = None
    ip_address: str | None = None


@dataclass(frozen=True, slots=True)
class DeleteRoleCommand:
    role_id: int
    operator_id: int
    operator_name: str
    ip_address: str | None = None


@dataclass(frozen=True, slots=True)
class AssignRoleToUserCommand:
    user_id: int
    role_id: int
    operator_id: int
    operator_name: str
    ip_address: str | None = None


@dataclass(frozen=True, slots=True)
class RemoveRoleFromUserCommand:
    user_id: int
    role_id: int
    operator_id: int
    operator_name: str
    ip_address: str | None = None


@dataclass(frozen=True, slots=True)
class CreateAdminUserCommand:
    username: str
    password: str
    operator_id: int
    operator_name: str
    email: str | None = None
    phone: str | None = None
    nickname: str | None = None
    role: str = "user"
    allowed_devices: int = 3
    offline_enabled: bool = True
    offline_days: int = 7
    expires_at: datetime | None = None
    remark: str | None = None


@dataclass(frozen=True, slots=True)
class UpdateAdminUserCommand:
    user_id: int
    operator_id: int
    operator_name: str
    updates: dict[str, Any]


@dataclass(frozen=True, slots=True)
class DeleteAdminUserCommand:
    user_id: int
    operator_id: int
    operator_name: str
    hard_delete: bool = False


@dataclass(frozen=True, slots=True)
class ToggleAdminUserStatusCommand:
    user_id: int
    operator_id: int
    operator_name: str
    is_active: bool


@dataclass(frozen=True, slots=True)
class ResetAdminUserPasswordCommand:
    user_id: int
    operator_id: int
    operator_name: str
    new_password: str
    force_logout: bool = True


@dataclass(frozen=True, slots=True)
class UnlockAdminUserCommand:
    user_id: int
    operator_id: int
    operator_name: str


@dataclass(frozen=True, slots=True)
class BatchAdminUsersCommand:
    user_ids: list[int]
    action: str
    operator_id: int
    operator_name: str
