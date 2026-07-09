"""Offline sync query use cases."""

from __future__ import annotations

from .ports import OfflineSyncQueryPort
from .queries import (
    GetDailySyncQuery,
    GetIncrementalSyncQuery,
    GetOfflineDatesQuery,
    GetOfflineStocksQuery,
    GetOfflineSyncStatusQuery,
)


class OfflineSyncQueryService:
    def __init__(self, sync_port: OfflineSyncQueryPort) -> None:
        self.sync_port = sync_port

    def get_sync_status(self, query: GetOfflineSyncStatusQuery) -> dict:
        return self.sync_port.get_sync_status(query)

    def get_incremental_sync(self, query: GetIncrementalSyncQuery) -> dict:
        return self.sync_port.get_incremental_sync(query)

    def get_daily_sync(self, query: GetDailySyncQuery) -> dict:
        return self.sync_port.get_daily_sync(query)

    def get_stocks(self, query: GetOfflineStocksQuery) -> dict:
        return self.sync_port.get_stocks(query)

    def get_dates(self, query: GetOfflineDatesQuery) -> dict:
        return self.sync_port.get_dates(query)
