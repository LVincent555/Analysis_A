from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app.contexts.market_data.application.queries import (
    GetSectorRawDataQuery,
    GetSectorTrendQuery,
)
from app.contexts.market_data.application.sector_queries import GetSectorRawDataUseCase, GetSectorTrendUseCase
from app.contexts.market_data.infrastructure.sector_queries import LegacySectorQueryAdapter


class FakeSectorPort:
    def __init__(self) -> None:
        self.raw_query: GetSectorRawDataQuery | None = None
        self.trend_query: GetSectorTrendQuery | None = None

    def get_sector_raw_data(self, query: GetSectorRawDataQuery) -> dict:
        self.raw_query = query
        return {"data": []}

    def get_sector_trend(self, query: GetSectorTrendQuery) -> dict:
        self.trend_query = query
        return {"sectors": []}


class FakeSectorService:
    def get_available_dates(self) -> list[str]:
        return ["20260708"]

    def get_sector_ranking(self, target_date=None, limit: int = 100) -> dict:
        return {"date": target_date, "limit": limit}

    def search_sectors(self, keyword: str) -> list[str]:
        return [keyword]

    def get_sector_detail(self, sector_name: str, days: int = 30, target_date=None) -> dict:
        return {"name": sector_name, "days": days, "date": target_date}


class FakeSectorCache:
    def get_sector_latest_date(self):
        return date(2026, 7, 8)

    def get_top_n_sectors(self, target_date, limit: int) -> list[dict]:
        return [
            {
                "sector_id": 1,
                "rank": 1,
                "total_score": 99.0,
                "price_change": 2.0,
                "open_price": 10.0,
                "high_price": 11.0,
                "low_price": 9.5,
                "close_price": 10.8,
                "turnover_rate": 1.5,
                "volume_days": 3,
                "avg_volume_ratio_50": 1.1,
                "volume": 100000,
                "volatility": 5.0,
                "beta": 1.0,
                "correlation": 0.5,
                "long_term": 1.0,
                "short_term": 2,
                "overbought": 0,
                "oversold": 0,
                "macd_signal": 1.0,
                "rsi": 60.0,
                "dif": 0.1,
                "dem": 0.2,
                "adx": 20.0,
                "slowk": 55.0,
            }
        ][:limit]

    def get_sector_info(self, sector_id: int):
        return SimpleNamespace(sector_name="银行")

    def get_sector_dates_range(self, days: int) -> list[date]:
        return [date(2026, 7, 8), date(2026, 7, 7), date(2026, 7, 6)]

    def get_sector_history(self, sector_id: int, days: int, end_date=None) -> list[dict]:
        return [
            {"date": "20260706", "rank": 3, "total_score": 90.0},
            {"date": "20260707", "rank": 2, "total_score": 95.0},
            {"date": "20260708", "rank": 1, "total_score": 99.0},
        ][:days]


def test_sector_query_use_cases_delegate_to_port() -> None:
    port = FakeSectorPort()

    raw_result = GetSectorRawDataUseCase(port).execute(GetSectorRawDataQuery(target_date="20260708", limit=20))
    trend_result = GetSectorTrendUseCase(port).execute(GetSectorTrendQuery(days=3, limit=5, target_date="20260708"))

    assert raw_result == {"data": []}
    assert port.raw_query == GetSectorRawDataQuery(target_date="20260708", limit=20)
    assert trend_result == {"sectors": []}
    assert port.trend_query == GetSectorTrendQuery(days=3, limit=5, target_date="20260708")


def test_legacy_sector_adapter_builds_raw_data_from_cache() -> None:
    adapter = LegacySectorQueryAdapter(sector_service=FakeSectorService(), sector_cache=FakeSectorCache())

    result = adapter.get_sector_raw_data(GetSectorRawDataQuery(limit=10))

    assert result["date"] == "20260708"
    assert result["total_count"] == 1
    assert result["data"][0]["name"] == "银行"
    assert result["data"][0]["rank"] == 1
    assert result["data"][0]["slowk"] == 55.0


def test_legacy_sector_adapter_builds_trend_from_cache() -> None:
    adapter = LegacySectorQueryAdapter(sector_service=FakeSectorService(), sector_cache=FakeSectorCache())

    result = adapter.get_sector_trend(GetSectorTrendQuery(days=3, limit=1, target_date="20260708"))

    assert result == {
        "dates": ["20260706", "20260707", "20260708"],
        "sectors": [
            {
                "name": "银行",
                "ranks": [3, 2, 1],
                "scores": [90.0, 95.0, 99.0],
            }
        ],
    }
