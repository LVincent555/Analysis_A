from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app.contexts.market_data.application.queries import (
    GetStockRawDataQuery,
    SearchStockFullQuery,
    SearchStockQuery,
    StockSignalThresholdSettings,
)
from app.contexts.market_data.application.stock_queries import (
    GetStockRawDataUseCase,
    SearchStockFullUseCase,
    SearchStockUseCase,
)
from app.contexts.market_data.infrastructure.stock_queries import LegacyStockQueryAdapter
from app.services.signal_calculator import SignalThresholds


class FakeStockPort:
    def __init__(self) -> None:
        self.raw_query: GetStockRawDataQuery | None = None
        self.full_query: SearchStockFullQuery | None = None
        self.stock_query: SearchStockQuery | None = None

    def get_stock_raw_data(self, query: GetStockRawDataQuery) -> dict:
        self.raw_query = query
        return {"data": []}

    def search_stock_full(self, query: SearchStockFullQuery) -> list[dict]:
        self.full_query = query
        return [{"code": "600000"}]

    def search_stock(self, query: SearchStockQuery) -> dict:
        self.stock_query = query
        return {"code": "600000"}


class FakeStockService:
    def __init__(self) -> None:
        self.full_args: tuple | None = None
        self.search_kwargs: dict | None = None

    def search_stock_full(self, keyword: str, limit: int) -> list[dict]:
        self.full_args = (keyword, limit)
        return [{"code": keyword}]

    def search_stock(self, keyword: str, **kwargs) -> dict:
        self.search_kwargs = {"keyword": keyword, **kwargs}
        return {"code": keyword}


class FakeStockCache:
    def get_latest_date(self):
        return date(2026, 7, 8)

    def get_top_n_by_rank(self, target_date, limit: int) -> list[dict]:
        return [
            {
                "stock_code": "600000",
                "rank": 1,
                "total_score": 99.5,
                "price_change": 2.1,
                "close_price": 10.5,
                "turnover_rate": 1.2,
                "volume_days": 3,
                "avg_volume_ratio_50": 1.1,
                "volatility": 4.5,
                "market_cap": 100.0,
            }
        ][:limit]

    def get_stock_info(self, stock_code: str):
        return SimpleNamespace(stock_name="浦发银行", industry="银行")


def test_stock_query_use_cases_delegate_to_port() -> None:
    port = FakeStockPort()

    raw_result = GetStockRawDataUseCase(port).execute(GetStockRawDataQuery(target_date="20260708", limit=20))
    full_result = SearchStockFullUseCase(port).execute(SearchStockFullQuery(keyword="浦发", limit=3))
    stock_result = SearchStockUseCase(port).execute(
        SearchStockQuery(keyword="600000", signal_thresholds=StockSignalThresholdSettings())
    )

    assert raw_result == {"data": []}
    assert port.raw_query == GetStockRawDataQuery(target_date="20260708", limit=20)
    assert full_result == [{"code": "600000"}]
    assert port.full_query == SearchStockFullQuery(keyword="浦发", limit=3)
    assert stock_result == {"code": "600000"}
    assert port.stock_query == SearchStockQuery(
        keyword="600000",
        signal_thresholds=StockSignalThresholdSettings(),
    )


def test_legacy_stock_adapter_builds_raw_data_from_cache() -> None:
    adapter = LegacyStockQueryAdapter(stock_service=FakeStockService(), stock_cache=FakeStockCache())

    result = adapter.get_stock_raw_data(GetStockRawDataQuery(limit=10))

    assert result == {
        "date": "20260708",
        "total_count": 1,
        "data": [
            {
                "code": "600000",
                "name": "浦发银行",
                "industry": "银行",
                "rank": 1,
                "total_score": 99.5,
                "price_change": 2.1,
                "close_price": 10.5,
                "turnover_rate": 1.2,
                "volume_days": 3,
                "avg_volume_ratio_50": 1.1,
                "volatility": 4.5,
                "market_cap": 100.0,
            }
        ],
    }


def test_legacy_stock_adapter_translates_service_queries_and_thresholds() -> None:
    stock_service = FakeStockService()
    adapter = LegacyStockQueryAdapter(stock_service=stock_service, stock_cache=FakeStockCache())

    assert adapter.search_stock_full(SearchStockFullQuery(keyword="浦发", limit=2)) == [{"code": "浦发"}]
    assert stock_service.full_args == ("浦发", 2)

    result = adapter.search_stock(
        SearchStockQuery(
            keyword="600000",
            target_date="20260708",
            signal_thresholds=StockSignalThresholdSettings(
                hot_list_mode="instant",
                hot_list_version="v1",
                hot_list_top=200,
                rank_jump_min=1500,
                steady_rise_days_min=4,
                price_surge_min=6.0,
            ),
        )
    )

    assert result == {"code": "600000"}
    assert stock_service.search_kwargs is not None
    assert stock_service.search_kwargs["target_date"] == "20260708"
    thresholds = stock_service.search_kwargs["signal_thresholds"]
    assert isinstance(thresholds, SignalThresholds)
    assert thresholds.hot_list_mode == "instant"
    assert thresholds.hot_list_version == "v1"
    assert thresholds.hot_list_top == 200
    assert thresholds.rank_jump_min == 1500
    assert thresholds.steady_rise_days_min == 4
    assert thresholds.price_surge_min == 6.0
