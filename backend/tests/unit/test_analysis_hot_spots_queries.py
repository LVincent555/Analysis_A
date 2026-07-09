from __future__ import annotations

from datetime import date

from app.contexts.analysis.application.hot_spots_queries import GetHotSpotsFullUseCase
from app.contexts.analysis.application.queries import GetHotSpotsFullQuery
from app.contexts.analysis.infrastructure.hot_spots_queries import LegacyHotSpotsAnalysisAdapter


class FakeHotSpotsPort:
    def __init__(self) -> None:
        self.query: GetHotSpotsFullQuery | None = None

    def get_hot_spots_full(self, query: GetHotSpotsFullQuery) -> dict:
        self.query = query
        return {"date": query.date, "stocks": []}


class FakeNumpyCache:
    def get_latest_date(self):
        return date(2026, 7, 8)


class FakeHotSpotsCache:
    calls: list[str] = []

    @classmethod
    def get_full_data(cls, date_value: str):
        cls.calls.append(date_value)
        return [{"code": "000001"}]


class FakeApiCache:
    def __init__(self) -> None:
        self.get_calls: list[tuple[str, str]] = []
        self.set_calls: list[tuple[str, str, dict, int]] = []

    def get_api_cache(self, namespace: str, key: str):
        self.get_calls.append((namespace, key))
        return None

    def set_api_cache(self, namespace: str, key: str, value: dict, *, ttl: int) -> None:
        self.set_calls.append((namespace, key, value, ttl))


def test_hot_spots_use_case_delegates_to_port() -> None:
    port = FakeHotSpotsPort()
    query = GetHotSpotsFullQuery(date="20260708")

    result = GetHotSpotsFullUseCase(port).execute(query)

    assert result == {"date": "20260708", "stocks": []}
    assert port.query == query


def test_legacy_hot_spots_adapter_uses_latest_date_and_cache() -> None:
    api_cache = FakeApiCache()
    FakeHotSpotsCache.calls = []
    adapter = LegacyHotSpotsAnalysisAdapter(
        numpy_cache_backend=FakeNumpyCache(),
        hot_spots_cache=FakeHotSpotsCache,
        api_cache=api_cache,
    )

    result = adapter.get_hot_spots_full(GetHotSpotsFullQuery())

    assert result == {
        "date": "20260708",
        "total_count": 1,
        "stocks": [{"code": "000001"}],
    }
    assert FakeHotSpotsCache.calls == ["20260708"]
    assert api_cache.get_calls == [("hotspots", "hotspots_full_20260708")]
    assert api_cache.set_calls[0][0] == "hotspots"
    assert api_cache.set_calls[0][3] == 90000
