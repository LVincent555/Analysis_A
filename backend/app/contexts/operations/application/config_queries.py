"""System configuration query-side use cases."""

from __future__ import annotations

from typing import Any

from ....shared.errors import AppError, ErrorCode
from ..domain.config import CONFIG_CATEGORIES, DEFAULT_CONFIGS, ConfigValueError, default_config_value, parse_config_value
from .ports import SystemConfigRepository
from .queries import ListSystemConfigsQuery, ValidatePasswordPolicyQuery


def _validation_error(message: str) -> AppError:
    return AppError(ErrorCode.VALIDATION_ERROR, message)


def _config_item(config: Any) -> dict:
    try:
        value = parse_config_value(config.config_value, config.config_type)
    except ConfigValueError as exc:
        raise AppError(
            ErrorCode.INFRASTRUCTURE_ERROR,
            f"配置项 {config.config_key} 的存储值无效: {exc}",
        ) from exc

    return {
        "id": config.id,
        "key": config.config_key,
        "value": value,
        "raw_value": config.config_value,
        "type": config.config_type,
        "category": config.category,
        "category_label": CONFIG_CATEGORIES.get(config.category, config.category),
        "description": config.description,
        "updated_at": config.updated_at.isoformat() if config.updated_at else None,
    }


class GetConfigCategoriesUseCase:
    def execute(self) -> dict:
        return {"categories": CONFIG_CATEGORIES}


class ListSystemConfigsUseCase:
    def __init__(self, *, configs: SystemConfigRepository) -> None:
        self.configs = configs

    def execute(self, query: ListSystemConfigsQuery) -> list[dict]:
        ensure_valid_category(query.category)
        return [_config_item(row) for row in self.configs.list_configs(query.category)]


class GroupSystemConfigsByCategoryUseCase:
    def __init__(self, *, configs: SystemConfigRepository) -> None:
        self.configs = configs

    def execute(self) -> dict[str, list[dict]]:
        grouped: dict[str, list[dict]] = {}
        for item in ListSystemConfigsUseCase(configs=self.configs).execute(ListSystemConfigsQuery()):
            grouped.setdefault(item["category"], []).append(item)
        return grouped


class _PolicyBase:
    def __init__(self, *, configs: SystemConfigRepository) -> None:
        self.configs = configs

    def _get_value(self, key: str, default: Any = None) -> Any:
        config = self.configs.get_by_key(key)
        if config:
            try:
                return parse_config_value(config.config_value, config.config_type)
            except ConfigValueError as exc:
                raise AppError(
                    ErrorCode.INFRASTRUCTURE_ERROR,
                    f"配置项 {key} 的存储值无效: {exc}",
                ) from exc
        if key in DEFAULT_CONFIGS:
            return default_config_value(key)
        return default


class GetPasswordPolicyUseCase(_PolicyBase):
    def execute(self) -> dict:
        return {
            "min_length": self._get_value("password_min_length", 6),
            "max_length": self._get_value("password_max_length", 100),
            "require_digit": self._get_value("password_require_digit", False),
            "require_upper": self._get_value("password_require_upper", False),
            "require_lower": self._get_value("password_require_lower", False),
            "require_special": self._get_value("password_require_special", False),
            "expire_days": self._get_value("password_expire_days", 0),
        }


class GetLoginPolicyUseCase(_PolicyBase):
    def execute(self) -> dict:
        return {
            "max_attempts": self._get_value("login_max_attempts", 5),
            "lockout_minutes": self._get_value("login_lockout_minutes", 30),
            "attempt_reset_minutes": self._get_value("login_attempt_reset_minutes", 60),
            "captcha_enabled": self._get_value("login_captcha_enabled", False),
            "captcha_threshold": self._get_value("login_captcha_threshold", 3),
        }


class GetSessionPolicyUseCase(_PolicyBase):
    def execute(self) -> dict:
        return {
            "access_token_hours": self._get_value("session_access_token_hours", 24),
            "refresh_token_days": self._get_value("session_refresh_token_days", 7),
            "max_devices": self._get_value("session_max_devices", 3),
            "idle_timeout_minutes": self._get_value("session_idle_timeout_minutes", 30),
            "single_device": self._get_value("session_single_device", False),
        }


class ValidatePasswordPolicyUseCase:
    def __init__(self, *, configs: SystemConfigRepository) -> None:
        self.configs = configs

    def execute(self, query: ValidatePasswordPolicyQuery) -> dict:
        policy = GetPasswordPolicyUseCase(configs=self.configs).execute()
        errors: list[str] = []
        password = query.password

        if len(password) < policy["min_length"]:
            errors.append(f"密码长度不能少于 {policy['min_length']} 位")
        if len(password) > policy["max_length"]:
            errors.append(f"密码长度不能超过 {policy['max_length']} 位")
        if policy["require_digit"] and not any(char.isdigit() for char in password):
            errors.append("密码必须包含数字")
        if policy["require_upper"] and not any(char.isupper() for char in password):
            errors.append("密码必须包含大写字母")
        if policy["require_lower"] and not any(char.islower() for char in password):
            errors.append("密码必须包含小写字母")
        if policy["require_special"]:
            special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
            if not any(char in special_chars for char in password):
                errors.append("密码必须包含特殊字符")

        return {"valid": len(errors) == 0, "errors": errors}


def ensure_valid_category(category: str | None) -> None:
    if category and category not in CONFIG_CATEGORIES:
        raise _validation_error(f"未知配置分类: {category}")
