"""Operations query DTOs."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ListOperationLogsQuery:
    page: int = 1
    page_size: int = 20
    log_type: str | None = None
    action: str | None = None
    operator_id: int | None = None
    operator_name: str | None = None
    target_type: str | None = None
    target_id: int | None = None
    status: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    search: str | None = None


@dataclass(frozen=True, slots=True)
class GetOperationLogDetailQuery:
    log_id: int


@dataclass(frozen=True, slots=True)
class GetOperationLogStatisticsQuery:
    days: int = 7


@dataclass(frozen=True, slots=True)
class GetUserActivityQuery:
    user_id: int
    page: int = 1
    page_size: int = 20


@dataclass(frozen=True, slots=True)
class ExportOperationLogsQuery:
    log_type: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    limit: int = 1000


@dataclass(frozen=True, slots=True)
class ListSystemConfigsQuery:
    category: str | None = None


@dataclass(frozen=True, slots=True)
class ValidatePasswordPolicyQuery:
    password: str
