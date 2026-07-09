from __future__ import annotations

from app.contexts.analysis.application.basic_queries import (
    AnalyzePeriodUseCase,
    GetMarketVolatilitySummaryUseCase,
    ListAvailableDatesUseCase,
)
from app.contexts.analysis.application.queries import AnalyzePeriodQuery, MarketVolatilitySummaryQuery
from app.contexts.analysis.infrastructure.basic_analysis import LegacyBasicAnalysisQueryAdapter


class FakeBasicAnalysisPort:
    def __init__(self) -> None:
        self.period_query: AnalyzePeriodQuery | None = None
        self.volatility_query: MarketVolatilitySummaryQuery | None = None

    def get_available_dates(self) -> list[str]:
        return ["20260708", "20260707"]

    def analyze_period(self, query: AnalyzePeriodQuery) -> dict:
        self.period_query = query
        return {"kind": "period"}

    def get_market_volatility_summary(self, query: MarketVolatilitySummaryQuery) -> dict:
        self.volatility_query = query
        return {"current": 2.5}


class FakeAnalysisService:
    def __init__(self) -> None:
        self.kwargs: dict | None = None

    def get_available_dates(self) -> list[str]:
        return ["20260708"]

    def analyze_period(self, period: int, **kwargs):
        self.kwargs = {"period": period, **kwargs}
        return {"ok": True}


class FakeVolatilityCache:
    def __init__(self) -> None:
        self.days: int | None = None

    def get_market_volatility_summary(self, *, days: int) -> dict:
        self.days = days
        return {"current": 1.8, "days": []}


def test_basic_analysis_use_cases_delegate_to_port() -> None:
    port = FakeBasicAnalysisPort()

    dates = ListAvailableDatesUseCase(port).execute()
    period_result = AnalyzePeriodUseCase(port).execute(
        AnalyzePeriodQuery(period=5, max_count=400, board_type="bjs", target_date="20260708")
    )
    volatility_result = GetMarketVolatilitySummaryUseCase(port).execute(MarketVolatilitySummaryQuery(days=7))

    assert dates == ["20260708", "20260707"]
    assert period_result == {"kind": "period"}
    assert port.period_query == AnalyzePeriodQuery(
        period=5,
        max_count=400,
        board_type="bjs",
        target_date="20260708",
    )
    assert volatility_result == {"current": 2.5}
    assert port.volatility_query == MarketVolatilitySummaryQuery(days=7)


def test_legacy_basic_analysis_adapter_translates_queries() -> None:
    analysis_service = FakeAnalysisService()
    volatility_cache = FakeVolatilityCache()
    adapter = LegacyBasicAnalysisQueryAdapter(
        analysis_service=analysis_service,
        volatility_cache=volatility_cache,
    )

    assert adapter.get_available_dates() == ["20260708"]
    assert adapter.analyze_period(
        AnalyzePeriodQuery(period=3, max_count=200, board_type="main", target_date="20260708")
    ) == {"ok": True}
    assert adapter.get_market_volatility_summary(MarketVolatilitySummaryQuery(days=4)) == {
        "current": 1.8,
        "days": [],
    }

    assert analysis_service.kwargs == {
        "period": 3,
        "max_count": 200,
        "board_type": "main",
        "target_date": "20260708",
    }
    assert volatility_cache.days == 4
