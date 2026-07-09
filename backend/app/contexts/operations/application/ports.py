"""Operations application ports."""

from datetime import datetime
from typing import Any, Protocol


class OperationLogQueryRepository(Protocol):
    def list_logs(
        self,
        *,
        page: int,
        page_size: int,
        log_type: str | None,
        action: str | None,
        operator_id: int | None,
        operator_name: str | None,
        target_type: str | None,
        target_id: int | None,
        status: str | None,
        start_at: datetime | None,
        end_before: datetime | None,
        search: str | None,
    ) -> tuple[int, list[Any]]:
        ...

    def get_log_by_id(self, log_id: int) -> Any | None:
        ...

    def type_distribution_since(self, start_at: datetime) -> dict[str, int]:
        ...

    def status_distribution_since(self, start_at: datetime) -> dict[str | None, int]:
        ...

    def daily_counts_since(self, start_at: datetime) -> list[tuple[Any, int]]:
        ...

    def count_action_since(self, action: str, start_at: datetime) -> int:
        ...

    def count_type_since(self, log_type: str, start_at: datetime) -> int:
        ...

    def count_since(self, start_at: datetime) -> int:
        ...

    def list_user_activity(self, *, user_id: int, page: int, page_size: int) -> tuple[int, list[Any]]:
        ...

    def export_logs(
        self,
        *,
        log_type: str | None,
        start_at: datetime | None,
        end_before: datetime | None,
        limit: int,
    ) -> list[Any]:
        ...


class OperationLogCommandRepository(Protocol):
    def record(
        self,
        *,
        log_type: str,
        action: str,
        operator_id: int | None,
        operator_name: str | None,
        target_type: str | None = None,
        target_id: int | None = None,
        target_name: str | None = None,
        ip_address: str | None = None,
        detail: dict | None = None,
        old_value: dict | None = None,
        new_value: dict | None = None,
        status: str = "success",
    ) -> None:
        ...

    def delete_before(self, cutoff: datetime) -> int:
        ...

    def commit(self) -> None:
        ...


class SystemConfigRepository(Protocol):
    def get_by_key(self, key: str) -> Any | None:
        ...

    def list_configs(self, category: str | None = None) -> list[Any]:
        ...

    def set_value(self, config: Any, serialized_value: str, operator_id: int, updated_at: datetime) -> None:
        ...

    def commit(self) -> None:
        ...


class ConfigCacheReloader(Protocol):
    def reload(self) -> None:
        ...


class CacheManagementPort(Protocol):
    def get_numpy_stats(self) -> dict:
        ...

    def get_hotspots_stats(self) -> dict:
        ...

    def get_unified_stats(self) -> dict:
        ...

    def get_region_specs(self) -> dict:
        ...

    def clear_hotspots_cache(self) -> None:
        ...

    def clear_api_cache(self) -> None:
        ...

    def clear_report_cache(self) -> None:
        ...

    def clear_region(self, region_name: str) -> None:
        ...

    def reload_all(self) -> None:
        ...

    def reload_numpy_cache(self) -> None:
        ...

    def reload_hotspots_cache(self) -> None:
        ...

    def reload_config_cache(self) -> None:
        ...

    def gc(self) -> dict:
        ...
