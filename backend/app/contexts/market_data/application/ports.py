"""Market data application ports."""

from __future__ import annotations

from typing import Any, Protocol

from .queries import (
    GetSectorDetailQuery,
    GetSectorRankChangesQuery,
    GetSectorRankingQuery,
    GetSectorRawDataQuery,
    GetSectorTrendQuery,
    GetDailySyncQuery,
    GetIncrementalSyncQuery,
    GetOfflineDatesQuery,
    GetOfflineStocksQuery,
    GetOfflineSyncStatusQuery,
    GetStockRawDataQuery,
    SearchSectorsQuery,
    SearchStockFullQuery,
    SearchStockQuery,
)


class StockQueryPort(Protocol):
    def get_stock_raw_data(self, query: GetStockRawDataQuery) -> dict | None:
        ...

    def search_stock_full(self, query: SearchStockFullQuery) -> list[Any]:
        ...

    def search_stock(self, query: SearchStockQuery) -> Any | None:
        ...


class SectorQueryPort(Protocol):
    def get_available_dates(self) -> list[str]:
        ...

    def get_sector_ranking(self, query: GetSectorRankingQuery) -> Any:
        ...

    def get_sector_raw_data(self, query: GetSectorRawDataQuery) -> dict:
        ...

    def search_sectors(self, query: SearchSectorsQuery) -> list[str]:
        ...

    def get_sector_trend(self, query: GetSectorTrendQuery) -> dict:
        ...

    def get_sector_rank_changes(self, query: GetSectorRankChangesQuery) -> dict:
        ...

    def get_sector_detail(self, query: GetSectorDetailQuery) -> Any | None:
        ...


class OfflineSyncQueryPort(Protocol):
    def get_sync_status(self, query: GetOfflineSyncStatusQuery) -> dict:
        ...

    def get_incremental_sync(self, query: GetIncrementalSyncQuery) -> dict:
        ...

    def get_daily_sync(self, query: GetDailySyncQuery) -> dict:
        ...

    def get_stocks(self, query: GetOfflineStocksQuery) -> dict:
        ...

    def get_dates(self, query: GetOfflineDatesQuery) -> dict:
        ...
