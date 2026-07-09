from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app.contexts.analysis.application.industry_queries import GetIndustryStatsUseCase, GetIndustryTrendUseCase
from app.contexts.analysis.application.queries import GetIndustryStatsQuery, GetIndustryTrendQuery
from app.contexts.analysis.infrastructure.industry_queries import LegacyIndustryAnalysisAdapter


class FakeIndustryPort:
    def __init__(self) -> None:
        self.stats_query: GetIndustryStatsQuery | None = None
        self.trend_query: GetIndustryTrendQuery | None = None

    def get_industry_stats(self, query: GetIndustryStatsQuery) -> list[dict]:
        self.stats_query = query
        return [{"industry": "银行"}]

    def get_industry_trend(self, query: GetIndustryTrendQuery) -> dict:
        self.trend_query = query
        return {"data": []}


class FakeIndustryService:
    def __init__(self) -> None:
        self.args: dict | None = None

    def analyze_industry(self, **kwargs):
        self.args = kwargs
        return []


class FakeCache:
    def __init__(self) -> None:
        self.saved: dict | None = None

    def get_api_cache(self, region: str, key: str):
        return None

    def set_api_cache(self, region: str, key: str, value, ttl: int) -> None:
        self.saved = {"region": region, "key": key, "value": value, "ttl": ttl}


class FakeStockCache:
    def get_latest_date(self):
        return date(2026, 7, 8)

    def get_dates_range(self, days: int):
        return [date(2026, 7, 8), date(2026, 7, 7), date(2026, 7, 6)]

    def get_top_n_by_rank(self, target_date, top_n: int) -> list[dict]:
        return [{"stock_code": "600000"}]

    def get_stocks_batch(self, stock_codes: list[str]) -> dict:
        return {"600000": SimpleNamespace(industry="银行")}


def test_industry_use_cases_delegate_to_port() -> None:
    port = FakeIndustryPort()

    stats = GetIndustryStatsUseCase(port).execute(GetIndustryStatsQuery(period=5, top_n=50))
    trend = GetIndustryTrendUseCase(port).execute(
        GetIndustryTrendQuery(period=7, top_n=100, target_date="20260708")
    )

    assert stats == [{"industry": "银行"}]
    assert port.stats_query == GetIndustryStatsQuery(period=5, top_n=50)
    assert trend == {"data": []}
    assert port.trend_query == GetIndustryTrendQuery(period=7, top_n=100, target_date="20260708")


def test_legacy_industry_adapter_builds_trend_from_cache() -> None:
    api_cache = FakeCache()
    adapter = LegacyIndustryAnalysisAdapter(
        industry_service=FakeIndustryService(),
        stock_cache=FakeStockCache(),
        api_cache=api_cache,
    )

    result = adapter.get_industry_trend(GetIndustryTrendQuery(period=2, top_n=10, target_date="20260708"))

    assert result == {
        "data": [
            {"date": "20260707", "industry_counts": {"银行": 1}},
            {"date": "20260708", "industry_counts": {"银行": 1}},
        ],
        "industries": ["银行"],
    }
    assert api_cache.saved is not None
    assert api_cache.saved["region"] == "industry_trend"
