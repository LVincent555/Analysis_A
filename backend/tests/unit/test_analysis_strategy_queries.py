from __future__ import annotations

import asyncio
from datetime import date
from types import SimpleNamespace

from app.contexts.analysis.application.queries import (
    GetNeedleUnder20StockDetailQuery,
    GetNeedleUnder20StocksQuery,
)
from app.contexts.analysis.application.strategy_queries import (
    GetNeedleUnder20StockDetailUseCase,
    GetNeedleUnder20StocksUseCase,
)
from app.contexts.analysis.infrastructure.strategy_queries import LegacyNeedleUnder20StrategyAdapter


class FakeStrategyPort:
    def __init__(self) -> None:
        self.list_query: GetNeedleUnder20StocksQuery | None = None
        self.detail_query: GetNeedleUnder20StockDetailQuery | None = None

    async def get_needle_under_20_stocks(self, query: GetNeedleUnder20StocksQuery) -> dict:
        self.list_query = query
        return {"data": []}

    def get_needle_under_20_stock_detail(self, query: GetNeedleUnder20StockDetailQuery) -> dict:
        self.detail_query = query
        return {"stock_code": query.stock_code}


class FakeApiCache:
    def __init__(self) -> None:
        self.get_calls: list[tuple[str, str]] = []
        self.set_calls: list[tuple[str, str, dict, int]] = []

    def get_api_cache(self, namespace: str, key: str):
        self.get_calls.append((namespace, key))
        return None

    def set_api_cache(self, namespace: str, key: str, value: dict, *, ttl: int) -> None:
        self.set_calls.append((namespace, key, value, ttl))


class FakeNumpyCache:
    def get_latest_date(self):
        return date(2026, 7, 8)

    def get_dates_range(self, days: int):
        return [date(2026, 7, 8), date(2026, 7, 7)]

    def get_all_stocks(self):
        return {"000001": "one"}

    def get_stock_data_for_strategy(self, stock_code, target_date, lookback_days=30):
        return {
            "stock_code": stock_code,
            "stock_name": "Ping An",
            "signal_date": target_date.strftime("%Y%m%d"),
            "closes": list(range(20)),
            "highs": list(range(20)),
            "lows": list(range(20)),
            "opens": list(range(20)),
            "volumes": list(range(20)),
            "turnovers": list(range(20)),
            "ranks": [20, 10],
            "bbis": list(range(20)),
            "price_changes": [-2.5],
        }

    def get_stock_info(self, stock_code):
        return SimpleNamespace(industry="Bank")


class FakePattern:
    value = "bottom_volume"


class FakeWashout:
    is_valid = True
    bbi_break = False
    price_change_pct = -2.5
    pattern = FakePattern()
    pattern_name = "Bottom Volume"
    score = 88

    def to_dict(self) -> dict:
        return {"score": self.score}


class FakeDetector:
    def detect(self, closes, highs, lows, bbis):
        return FakeWashout()


class FakeStrategyResult:
    def to_dict(self) -> dict:
        return {"total_score": 88}


class FakeStrategy:
    def analyze(self, **kwargs):
        return FakeStrategyResult()


def test_strategy_use_cases_delegate_to_port() -> None:
    port = FakeStrategyPort()
    list_query = GetNeedleUnder20StocksQuery(date="20260708", days=7, long_period=21)
    detail_query = GetNeedleUnder20StockDetailQuery(stock_code="000001", date="20260708")

    list_result = asyncio.run(GetNeedleUnder20StocksUseCase(port).execute(list_query))
    detail_result = GetNeedleUnder20StockDetailUseCase(port).execute(detail_query)

    assert list_result == {"data": []}
    assert detail_result == {"stock_code": "000001"}
    assert port.list_query == list_query
    assert port.detail_query == detail_query


def test_legacy_strategy_adapter_computes_and_caches_list_query() -> None:
    api_cache = FakeApiCache()
    adapter = LegacyNeedleUnder20StrategyAdapter(
        numpy_cache_backend=FakeNumpyCache(),
        api_cache=api_cache,
        detector_factory=lambda **kwargs: FakeDetector(),
    )

    result = asyncio.run(
        adapter.get_needle_under_20_stocks(
            GetNeedleUnder20StocksQuery(
                date="20260708",
                days=5,
                pattern="bottom_volume",
                max_drop_pct=5.0,
                long_period=10,
            )
        )
    )

    assert result["total_count"] == 1
    assert result["data"][0]["stock_code"] == "000001"
    assert result["data"][0]["rank"] == 1
    assert result["industry_distribution"] == {"Bank": 1}
    assert api_cache.get_calls == [("needle20", "needle20:20260708:5:0:bottom_volume:True:5.0:10")]
    assert api_cache.set_calls[0][0] == "needle20"
    assert api_cache.set_calls[0][3] == 90000


def test_legacy_strategy_adapter_returns_detail_with_industry() -> None:
    adapter = LegacyNeedleUnder20StrategyAdapter(
        numpy_cache_backend=FakeNumpyCache(),
        api_cache=FakeApiCache(),
        strategy_factory=FakeStrategy,
    )

    result = adapter.get_needle_under_20_stock_detail(
        GetNeedleUnder20StockDetailQuery(stock_code="000001", date="20260708")
    )

    assert result == {"total_score": 88, "industry": "Bank"}
