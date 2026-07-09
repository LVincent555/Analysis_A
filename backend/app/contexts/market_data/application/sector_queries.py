"""Sector query use cases."""

from __future__ import annotations

from typing import Any

from .ports import SectorQueryPort
from .queries import (
    GetSectorDetailQuery,
    GetSectorRankChangesQuery,
    GetSectorRankingQuery,
    GetSectorRawDataQuery,
    GetSectorTrendQuery,
    SearchSectorsQuery,
)


class GetSectorAvailableDatesUseCase:
    def __init__(self, sector_port: SectorQueryPort) -> None:
        self.sector_port = sector_port

    def execute(self) -> list[str]:
        return self.sector_port.get_available_dates()


class GetSectorRankingUseCase:
    def __init__(self, sector_port: SectorQueryPort) -> None:
        self.sector_port = sector_port

    def execute(self, query: GetSectorRankingQuery) -> Any:
        return self.sector_port.get_sector_ranking(query)


class GetSectorRawDataUseCase:
    def __init__(self, sector_port: SectorQueryPort) -> None:
        self.sector_port = sector_port

    def execute(self, query: GetSectorRawDataQuery) -> dict:
        return self.sector_port.get_sector_raw_data(query)


class SearchSectorsUseCase:
    def __init__(self, sector_port: SectorQueryPort) -> None:
        self.sector_port = sector_port

    def execute(self, query: SearchSectorsQuery) -> list[str]:
        return self.sector_port.search_sectors(query)


class GetSectorTrendUseCase:
    def __init__(self, sector_port: SectorQueryPort) -> None:
        self.sector_port = sector_port

    def execute(self, query: GetSectorTrendQuery) -> dict:
        return self.sector_port.get_sector_trend(query)


class GetSectorRankChangesUseCase:
    def __init__(self, sector_port: SectorQueryPort) -> None:
        self.sector_port = sector_port

    def execute(self, query: GetSectorRankChangesQuery) -> dict:
        return self.sector_port.get_sector_rank_changes(query)


class GetSectorDetailUseCase:
    def __init__(self, sector_port: SectorQueryPort) -> None:
        self.sector_port = sector_port

    def execute(self, query: GetSectorDetailQuery) -> Any | None:
        return self.sector_port.get_sector_detail(query)
