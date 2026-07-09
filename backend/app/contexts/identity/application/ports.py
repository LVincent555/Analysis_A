"""Identity application ports."""

from datetime import datetime
from typing import Any, Protocol


class PasswordHasher(Protocol):
    def hash(self, password: str) -> str:
        ...

    def verify(self, password: str, hashed: str) -> bool:
        ...


class TokenIssuer(Protocol):
    def create_access_token(
        self,
        user_id: int,
        device_id: str = "default",
        expires_hours: int | None = None,
        token_version: int | None = None,
    ) -> str:
        ...

    def create_refresh_token(
        self,
        user_id: int,
        device_id: str = "default",
        expires_days: int | None = None,
        token_version: int | None = None,
    ) -> str:
        ...

    def verify_token(self, token: str) -> dict | None:
        ...

    def get_token_expiry(self, token: str) -> datetime | None:
        ...


class SessionKeyStore(Protocol):
    def set(self, user_id: int, session_key: bytes, device_id: str = "default") -> None:
        ...

    def get(self, user_id: int, device_id: str = "default") -> bytes | None:
        ...

    def remove(self, user_id: int, device_id: str | None = None) -> None:
        ...


class SessionPolicyProvider(Protocol):
    def get_login_policy(self) -> dict:
        ...

    def get_session_policy(self, user: Any) -> dict:
        ...


class IdentityUserRepository(Protocol):
    def get_by_id(self, user_id: int) -> Any | None:
        ...

    def get_by_username(self, username: str) -> Any | None:
        ...

    def add_user(self, username: str, password_hash: str, user_key_encrypted: str) -> Any:
        ...

    def refresh(self, entity: Any) -> None:
        ...

    def commit(self) -> None:
        ...


class IdentitySessionRepository(Protocol):
    def find_valid_refresh_session(
        self,
        user_id: int,
        device_id: str,
        refresh_token: str,
        now: datetime,
    ) -> Any | None:
        ...

    def find_active_session(self, user_id: int, device_id: str, now: datetime) -> Any | None:
        ...

    def touch(self, session: Any, now: datetime) -> None:
        ...

    def get_by_user_device(self, user_id: int, device_id: str) -> Any | None:
        ...

    def count_active_for_user(self, user_id: int, now: datetime) -> int:
        ...

    def find_oldest_active_for_user(self, user_id: int, now: datetime) -> Any | None:
        ...

    def list_active_for_user(self, user_id: int, now: datetime) -> list[Any]:
        ...

    def list_for_admin(
        self,
        *,
        page: int,
        page_size: int,
        user_id: int | None,
        username: str | None,
        include_expired: bool,
        include_revoked: bool,
        now: datetime,
    ) -> tuple[int, list[Any]]:
        ...

    def get_by_id(self, session_id: int) -> Any | None:
        ...

    def list_unrevoked_for_user(
        self,
        user_id: int,
        exclude_session_id: int | None = None,
    ) -> list[Any]:
        ...

    def list_active(self, now: datetime) -> list[Any]:
        ...

    def count_online_users(self, *, now: datetime, active_since: datetime) -> int:
        ...

    def platform_distribution(self, now: datetime) -> dict[str, int]:
        ...

    def delete(self, session: Any) -> None:
        ...

    def upsert_user_device_session(
        self,
        *,
        existing_session: Any | None,
        user_id: int,
        device_id: str,
        device_name: str | None,
        session_key_encrypted: str,
        refresh_token: str,
        expires_at: datetime,
        now: datetime,
    ) -> Any:
        ...

    def revoke_device(self, user_id: int, device_id: str, revoked_by: int, now: datetime) -> None:
        ...

    def delete_all_for_user(self, user_id: int) -> None:
        ...

    def cleanup_expired_before(self, cutoff: datetime) -> int:
        ...

    def commit(self) -> None:
        ...


class LoginHistoryQueryPort(Protocol):
    def get_login_history(self) -> Any:
        ...


