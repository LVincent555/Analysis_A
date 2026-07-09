"""Admin user command-side use cases for the Identity context."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from ....shared.errors import AppError, ErrorCode
from ....shared.time import utc_now_naive
from .commands import (
    BatchAdminUsersCommand,
    CreateAdminUserCommand,
    DeleteAdminUserCommand,
    ResetAdminUserPasswordCommand,
    ToggleAdminUserStatusCommand,
    UnlockAdminUserCommand,
    UpdateAdminUserCommand,
)
from .ports import (
    IdentityAuditLogRepository,
    IdentityCryptoProvider,
    IdentityUserCommandRepository,
    PasswordHasher,
)


@dataclass(frozen=True, slots=True)
class AdminUserCommandResult:
    success: bool
    message: str
    user: Any | None = None
    affected: int | None = None


def _validation_error(message: str) -> AppError:
    return AppError(ErrorCode.VALIDATION_ERROR, message)


def _conflict(message: str) -> AppError:
    return AppError(ErrorCode.CONFLICT, message)


def _not_found(message: str) -> AppError:
    return AppError(ErrorCode.NOT_FOUND, message)


def _role_mapping(role_name: str) -> str:
    if role_name in ("super_admin", "admin"):
        return "admin"
    return "user"


def _string_value(value) -> str | None:
    return str(value) if value else None


def _parse_datetime(value):
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    return value


class _AdminUserCommandBase:
    def __init__(
        self,
        *,
        users: IdentityUserCommandRepository,
        audit_logs: IdentityAuditLogRepository,
    ) -> None:
        self.users = users
        self.audit_logs = audit_logs

    def _validate_role(self, role_name: str):
        role = self.users.get_active_role_by_name(role_name)
        if not role and role_name not in ("admin", "user"):
            raise _validation_error(f"角色 '{role_name}' 不存在")
        return role

    def _sync_role_if_present(self, user_id: int, role_name: str) -> None:
        role = self.users.get_active_role_by_name(role_name)
        if not role:
            return
        self.users.clear_user_roles(user_id)
        self.users.assign_role_to_user(user_id, role.id)


class CreateAdminUserUseCase(_AdminUserCommandBase):
    def __init__(
        self,
        *,
        users: IdentityUserCommandRepository,
        audit_logs: IdentityAuditLogRepository,
        password_hasher: PasswordHasher,
        crypto: IdentityCryptoProvider,
    ) -> None:
        super().__init__(users=users, audit_logs=audit_logs)
        self.password_hasher = password_hasher
        self.crypto = crypto

    def execute(self, command: CreateAdminUserCommand) -> AdminUserCommandResult:
        if self.users.get_user_by_username(command.username):
            raise _conflict(f"用户名 '{command.username}' 已存在")

        self._validate_role(command.role)
        mapped_role = _role_mapping(command.role)
        now = utc_now_naive()
        user_key = self.crypto.generate_key()
        user = self.users.create_user(
            username=command.username,
            password_hash=self.password_hasher.hash(command.password),
            user_key_encrypted=self.crypto.encrypt_user_key(user_key),
            email=command.email,
            phone=command.phone,
            nickname=command.nickname,
            role=mapped_role,
            allowed_devices=command.allowed_devices,
            offline_enabled=command.offline_enabled,
            offline_days=command.offline_days,
            expires_at=command.expires_at,
            remark=command.remark,
            created_by=command.operator_id,
            now=now,
        )
        self._sync_role_if_present(user.id, command.role)
        self.audit_logs.record(
            log_type="USER",
            action="user_create",
            operator_id=command.operator_id,
            operator_name=command.operator_name,
            target_type="user",
            target_id=user.id,
            target_name=user.username,
            new_value={
                "username": command.username,
                "role": command.role,
                "mapped_role": mapped_role,
            },
        )
        self.users.commit()
        self.users.refresh(user)

        return AdminUserCommandResult(success=True, message="用户创建成功", user=user)


class UpdateAdminUserUseCase(_AdminUserCommandBase):
    def execute(self, command: UpdateAdminUserCommand) -> AdminUserCommandResult:
        user = self.users.get_user_by_id(command.user_id)
        if not user:
            raise _not_found("用户不存在")

        allowed_fields = {
            "email",
            "phone",
            "nickname",
            "avatar_url",
            "remark",
            "allowed_devices",
            "offline_enabled",
            "offline_days",
            "expires_at",
        }
        old_value: dict[str, str | None] = {}
        new_value: dict[str, str | None] = {}

        for field, raw_value in command.updates.items():
            if field not in allowed_fields:
                continue

            new_val = _parse_datetime(raw_value) if field == "expires_at" else raw_value
            old_val = getattr(user, field)
            if old_val != new_val:
                old_value[field] = _string_value(old_val)
                new_value[field] = _string_value(new_val)
                setattr(user, field, new_val)

        role_changed = False
        original_role = None
        if "role" in command.updates:
            original_role = command.updates["role"]
            mapped_role = _role_mapping(original_role)
            self._validate_role(original_role)
            if user.role != original_role:
                old_value["role"] = _string_value(user.role)
                user.role = mapped_role
                new_value["role"] = original_role
                new_value["mapped_role"] = mapped_role
                role_changed = True

        if not new_value:
            return AdminUserCommandResult(success=True, message="用户更新成功", user=user)

        user.updated_at = utc_now_naive()
        if role_changed and original_role:
            self._sync_role_if_present(user.id, original_role)

        self.audit_logs.record(
            log_type="USER",
            action="user_update",
            operator_id=command.operator_id,
            operator_name=command.operator_name,
            target_type="user",
            target_id=user.id,
            target_name=user.username,
            old_value=old_value,
            new_value=new_value,
        )
        self.users.commit()
        self.users.refresh(user)

        return AdminUserCommandResult(success=True, message="用户更新成功", user=user)


class DeleteAdminUserUseCase(_AdminUserCommandBase):
    def execute(self, command: DeleteAdminUserCommand) -> AdminUserCommandResult:
        if command.user_id == command.operator_id:
            raise _validation_error("不能删除自己的账户")

        user = self.users.get_user_by_id(command.user_id)
        if not user:
            raise _not_found("用户不存在")

        now = utc_now_naive()
        username = user.username
        if command.hard_delete:
            self.users.hard_delete_user(user)
        else:
            user.deleted_at = now
            user.is_active = False
            self.users.revoke_sessions_for_user(
                command.user_id,
                revoked_by=command.operator_id,
                now=now,
                only_unrevoked=False,
            )

        self.audit_logs.record(
            log_type="USER",
            action="user_delete",
            operator_id=command.operator_id,
            operator_name=command.operator_name,
            target_type="user",
            target_id=command.user_id,
            target_name=username,
            detail={"hard_delete": command.hard_delete},
        )
        self.users.commit()

        return AdminUserCommandResult(success=True, message="用户已删除")


class ToggleAdminUserStatusUseCase(_AdminUserCommandBase):
    def execute(self, command: ToggleAdminUserStatusCommand) -> AdminUserCommandResult:
        if command.user_id == command.operator_id:
            raise _validation_error("不能禁用自己的账户")

        user = self.users.get_user_by_id(command.user_id)
        if not user:
            raise _not_found("用户不存在")

        now = utc_now_naive()
        old_status = user.is_active
        user.is_active = command.is_active
        user.updated_at = now
        if not command.is_active:
            self.users.revoke_sessions_for_user(
                command.user_id,
                revoked_by=command.operator_id,
                now=now,
                only_unrevoked=True,
            )

        self.audit_logs.record(
            log_type="USER",
            action="user_enable" if command.is_active else "user_disable",
            operator_id=command.operator_id,
            operator_name=command.operator_name,
            target_type="user",
            target_id=user.id,
            target_name=user.username,
            old_value={"is_active": old_status},
            new_value={"is_active": command.is_active},
        )
        self.users.commit()
        self.users.refresh(user)

        return AdminUserCommandResult(success=True, message="用户状态已更新", user=user)


class ResetAdminUserPasswordUseCase(_AdminUserCommandBase):
    def __init__(
        self,
        *,
        users: IdentityUserCommandRepository,
        audit_logs: IdentityAuditLogRepository,
        password_hasher: PasswordHasher,
    ) -> None:
        super().__init__(users=users, audit_logs=audit_logs)
        self.password_hasher = password_hasher

    def execute(self, command: ResetAdminUserPasswordCommand) -> AdminUserCommandResult:
        user = self.users.get_user_by_id(command.user_id)
        if not user:
            raise _not_found("用户不存在")

        now = utc_now_naive()
        user.password_hash = self.password_hasher.hash(command.new_password)
        user.password_changed_at = now
        user.updated_at = now
        user.failed_attempts = 0
        user.locked_until = None
        if command.force_logout:
            user.token_version = (user.token_version or 1) + 1
            self.users.revoke_sessions_for_user(
                command.user_id,
                revoked_by=command.operator_id,
                now=now,
                only_unrevoked=True,
            )

        self.audit_logs.record(
            log_type="SECURITY",
            action="password_reset",
            operator_id=command.operator_id,
            operator_name=command.operator_name,
            target_type="user",
            target_id=user.id,
            target_name=user.username,
            detail={"force_logout": command.force_logout},
        )
        self.users.commit()
        self.users.refresh(user)

        return AdminUserCommandResult(success=True, message="用户密码已重置", user=user)


class UnlockAdminUserUseCase(_AdminUserCommandBase):
    def execute(self, command: UnlockAdminUserCommand) -> AdminUserCommandResult:
        user = self.users.get_user_by_id(command.user_id)
        if not user:
            raise _not_found("用户不存在")

        user.failed_attempts = 0
        user.locked_until = None
        user.updated_at = utc_now_naive()
        self.audit_logs.record(
            log_type="SECURITY",
            action="account_unlocked",
            operator_id=command.operator_id,
            operator_name=command.operator_name,
            target_type="user",
            target_id=user.id,
            target_name=user.username,
        )
        self.users.commit()
        self.users.refresh(user)

        return AdminUserCommandResult(success=True, message="用户已解锁", user=user)


class BatchAdminUsersUseCase(_AdminUserCommandBase):
    def execute(self, command: BatchAdminUsersCommand) -> AdminUserCommandResult:
        if command.action not in ("enable", "disable", "delete"):
            raise _validation_error("无效的操作类型")

        user_ids = [user_id for user_id in command.user_ids if user_id != command.operator_id]
        if not user_ids:
            return AdminUserCommandResult(success=True, message="批量操作完成", affected=0)

        now = utc_now_naive()
        if command.action == "enable":
            affected = self.users.bulk_set_users_active(user_ids, True, now)
        elif command.action == "disable":
            affected = self.users.bulk_set_users_active(user_ids, False, now)
            self.users.revoke_sessions_for_users(
                user_ids,
                revoked_by=command.operator_id,
                now=now,
                only_unrevoked=True,
            )
        else:
            affected = self.users.bulk_soft_delete_users(user_ids, now)
            self.users.revoke_sessions_for_users(
                user_ids,
                revoked_by=command.operator_id,
                now=now,
                only_unrevoked=False,
            )

        self.audit_logs.record(
            log_type="USER",
            action=f"batch_{command.action}",
            operator_id=command.operator_id,
            operator_name=command.operator_name,
            detail={"user_ids": user_ids, "affected": affected},
        )
        self.users.commit()

        return AdminUserCommandResult(success=True, message="批量操作完成", affected=affected)
