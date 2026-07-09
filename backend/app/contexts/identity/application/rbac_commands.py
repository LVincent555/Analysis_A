"""RBAC command-side use cases for the Identity context."""

from dataclasses import dataclass

from ....shared.errors import AppError, ErrorCode
from ....shared.time import utc_now_naive
from .commands import (
    AssignRoleToUserCommand,
    CreateRoleCommand,
    DeleteRoleCommand,
    RemoveRoleFromUserCommand,
    UpdateRoleCommand,
)
from .ports import IdentityAuditLogRepository, IdentityRoleCommandRepository


@dataclass(frozen=True, slots=True)
class RoleCommandResult:
    success: bool
    message: str
    role_id: int | None = None


def _validation_error(message: str) -> AppError:
    return AppError(ErrorCode.VALIDATION_ERROR, message)


def _role_value(role) -> dict:
    return {
        "display_name": role.display_name,
        "description": role.description,
        "permissions": role.get_permissions(),
        "is_active": role.is_active,
    }


class CreateRoleUseCase:
    def __init__(
        self,
        *,
        roles: IdentityRoleCommandRepository,
        audit_logs: IdentityAuditLogRepository,
    ) -> None:
        self.roles = roles
        self.audit_logs = audit_logs

    def execute(self, command: CreateRoleCommand) -> RoleCommandResult:
        if self.roles.get_role_by_name(command.name):
            raise _validation_error(f"角色名称已存在: {command.name}")

        role = self.roles.create_role(
            name=command.name,
            display_name=command.display_name,
            description=command.description,
            permissions=command.permissions,
        )
        self.audit_logs.record(
            log_type="USER",
            action="role_create",
            operator_id=command.operator_id,
            operator_name=command.operator_name,
            target_type="role",
            target_id=role.id,
            target_name=command.name,
            ip_address=command.ip_address,
            new_value={
                "name": command.name,
                "display_name": command.display_name,
                "permissions": command.permissions,
            },
        )
        self.roles.commit()

        return RoleCommandResult(success=True, message="角色创建成功", role_id=role.id)


class UpdateRoleUseCase:
    def __init__(
        self,
        *,
        roles: IdentityRoleCommandRepository,
        audit_logs: IdentityAuditLogRepository,
    ) -> None:
        self.roles = roles
        self.audit_logs = audit_logs

    def execute(self, command: UpdateRoleCommand) -> RoleCommandResult:
        role = self.roles.get_role_by_id(command.role_id)
        if not role:
            raise _validation_error("角色不存在")

        if role.is_system and command.permissions is not None:
            raise _validation_error("系统预设角色的权限不可修改")

        old_value = _role_value(role)

        if command.display_name is not None:
            role.display_name = command.display_name
        if command.description is not None:
            role.description = command.description
        if command.permissions is not None:
            self.roles.set_role_permissions(role, command.permissions)
        if command.is_active is not None:
            role.is_active = command.is_active

        role.updated_at = utc_now_naive()
        self.audit_logs.record(
            log_type="USER",
            action="role_update",
            operator_id=command.operator_id,
            operator_name=command.operator_name,
            target_type="role",
            target_id=command.role_id,
            target_name=role.name,
            ip_address=command.ip_address,
            old_value=old_value,
            new_value=_role_value(role),
        )
        self.roles.commit()

        return RoleCommandResult(success=True, message="角色更新成功")


class DeleteRoleUseCase:
    def __init__(
        self,
        *,
        roles: IdentityRoleCommandRepository,
        audit_logs: IdentityAuditLogRepository,
    ) -> None:
        self.roles = roles
        self.audit_logs = audit_logs

    def execute(self, command: DeleteRoleCommand) -> RoleCommandResult:
        role = self.roles.get_role_by_id(command.role_id)
        if not role:
            raise _validation_error("角色不存在")

        if role.is_system:
            raise _validation_error("系统预设角色不可删除")

        user_count = self.roles.count_users_for_role(command.role_id)
        if user_count > 0:
            raise _validation_error(f"该角色下还有 {user_count} 个用户，请先移除用户")

        role_name = role.name
        self.roles.delete_role(role)
        self.audit_logs.record(
            log_type="USER",
            action="role_delete",
            operator_id=command.operator_id,
            operator_name=command.operator_name,
            target_type="role",
            target_id=command.role_id,
            target_name=role_name,
            ip_address=command.ip_address,
        )
        self.roles.commit()

        return RoleCommandResult(success=True, message="角色删除成功")


class AssignRoleToUserUseCase:
    def __init__(
        self,
        *,
        roles: IdentityRoleCommandRepository,
        audit_logs: IdentityAuditLogRepository,
    ) -> None:
        self.roles = roles
        self.audit_logs = audit_logs

    def execute(self, command: AssignRoleToUserCommand) -> RoleCommandResult:
        user = self.roles.get_user_by_id(command.user_id)
        if not user:
            raise _validation_error("用户不存在")

        role = self.roles.get_role_by_id(command.role_id)
        if not role:
            raise _validation_error("角色不存在")

        if self.roles.user_has_role(command.user_id, command.role_id):
            return RoleCommandResult(success=True, message="用户已拥有该角色")

        self.roles.assign_role_to_user(command.user_id, command.role_id)
        self.audit_logs.record(
            log_type="USER",
            action="role_assign",
            operator_id=command.operator_id,
            operator_name=command.operator_name,
            target_type="user",
            target_id=command.user_id,
            target_name=user.username,
            ip_address=command.ip_address,
            detail={"role_id": command.role_id, "role_name": role.name},
        )
        self.roles.commit()

        return RoleCommandResult(success=True, message=f"已为用户分配角色: {role.display_name}")


class RemoveRoleFromUserUseCase:
    def __init__(
        self,
        *,
        roles: IdentityRoleCommandRepository,
        audit_logs: IdentityAuditLogRepository,
    ) -> None:
        self.roles = roles
        self.audit_logs = audit_logs

    def execute(self, command: RemoveRoleFromUserCommand) -> RoleCommandResult:
        user = self.roles.get_user_by_id(command.user_id)
        if not user:
            raise _validation_error("用户不存在")

        role = self.roles.get_role_by_id(command.role_id)
        if not role:
            raise _validation_error("角色不存在")

        self.roles.remove_role_from_user(command.user_id, command.role_id)
        self.audit_logs.record(
            log_type="USER",
            action="role_remove",
            operator_id=command.operator_id,
            operator_name=command.operator_name,
            target_type="user",
            target_id=command.user_id,
            target_name=user.username,
            ip_address=command.ip_address,
            detail={"role_id": command.role_id, "role_name": role.name},
        )
        self.roles.commit()

        return RoleCommandResult(success=True, message=f"已移除用户角色: {role.display_name}")