class IdentityCryptoProvider(Protocol):
    def generate_key(self) -> bytes:
        ...

    def encrypt_user_key(self, user_key: bytes) -> str:
        ...

    def encrypt_session_key_with_password(self, password: str, session_key: bytes) -> str:
        ...


class IdentityAuditLogRepository(Protocol):
    def record(
        self,
        *,
        log_type: str,
        action: str,
        operator_id: int | None,
        operator_name: str | None,
        target_type: str | None = None,
        target_id: int | None = None,
        target_name: str | None = None,
        ip_address: str | None = None,
        detail: dict | None = None,
        old_value: dict | None = None,
        new_value: dict | None = None,
        status: str = "success",
    ) -> None:
        ...


class IdentityRoleQueryRepository(Protocol):
    def list_roles(self, include_inactive: bool) -> list[Any]:
        ...

    def count_users_for_role(self, role_id: int) -> int:
        ...

    def get_role_by_id(self, role_id: int) -> Any | None:
        ...

    def get_user_with_roles(self, user_id: int) -> Any | None:
        ...


class IdentityRoleCommandRepository(Protocol):
    def get_user_by_id(self, user_id: int) -> Any | None:
        ...

    def get_role_by_id(self, role_id: int) -> Any | None:
        ...

    def get_role_by_name(self, name: str) -> Any | None:
        ...

    def create_role(
        self,
        *,
        name: str,
        display_name: str,
        description: str | None,
        permissions: list[str],
    ) -> Any:
        ...

    def set_role_permissions(self, role: Any, permissions: list[str]) -> None:
        ...

    def count_users_for_role(self, role_id: int) -> int:
        ...

    def user_has_role(self, user_id: int, role_id: int) -> bool:
        ...

    def assign_role_to_user(self, user_id: int, role_id: int) -> None:
        ...

    def remove_role_from_user(self, user_id: int, role_id: int) -> None:
        ...

    def delete_role(self, role: Any) -> None:
        ...

    def commit(self) -> None:
        ...


class IdentityUserQueryRepository(Protocol):
    def list_users(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None,
        role: str | None,
        status: str | None,
        sort_by: str,
        sort_order: str,
        include_deleted: bool,
        now: datetime,
    ) -> tuple[int, list[Any], dict[int, int]]:
        ...

    def get_user_by_id(self, user_id: int) -> Any | None:
        ...

    def list_unrevoked_sessions_for_user(self, user_id: int) -> list[Any]:
        ...


class IdentityUserCommandRepository(Protocol):
    def get_user_by_id(self, user_id: int) -> Any | None:
        ...

    def get_user_by_username(self, username: str) -> Any | None:
        ...

    def get_active_role_by_name(self, name: str) -> Any | None:
        ...

    def create_user(
        self,
        *,
        username: str,
        password_hash: str,
        user_key_encrypted: str,
        email: str | None,
        phone: str | None,
        nickname: str | None,
        role: str,
        allowed_devices: int,
        offline_enabled: bool,
        offline_days: int,
        expires_at: datetime | None,
        remark: str | None,
        created_by: int,
        now: datetime,
    ) -> Any:
        ...

    def refresh(self, entity: Any) -> None:
        ...

    def clear_user_roles(self, user_id: int) -> None:
        ...

    def assign_role_to_user(self, user_id: int, role_id: int) -> None:
        ...

    def revoke_sessions_for_user(
        self,
        user_id: int,
        *,
        revoked_by: int,
        now: datetime,
        only_unrevoked: bool,
    ) -> None:
        ...

    def hard_delete_user(self, user: Any) -> None:
        ...

    def bulk_set_users_active(self, user_ids: list[int], is_active: bool, now: datetime) -> int:
        ...

    def bulk_soft_delete_users(self, user_ids: list[int], now: datetime) -> int:
        ...

    def revoke_sessions_for_users(
        self,
        user_ids: list[int],
        *,
        revoked_by: int,
        now: datetime,
        only_unrevoked: bool,
    ) -> None:
        ...

    def commit(self) -> None:
        ...
