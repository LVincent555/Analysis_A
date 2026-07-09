from __future__ import annotations

import pytest

from app.contexts.operations.application.commands import (
    BatchUpdateSystemConfigsCommand,
    ResetSystemConfigCommand,
    UpdateSystemConfigCommand,
)
from app.contexts.operations.application.config_commands import (
    BatchUpdateSystemConfigsUseCase,
    ResetSystemConfigUseCase,
    UpdateSystemConfigUseCase,
)
from app.contexts.operations.application.config_queries import (
    GetPasswordPolicyUseCase,
    ListSystemConfigsUseCase,
    ValidatePasswordPolicyUseCase,
)
from app.contexts.operations.application.queries import ListSystemConfigsQuery, ValidatePasswordPolicyQuery
from app.contexts.operations.infrastructure.repositories import (
    SqlAlchemyOperationLogRepository,
    SqlAlchemySystemConfigRepository,
)
from app.db_models import OperationLog, SystemConfig
from app.shared.errors import AppError, ErrorCode


class RecordingConfigCache:
    def __init__(self) -> None:
        self.reload_count = 0

    def reload(self) -> None:
        self.reload_count += 1


def _add_config(db_session, key: str, value: str, value_type: str, category: str = "system") -> SystemConfig:
    config = SystemConfig(
        config_key=key,
        config_value=value,
        config_type=value_type,
        category=category,
        description=f"{key} description",
    )
    db_session.add(config)
    db_session.commit()
    db_session.refresh(config)
    return config


def _config_repo(db_session) -> SqlAlchemySystemConfigRepository:
    return SqlAlchemySystemConfigRepository(db_session)


def _audit_repo(db_session) -> SqlAlchemyOperationLogRepository:
    return SqlAlchemyOperationLogRepository(db_session)


def test_update_config_serializes_false_string_as_false(db_session) -> None:
    config = _add_config(db_session, "session_single_device", "true", "bool", "session")
    cache = RecordingConfigCache()

    result = UpdateSystemConfigUseCase(
        configs=_config_repo(db_session),
        audit_logs=_audit_repo(db_session),
        config_cache=cache,
    ).execute(
        UpdateSystemConfigCommand(
            key="session_single_device",
            value="false",
            operator_id=1,
            operator_name="admin",
            ip_address="127.0.0.1",
        )
    )

    db_session.refresh(config)
    assert result["value"] is False
    assert config.config_value == "false"
    assert cache.reload_count == 1
    log = db_session.query(OperationLog).filter_by(action="config_update").one()
    assert log.target_name == "session_single_device"
    assert '"true"' in log.old_value
    assert '"false"' in log.new_value


def test_update_config_rejects_invalid_int_before_writing(db_session) -> None:
    config = _add_config(db_session, "login_max_attempts", "5", "int", "login")

    with pytest.raises(AppError) as exc_info:
        UpdateSystemConfigUseCase(
            configs=_config_repo(db_session),
            audit_logs=_audit_repo(db_session),
            config_cache=RecordingConfigCache(),
        ).execute(
            UpdateSystemConfigCommand(
                key="login_max_attempts",
                value="not-an-int",
                operator_id=1,
                operator_name="admin",
            )
        )

    db_session.refresh(config)
    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
    assert config.config_value == "5"
    assert db_session.query(OperationLog).count() == 0


def test_batch_update_config_is_all_or_nothing_on_validation_error(db_session) -> None:
    login_attempts = _add_config(db_session, "login_max_attempts", "5", "int", "login")
    single_device = _add_config(db_session, "session_single_device", "false", "bool", "session")
    cache = RecordingConfigCache()

    result = BatchUpdateSystemConfigsUseCase(
        configs=_config_repo(db_session),
        audit_logs=_audit_repo(db_session),
        config_cache=cache,
    ).execute(
        BatchUpdateSystemConfigsCommand(
            updates={
                "login_max_attempts": 8,
                "session_single_device": "maybe",
            },
            operator_id=1,
            operator_name="admin",
        )
    )

    db_session.refresh(login_attempts)
    db_session.refresh(single_device)
    assert result["success"] is False
    assert result["updated"] == 0
    assert login_attempts.config_value == "5"
    assert single_device.config_value == "false"
    assert cache.reload_count == 0
    assert db_session.query(OperationLog).count() == 0


def test_batch_update_config_commits_valid_updates_once(db_session) -> None:
    login_attempts = _add_config(db_session, "login_max_attempts", "5", "int", "login")
    single_device = _add_config(db_session, "session_single_device", "false", "bool", "session")
    cache = RecordingConfigCache()

    result = BatchUpdateSystemConfigsUseCase(
        configs=_config_repo(db_session),
        audit_logs=_audit_repo(db_session),
        config_cache=cache,
    ).execute(
        BatchUpdateSystemConfigsCommand(
            updates={
                "login_max_attempts": "8",
                "session_single_device": True,
            },
            operator_id=1,
            operator_name="admin",
        )
    )

    db_session.refresh(login_attempts)
    db_session.refresh(single_device)
    assert result["success"] is True
    assert result["updated"] == 2
    assert login_attempts.config_value == "8"
    assert single_device.config_value == "true"
    assert cache.reload_count == 1
    assert db_session.query(OperationLog).filter_by(action="config_update").count() == 2


def test_reset_config_uses_typed_default_value(db_session) -> None:
    config = _add_config(db_session, "session_single_device", "true", "bool", "session")

    result = ResetSystemConfigUseCase(
        configs=_config_repo(db_session),
        audit_logs=_audit_repo(db_session),
        config_cache=RecordingConfigCache(),
    ).execute(
        ResetSystemConfigCommand(
            key="session_single_device",
            operator_id=1,
            operator_name="admin",
        )
    )

    db_session.refresh(config)
    assert result["value"] is False
    assert config.config_value == "false"


def test_config_queries_use_database_and_defaults(db_session) -> None:
    _add_config(db_session, "password_min_length", "8", "int", "password")
    _add_config(db_session, "password_require_digit", "true", "bool", "password")

    configs = ListSystemConfigsUseCase(configs=_config_repo(db_session)).execute(
        ListSystemConfigsQuery(category="password")
    )
    policy = GetPasswordPolicyUseCase(configs=_config_repo(db_session)).execute()
    validation = ValidatePasswordPolicyUseCase(configs=_config_repo(db_session)).execute(
        ValidatePasswordPolicyQuery(password="abcdefg")
    )

    assert {item["key"] for item in configs} == {"password_min_length", "password_require_digit"}
    assert policy["min_length"] == 8
    assert policy["require_digit"] is True
    assert validation["valid"] is False
    assert "密码长度不能少于 8 位" in validation["errors"]
    assert "密码必须包含数字" in validation["errors"]
