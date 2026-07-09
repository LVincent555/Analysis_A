"""System configuration domain rules."""

from __future__ import annotations

import json
from typing import Any

CONFIG_CATEGORIES = {
    "password": "密码策略",
    "login": "登录策略",
    "session": "会话策略",
    "system": "系统配置",
}

DEFAULT_CONFIGS = {
    "password_min_length": {"value": "6", "type": "int", "category": "password", "description": "密码最小长度"},
    "password_max_length": {"value": "100", "type": "int", "category": "password", "description": "密码最大长度"},
    "password_require_digit": {"value": "false", "type": "bool", "category": "password", "description": "要求包含数字"},
    "password_require_upper": {"value": "false", "type": "bool", "category": "password", "description": "要求包含大写字母"},
    "password_require_lower": {"value": "false", "type": "bool", "category": "password", "description": "要求包含小写字母"},
    "password_require_special": {"value": "false", "type": "bool", "category": "password", "description": "要求包含特殊字符"},
    "password_expire_days": {"value": "0", "type": "int", "category": "password", "description": "密码过期天数，0=不过期"},
    "login_max_attempts": {"value": "5", "type": "int", "category": "login", "description": "最大失败尝试次数"},
    "login_lockout_minutes": {"value": "30", "type": "int", "category": "login", "description": "锁定时长，分钟"},
    "login_attempt_reset_minutes": {"value": "60", "type": "int", "category": "login", "description": "失败计数重置时间"},
    "login_captcha_enabled": {"value": "false", "type": "bool", "category": "login", "description": "启用验证码"},
    "login_captcha_threshold": {"value": "3", "type": "int", "category": "login", "description": "验证码触发次数"},
    "session_access_token_hours": {"value": "24", "type": "int", "category": "session", "description": "Access Token 有效期，小时"},
    "session_refresh_token_days": {"value": "7", "type": "int", "category": "session", "description": "Refresh Token 有效期，天"},
    "session_max_devices": {"value": "3", "type": "int", "category": "session", "description": "默认最大设备数"},
    "session_idle_timeout_minutes": {"value": "30", "type": "int", "category": "session", "description": "空闲超时，分钟"},
    "session_single_device": {"value": "false", "type": "bool", "category": "session", "description": "单设备登录限制"},
}

TRUE_VALUES = {"true", "1", "yes", "on", "y"}
FALSE_VALUES = {"false", "0", "no", "off", "n"}


class ConfigValueError(ValueError):
    """Raised when a config value cannot be represented by its declared type."""


def parse_config_value(value: Any, value_type: str) -> Any:
    if value_type == "int":
        if isinstance(value, bool):
            raise ConfigValueError("布尔值不能作为整数配置")
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ConfigValueError("整数配置必须是有效整数") from exc

    if value_type == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, int) and value in (0, 1):
            return bool(value)
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in TRUE_VALUES:
                return True
            if normalized in FALSE_VALUES:
                return False
        raise ConfigValueError("布尔配置必须是 true/false")

    if value_type == "json":
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError as exc:
                raise ConfigValueError("JSON 配置必须是有效 JSON") from exc
        return value

    return "" if value is None else str(value)


def serialize_config_value(value: Any, value_type: str) -> str:
    parsed = parse_config_value(value, value_type)
    if value_type == "bool":
        return "true" if parsed else "false"
    if value_type == "json":
        try:
            return json.dumps(parsed, ensure_ascii=False)
        except TypeError as exc:
            raise ConfigValueError("JSON 配置必须可序列化") from exc
    return str(parsed)


def default_config_value(key: str) -> Any:
    config = DEFAULT_CONFIGS[key]
    return parse_config_value(config["value"], config["type"])
