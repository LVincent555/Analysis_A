"""Market data query DTOs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StockSignalThresholdSettings:
    hot_list_mode: str = "frequent"
    hot_list_version: str = "v2"
    hot_list_top: int = 100
    hot_list_top2: int = 500
    hot_list_top3: int = 2000
    hot_list_top4: int = 3000
    rank_jump_min: int = 1000
    rank_jump_large: int = 3000
    steady_rise_days_min: int = 3
    price_surge_min: float = 5.0
    volume_surge_min: float = 10.0
    volatility_surge_min: float = 10.0


@dataclass(frozen=True, slots=True)
class GetStockRawDataQuery:
    target_date: str | None = None
    limit: int = 5000


@dataclass(frozen=True, slots=True)
class SearchStockFullQuery:
    keyword: str
    limit: int = 5


@dataclass(frozen=True, slots=True)
class SearchStockQuery:
    keyword: str
    target_date: str | None = None
    signal_thresholds: StockSignalThresholdSettings | None = None


@dataclass(frozen=True, slots=True)
class GetSectorRankingQuery:
    target_date: str | None = None
    limit: int = 100


@dataclass(frozen=True, slots=True)
class GetSectorRawDataQuery:
    target_date: str | None = None
    limit: int = 600


@dataclass(frozen=True, slots=True)
class SearchSectorsQuery:
    keyword: str


@dataclass(frozen=True, slots=True)
class GetSectorTrendQuery:
    days: int = 7
    limit: int = 10
    target_date: str | None = None


@dataclass(frozen=True, slots=True)
class GetSectorRankChangesQuery:
    target_date: str | None = None
    compare_days: int = 1


@dataclass(frozen=True, slots=True)
class GetSectorDetailQuery:
    sector_name: str
    days: int = 30
    target_date: str | None = None


@dataclass(frozen=True, slots=True)
class OfflineSyncUserSettings:
    offline_days: int
    offline_enabled: bool


@dataclass(frozen=True, slots=True)
class GetOfflineSyncStatusQuery:
    user_settings: OfflineSyncUserSettings


@dataclass(frozen=True, slots=True)
class GetIncrementalSyncQuery:
    since: str
    user_settings: OfflineSyncUserSettings


@dataclass(frozen=True, slots=True)
class GetDailySyncQuery:
    date: str
    limit: int = 1000
    offset: int = 0
    user_settings: OfflineSyncUserSettings | None = None


@dataclass(frozen=True, slots=True)
class GetOfflineStocksQuery:
    user_settings: OfflineSyncUserSettings


@dataclass(frozen=True, slots=True)
class GetOfflineDatesQuery:
    user_settings: OfflineSyncUserSettings
