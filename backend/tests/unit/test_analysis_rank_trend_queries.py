from __future__ import annotations

from app.contexts.analysis.application.queries import (
    AnalyzeRankJumpQuery,
    AnalyzeSteadyRiseQuery,
    SignalThresholdSettings,
)
from app.contexts.analysis.application.rank_trend_queries import (
    AnalyzeRankJumpUseCase,
    AnalyzeSteadyRiseUseCase,
)
from app.contexts.analysis.infrastructure.rank_trend_analysis import LegacyRankTrendAnalysisAdapter
from app.services.signal_calculator import SignalThresholds


class FakeAnalysisPort:
    def __init__(self) -> None:
        self.rank_query: AnalyzeRankJumpQuery | None = None
        self.steady_query: AnalyzeSteadyRiseQuery | None = None

    def analyze_rank_jump(self, query: AnalyzeRankJumpQuery) -> dict:
        self.rank_query = query
        return {"kind": "rank"}

    def analyze_steady_rise(self, query: AnalyzeSteadyRiseQuery) -> dict:
        self.steady_query = query
        return {"kind": "steady"}


class FakeRankJumpService:
    def __init__(self) -> None:
        self.kwargs: dict | None = None

    def analyze_rank_jump(self, **kwargs):
        self.kwargs = kwargs
        return {"ok": True}


class FakeSteadyRiseService:
    def __init__(self) -> None:
        self.kwargs: dict | None = None

    def analyze_steady_rise(self, **kwargs):
        self.kwargs = kwargs
        return {"ok": True}


def test_rank_jump_use_case_passes_query_to_port() -> None:
    port = FakeAnalysisPort()
    thresholds = SignalThresholdSettings(rank_jump_min=1200)
    query = AnalyzeRankJumpQuery(
        jump_threshold=2800,
        board_type="bjs",
        sigma_multiplier=1.5,
        target_date="20260708",
        calculate_signals=True,
        signal_thresholds=thresholds,
    )

    result = AnalyzeRankJumpUseCase(port).execute(query)

    assert result == {"kind": "rank"}
    assert port.rank_query == query
    assert port.rank_query.signal_thresholds is thresholds


def test_steady_rise_use_case_passes_query_to_port() -> None:
    port = FakeAnalysisPort()
    thresholds = SignalThresholdSettings(steady_rise_days_min=5)
    query = AnalyzeSteadyRiseQuery(
        period=5,
        board_type="all",
        min_rank_improvement=300,
        sigma_multiplier=2.0,
        target_date="20260708",
        calculate_signals=True,
        signal_thresholds=thresholds,
    )

    result = AnalyzeSteadyRiseUseCase(port).execute(query)

    assert result == {"kind": "steady"}
    assert port.steady_query == query
    assert port.steady_query.signal_thresholds is thresholds


def test_legacy_adapter_translates_rank_jump_query_and_thresholds() -> None:
    rank_service = FakeRankJumpService()
    adapter = LegacyRankTrendAnalysisAdapter(
        rank_jump_service=rank_service,
        steady_rise_service=FakeSteadyRiseService(),
    )
    query = AnalyzeRankJumpQuery(
        jump_threshold=3000,
        board_type="main",
        sigma_multiplier=1.2,
        target_date="20260708",
        calculate_signals=True,
        signal_thresholds=SignalThresholdSettings(
            hot_list_mode="instant",
            hot_list_version="v1",
            hot_list_top=200,
            rank_jump_min=1500,
            steady_rise_days_min=4,
            steady_rise_days_large=8,
            volatility_surge_min=15.0,
            volatility_surge_large=30.0,
        ),
    )

    adapter.analyze_rank_jump(query)

    assert rank_service.kwargs is not None
    assert rank_service.kwargs["jump_threshold"] == 3000
    assert rank_service.kwargs["target_date"] == "20260708"
    thresholds = rank_service.kwargs["signal_thresholds"]
    assert isinstance(thresholds, SignalThresholds)
    assert thresholds.hot_list_mode == "instant"
    assert thresholds.hot_list_version == "v1"
    assert thresholds.hot_list_top == 200
    assert thresholds.rank_jump_min == 1500
    assert thresholds.steady_rise_days_min == 4
    assert thresholds.steady_rise_days_large == 8
    assert thresholds.volatility_surge_large == 30.0


def test_legacy_adapter_translates_steady_rise_query_without_thresholds() -> None:
    steady_service = FakeSteadyRiseService()
    adapter = LegacyRankTrendAnalysisAdapter(
        rank_jump_service=FakeRankJumpService(),
        steady_rise_service=steady_service,
    )
    query = AnalyzeSteadyRiseQuery(
        period=6,
        board_type="bjs",
        min_rank_improvement=250,
        sigma_multiplier=1.8,
        target_date="20260708",
        calculate_signals=False,
        signal_thresholds=None,
    )

    adapter.analyze_steady_rise(query)

    assert steady_service.kwargs == {
        "period": 6,
        "board_type": "bjs",
        "min_rank_improvement": 250,
        "sigma_multiplier": 1.8,
        "target_date": "20260708",
        "calculate_signals": False,
        "signal_thresholds": None,
    }
