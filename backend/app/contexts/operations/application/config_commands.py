"""System configuration command-side use cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ....shared.errors import AppError, ErrorCode
from ....shared.time import utc_now_naive
from ..domain.config import DEFAULT_CONFIGS, ConfigValueError, default_config_value, parse_config_value, serialize_config_value
from .commands import BatchUpdateSystemConfigsCommand, ResetSystemConfigCommand, UpdateSystemConfigCommand
from .ports import ConfigCacheReloader, OperationLogCommandRepository, SystemConfigRepository


@dataclass(frozen=True, slots=True)
class PreparedConfigUpdate:
    config: Any
    key: str
    old_value: str
    serialized_value: str
    parsed_value: Any


class NoopConfigCacheReloader:
    def reload(self) -> None:
        return None


def _validation_error(message: str, details: dict | None = None) -> AppError:
    return AppError(ErrorCode.VALIDATION_ERROR, message, details)


def _not_found(message: str) -> AppError:
    return AppError(ErrorCode.NOT_FOUND, message)


class _ConfigCommandBase:
    def __init__(
        self,
        *,
        configs: SystemConfigRepository,
        audit_logs: OperationLogCommandRepository,
        config_cache: ConfigCacheReloader | None = None,
    ) -> None:
        self.configs = configs
        self.audit_logs = audit_logs
        self.config_cache = config_cache or NoopConfigCacheReloader()

    def _prepare_update(self, key: str, value: Any) -> PreparedConfigUpdate:
        config = self.configs.get_by_key(key)
        if not config:
            raise _not_found(f"配置项不存在: {key}")

        try:
            serialized_value = serialize_config_value(value, config.config_type)
            parsed_value = parse_config_value(serialized_value, config.config_type)
        except ConfigValueError as exc:
            raise _validation_error(f"配置项 {key} 的值无效: {exc}") from exc

        return PreparedConfigUpdate(
            config=config,
            key=key,
            old_value=config.config_value,
            serialized_value=serialized_value,
            parsed_value=parsed_value,
        )

    def _apply_prepared_update(
        self,
        prepared: PreparedConfigUpdate,
        *,
        operator_id: int,
        operator_name: str,
        ip_address: str | None,
    ) -> None:
        self.configs.set_value(
            prepared.config,
            prepared.serialized_value,
            operator_id,
            utc_now_naive(),
        )
        self.audit_logs.record(
            log_type="SYSTEM",
            action="config_update",
            operator_id=operator_id,
            operator_name=operator_name,
            target_type="config",
            target_id=prepared.config.id,
            target_name=prepared.key,
            ip_address=ip_address,
            old_value={"value": prepared.old_value},
            new_value={"value": prepared.serialized_value},
            detail={"description": prepared.config.description},
        )

    def _commit_and_reload(self) -> None:
        self.configs.commit()
        self.config_cache.reload()


class UpdateSystemConfigUseCase(_ConfigCommandBase):
    def execute(self, command: UpdateSystemConfigCommand) -> dict:
        prepared = self._prepare_update(command.key, command.value)
        self._apply_prepared_update(
            prepared,
            operator_id=command.operator_id,
            operator_name=command.operator_name,
            ip_address=command.ip_address,
        )
        self._commit_and_reload()
        return {
            "success": True,
            "message": "配置已更新",
            "key": command.key,
            "value": prepared.parsed_value,
        }


class BatchUpdateSystemConfigsUseCase(_ConfigCommandBase):
    def execute(self, command: BatchUpdateSystemConfigsCommand) -> dict:
        prepared_updates: list[PreparedConfigUpdate] = []
        errors: list[dict[str, str]] = []

        for key, value in command.updates.items():
            try:
                prepared_updates.append(self._prepare_update(key, value))
            except AppError as error:
                errors.append({"key": key, "error": error.message})

        if errors:
            return {
                "success": False,
                "message": "批量更新失败，未写入任何配置",
                "updated": 0,
                "errors": errors,
            }

        for prepared in prepared_updates:
            self._apply_prepared_update(
                prepared,
                operator_id=command.operator_id,
                operator_name=command.operator_name,
                ip_address=command.ip_address,
            )

        self._commit_and_reload()
        return {
            "success": True,
            "message": f"已更新 {len(prepared_updates)} 项配置",
            "updated": len(prepared_updates),
            "errors": [],
        }


class ResetSystemConfigUseCase(_ConfigCommandBase):
    def execute(self, command: ResetSystemConfigCommand) -> dict:
        if command.key not in DEFAULT_CONFIGS:
            raise _validation_error(f"没有默认值: {command.key}")

        default_value = default_config_value(command.key)
        prepared = self._prepare_update(command.key, default_value)
        self._apply_prepared_update(
            prepared,
            operator_id=command.operator_id,
            operator_name=command.operator_name,
            ip_address=command.ip_address,
        )
        self._commit_and_reload()
        return {
            "success": True,
            "message": "配置已更新",
            "key": command.key,
            "value": prepared.parsed_value,
        }
