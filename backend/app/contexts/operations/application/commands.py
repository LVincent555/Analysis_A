"""Operations command DTOs."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CleanupOperationLogsCommand:
    days: int = 90


@dataclass(frozen=True, slots=True)
class UpdateSystemConfigCommand:
    key: str
    value: object
    operator_id: int
    operator_name: str
    ip_address: str | None = None


@dataclass(frozen=True, slots=True)
class BatchUpdateSystemConfigsCommand:
    updates: dict[str, object]
    operator_id: int
    operator_name: str
    ip_address: str | None = None


@dataclass(frozen=True, slots=True)
class ResetSystemConfigCommand:
    key: str
    operator_id: int
    operator_name: str
    ip_address: str | None = None


@dataclass(frozen=True, slots=True)
class ClearCacheCommand:
    cache_type: str = "all"
