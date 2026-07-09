from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.contexts.operations.application.commands import CleanupOperationLogsCommand
from app.contexts.operations.application.log_commands import CleanupOperationLogsUseCase
from app.contexts.operations.application.log_queries import (
    ExportOperationLogsUseCase,
    GetOperationLogDetailUseCase,
    GetOperationLogStatisticsUseCase,
    GetUserActivityUseCase,
    ListOperationLogsUseCase,
)
from app.contexts.operations.application.queries import (
    ExportOperationLogsQuery,
    GetOperationLogDetailQuery,
    GetOperationLogStatisticsQuery,
    GetUserActivityQuery,
    ListOperationLogsQuery,
)
from app.contexts.operations.infrastructure.repositories import SqlAlchemyOperationLogRepository
from app.db_models import OperationLog
from app.shared.errors import AppError, ErrorCode
from app.shared.time import utc_now_naive


def _add_log(db_session, **overrides) -> OperationLog:
    values = {
        "log_type": "USER",
        "action": "user_update",
        "operator_id": 1,
        "operator_name": "admin",
        "target_type": "user",
        "target_id": 2,
        "target_name": "demo",
        "ip_address": "127.0.0.1",
        "detail": '{"note": "alpha"}',
        "status": "success",
        "created_at": utc_now_naive(),
    }
    values.update(overrides)
    log = OperationLog(**values)
    db_session.add(log)
    db_session.commit()
    db_session.refresh(log)
    return log


def _repository(db_session) -> SqlAlchemyOperationLogRepository:
    return SqlAlchemyOperationLogRepository(db_session)


def test_list_operation_logs_filters_and_formats_items(db_session) -> None:
    _add_log(
        db_session,
        operator_name="alice",
        target_name="target-a",
        created_at=datetime(2026, 7, 2, 9, 0, 0),
    )
    _add_log(
        db_session,
        log_type="LOGIN",
        action="login_success",
        operator_name="bob",
        created_at=datetime(2026, 7, 4, 9, 0, 0),
    )

    result = ListOperationLogsUseCase(logs=_repository(db_session)).execute(
        ListOperationLogsQuery(
            log_type="USER",
            search="alice",
            start_date="2026-07-01",
            end_date="2026-07-03",
        )
    )

    assert result["total"] == 1
    assert result["items"][0]["operator_name"] == "alice"
    assert result["items"][0]["log_type_label"] == "用户操作"
    assert result["items"][0]["action_label"] == "更新用户"


def test_list_operation_logs_rejects_invalid_date(db_session) -> None:
    with pytest.raises(AppError) as exc_info:
        ListOperationLogsUseCase(logs=_repository(db_session)).execute(
            ListOperationLogsQuery(start_date="2026/07/01")
        )

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR


def test_get_operation_log_detail_parses_json_fields(db_session) -> None:
    log = _add_log(
        db_session,
        detail='{"changed": true}',
        old_value='{"role": "user"}',
        new_value='{"role": "admin"}',
    )

    result = GetOperationLogDetailUseCase(logs=_repository(db_session)).execute(
        GetOperationLogDetailQuery(log_id=log.id)
    )

    assert result["detail"] == {"changed": True}
    assert result["old_value"] == {"role": "user"}
    assert result["new_value"] == {"role": "admin"}


def test_get_operation_log_detail_raises_not_found(db_session) -> None:
    with pytest.raises(AppError) as exc_info:
        GetOperationLogDetailUseCase(logs=_repository(db_session)).execute(
            GetOperationLogDetailQuery(log_id=999)
        )

    assert exc_info.value.code == ErrorCode.NOT_FOUND


def test_operation_log_statistics_aggregates_recent_rows(db_session) -> None:
    _add_log(db_session, log_type="LOGIN", action="login_failed", status="failed")
    _add_log(db_session, log_type="SECURITY", action="account_locked")

    result = GetOperationLogStatisticsUseCase(logs=_repository(db_session)).execute(
        GetOperationLogStatisticsQuery(days=7)
    )

    assert result["total"] == 2
    assert result["type_distribution"]["LOGIN"]["count"] == 1
    assert result["status_distribution"]["failed"] == 1
    assert result["login_failed_count"] == 1
    assert result["security_event_count"] == 1
    assert result["daily_trend"]


def test_get_user_activity_includes_operator_and_target_rows(db_session) -> None:
    _add_log(db_session, operator_id=7, target_id=99, target_name="other")
    _add_log(db_session, operator_id=3, target_id=7, target_name="target-user")

    result = GetUserActivityUseCase(logs=_repository(db_session)).execute(
        GetUserActivityQuery(user_id=7)
    )

    assert result["total"] == 2
    assert {item["is_operator"] for item in result["items"]} == {True, False}


def test_export_operation_logs_returns_legacy_csv_rows(db_session) -> None:
    _add_log(
        db_session,
        log_type="LOGIN",
        action="login_failed",
        operator_name=None,
        status="failed",
        error_message="bad password",
        created_at=datetime(2026, 7, 2, 9, 30, 0),
    )

    rows = ExportOperationLogsUseCase(logs=_repository(db_session)).execute(
        ExportOperationLogsQuery(start_date="2026-07-01", end_date="2026-07-03", limit=1)
    )

    assert rows == [
        {
            "时间": "2026-07-02 09:30:00",
            "类型": "登录日志",
            "操作": "登录失败",
            "操作者": "系统",
            "目标": "demo",
            "IP地址": "127.0.0.1",
            "状态": "失败",
            "错误信息": "bad password",
        }
    ]


def test_cleanup_operation_logs_deletes_only_old_rows(db_session) -> None:
    _add_log(db_session, created_at=utc_now_naive() - timedelta(days=120))
    _add_log(db_session, created_at=utc_now_naive())

    result = CleanupOperationLogsUseCase(logs=_repository(db_session)).execute(
        CleanupOperationLogsCommand(days=90)
    )

    assert result["deleted"] == 1
    assert db_session.query(OperationLog).count() == 1


def test_cleanup_operation_logs_rejects_non_positive_days(db_session) -> None:
    with pytest.raises(AppError) as exc_info:
        CleanupOperationLogsUseCase(logs=_repository(db_session)).execute(
            CleanupOperationLogsCommand(days=0)
        )

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
