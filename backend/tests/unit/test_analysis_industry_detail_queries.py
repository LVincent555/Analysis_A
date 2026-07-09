from __future__ import annotations

from app.contexts.analysis.application.industry_detail_queries import (
    CompareIndustriesUseCase,
    GetIndustryStocksUseCase,
)
from app.contexts.analysis.application.queries import (
    CompareIndustriesQuery,
    GetIndustryStocksQuery,
    IndustryDetailSignalThresholdSettings,
)
from app.contexts.analysis.infrastructure.industry_detail_queries import LegacyIndustryDetailAnalysisAdapter
from app.services.signal_calculator import SignalThresholds


class FakeIndustryDetailPort:
    def __init__(self) -> None:
        self.stocks_query: GetIndustryStocksQuery | None = None
        self.compare_query: CompareIndustriesQuery | None = None

    def get_industry_stocks(self, query: GetIndustryStocksQuery) -> dict:
        self.stocks_query = query
        return {"industry": query.industry_name}

    def compare_industries(self, query: CompareIndustriesQuery) -> dict:
        self.compare_query = query
        return {"industries": query.industry_names}


class FakeIndustryDetailService:
    def __init__(self) -> None:
        self.stocks_kwargs: dict | None = None
        self.compare_kwargs: dict | None = None

    def get_industry_stocks(self, **kwargs):
        self.stocks_kwargs = kwargs
        return {"ok": True}

    def get_industry_detail(self, **kwargs):
        return {"ok": True}

    def get_industry_trend(self, **kwargs):
        return {"ok": True}

    def compare_industries(self, **kwargs):
        self.compare_kwargs = kwargs
        return {"ok": True}


def test_industry_detail_use_cases_delegate_to_port() -> None:
    port = FakeIndustryDetailPort()

    stocks = GetIndustryStocksUseCase(port).execute(
        GetIndustryStocksQuery(
            industry_name="银行",
            target_date="20260708",
            signal_thresholds=IndustryDetailSignalThresholdSettings(),
        )
    )
    compare = CompareIndustriesUseCase(port).execute(
        CompareIndustriesQuery(industry_names=["银行", "证券"], target_date="20260708", k=0.8)
    )

    assert stocks == {"industry": "银行"}
    assert port.stocks_query is not None
    assert port.stocks_query.industry_name == "银行"
    assert compare == {"industries": ["银行", "证券"]}
    assert port.compare_query == CompareIndustriesQuery(
        industry_names=["银行", "证券"],
        target_date="20260708",
        k=0.8,
    )


def test_legacy_industry_detail_adapter_translates_thresholds_and_compare() -> None:
    service = FakeIndustryDetailService()
    adapter = LegacyIndustryDetailAnalysisAdapter(industry_service=service)

    adapter.get_industry_stocks(
        GetIndustryStocksQuery(
            industry_name="银行",
            target_date="20260708",
            sort_mode="signal",
            calculate_signals=True,
            signal_thresholds=IndustryDetailSignalThresholdSettings(
                hot_list_mode="instant",
                hot_list_version="v1",
                hot_list_top=200,
                rank_jump_min=2500,
                steady_rise_days_min=4,
            ),
        )
    )
    adapter.compare_industries(CompareIndustriesQuery(["银行", "证券"], target_date="20260708", k=0.7))

    assert service.stocks_kwargs is not None
    assert service.stocks_kwargs["industry_name"] == "银行"
    assert service.stocks_kwargs["target_date"] == "20260708"
    assert service.stocks_kwargs["sort_mode"] == "signal"
    thresholds = service.stocks_kwargs["signal_thresholds"]
    assert isinstance(thresholds, SignalThresholds)
    assert thresholds.hot_list_mode == "instant"
    assert thresholds.hot_list_version == "v1"
    assert thresholds.hot_list_top == 200
    assert thresholds.rank_jump_min == 2500
    assert thresholds.steady_rise_days_min == 4
    assert thresholds.steady_rise_days_large == 5
    assert thresholds.volatility_surge_large == 100.0

    assert service.compare_kwargs == {
        "industry_names": ["银行", "证券"],
        "target_date": "20260708",
        "k_value": 0.7,
    }
