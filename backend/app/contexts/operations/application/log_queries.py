"""Operation log query-side use cases."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from ....shared.errors import AppError, ErrorCode
from ....shared.time import utc_now_naive
from ..domain.logs import (
    LOG_ACTIONS,
    LOG_TYPES,
    SYSTEM_OPERATOR_NAME,
    action_label,
    log_type_label,
    status_label,
)
from .ports import OperationLogQueryRepository
from .queries import (
    ExportOperationLogsQuery,
    GetOperationLogDetailQuery,
    GetOperationLogStatisticsQuery,
    GetUserActivityQuery,
    ListOperationLogsQuery,
)


def _validation_error(message: str) -> AppError:
    return AppError(ErrorCode.VALIDATION_ERROR, message)


def _not_found(message: str) -> AppError:
    return AppError(ErrorCode.NOT_FOUND, message)


def _validate_page(page: int, page_size: int) -> None:
    if page < 1:
        raise _validation_error("页码必须大于等于 1")
    if page_size < 1 or page_size > 100:
        raise _validation_error("每页数量必须在 1 到 100 之间")


def _validate_days(days: int) -> None:
    if days < 1 or days > 3650:
        raise _validation_error("统计天数必须在 1 到 3650 之间")


def _validate_limit(limit: int) -> None:
    if limit < 1 or limit > 10000:
        raise _validation_error("导出数量必须在 1 到 10000 之间")


def _parse_date(value: str | None, field_name: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise _validation_error(f"{field_name} 必须是 YYYY-MM-DD 格式") from exc


def _date_range(start_date: str | None, end_date: str | None) -> tuple[datetime | None, datetime | None]:
    start_at = _parse_date(start_date, "start_date")
    end_at = _parse_date(end_date, "end_date")
    end_before = end_at + timedelta(days=1) if end_at else None
    return start_at, end_before


def _json_value(raw: Any) -> Any:
    if not raw:
        return None
    if not isinstance(raw, str):
        return raw
    try:
        return json.loads(raw)
    except Exception:
        return raw


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _log_list_item(log: Any) -> dict:
    return {
        "id": log.id,
        "log_type": log.log_type,
        "log_type_label": log_type_label(log.log_type),
        "action": log.action,
        "action_label": action_label(log.action),
        "operator_id": log.operator_id,
        "operator_name": log.operator_name or SYSTEM_OPERATOR_NAME,
        "target_type": log.target_type,
        "target_id": log.target_id,
        "target_name": log.target_name,
        "ip_address": log.ip_address,
        "status": log.status,
        "error_message": log.error_message,
        "created_at": _iso(log.created_at),
    }


def _log_detail(log: Any) -> dict:
    item = _log_list_item(log)
    item.update(
        {
            "user_agent": log.user_agent,
            "detail": _json_value(log.detail),
            "old_value": _json_value(log.old_value),
            "new_value": _json_value(log.new_value),
        }
    )
    return item


def _date_key(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


class GetOperationLogTypesUseCase:
    def execute(self) -> dict:
        return {"types": LOG_TYPES, "actions": LOG_ACTIONS}


class ListOperationLogsUseCase:
    def __init__(self, *, logs: OperationLogQueryRepository) -> None:
        self.logs = logs

    def execute(self, query: ListOperationLogsQuery) -> dict:
        _validate_page(query.page, query.page_size)
        start_at, end_before = _date_range(query.start_date, query.end_date)
        total, rows = self.logs.list_logs(
            page=query.page,
            page_size=query.page_size,
            log_type=query.log_type,
            action=query.action,
            operator_id=query.operator_id,
            operator_name=query.operator_name,
            target_type=query.target_type,
            target_id=query.target_id,
            status=query.status,
            start_at=start_at,
            end_before=end_before,
            search=query.search,
        )
        return {
            "total": total,
            "page": query.page,
            "page_size": query.page_size,
            "items": [_log_list_item(row) for row in rows],
        }


class GetOperationLogDetailUseCase:
    def __init__(self, *, logs: OperationLogQueryRepository) -> None:
        self.logs = logs

    def execute(self, query: GetOperationLogDetailQuery) -> dict:
        log = self.logs.get_log_by_id(query.log_id)
        if not log:
            raise _not_found("日志不存在")
        return _log_detail(log)


class GetOperationLogStatisticsUseCase:
    def __init__(self, *, logs: OperationLogQueryRepository) -> None:
        self.logs = logs

    def execute(self, query: GetOperationLogStatisticsQuery) -> dict:
        _validate_days(query.days)
        now = utc_now_naive()
        start_at = now - timedelta(days=query.days)
        type_counts = self.logs.type_distribution_since(start_at)
        status_counts = self.logs.status_distribution_since(start_at)
        daily_counts = self.logs.daily_counts_since(start_at)

        return {
            "period_days": query.days,
            "total": self.logs.count_since(start_at),
            "type_distribution": {
                log_type: {"count": count, "label": log_type_label(log_type)}
                for log_type, count in type_counts.items()
            },
            "status_distribution": status_counts,
            "daily_trend": [
                {"date": _date_key(day), "count": count}
                for day, count in daily_counts
            ],
            "login_failed_count": self.logs.count_action_since("login_failed", start_at),
            "security_event_count": self.logs.count_type_since("SECURITY", start_at),
            "updated_at": now.isoformat(),
        }


class GetUserActivityUseCase:
    def __init__(self, *, logs: OperationLogQueryRepository) -> None:
        self.logs = logs

    def execute(self, query: GetUserActivityQuery) -> dict:
        _validate_page(query.page, query.page_size)
        total, rows = self.logs.list_user_activity(
            user_id=query.user_id,
            page=query.page,
            page_size=query.page_size,
        )
        return {
            "total": total,
            "page": query.page,
            "page_size": query.page_size,
            "items": [
                {
                    "id": log.id,
                    "log_type": log.log_type,
                    "action": log.action,
                    "action_label": action_label(log.action),
                    "operator_name": log.operator_name or SYSTEM_OPERATOR_NAME,
                    "target_name": log.target_name,
                    "ip_address": log.ip_address,
                    "status": log.status,
                    "created_at": _iso(log.created_at),
                    "is_operator": log.operator_id == query.user_id,
                }
                for log in rows
            ],
        }


class ExportOperationLogsUseCase:
    def __init__(self, *, logs: OperationLogQueryRepository) -> None:
        self.logs = logs

    def execute(self, query: ExportOperationLogsQuery) -> list[dict]:
        _validate_limit(query.limit)
        start_at, end_before = _date_range(query.start_date, query.end_date)
        rows = self.logs.export_logs(
            log_type=query.log_type,
            start_at=start_at,
            end_before=end_before,
            limit=query.limit,
        )
        return [
            {
                "时间": log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else "",
                "类型": log_type_label(log.log_type),
                "操作": action_label(log.action),
                "操作者": log.operator_name or SYSTEM_OPERATOR_NAME,
                "目标": log.target_name or "",
                "IP地址": log.ip_address or "",
                "状态": status_label(log.status),
                "错误信息": log.error_message or "",
            }
            for log in rows
        ]
