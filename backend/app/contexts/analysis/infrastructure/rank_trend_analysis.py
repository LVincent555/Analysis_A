"""Adapters for legacy rank and trend analysis services."""

from __future__ import annotations

from ..application.queries import (
    AnalyzeRankJumpQuery,
    AnalyzeSteadyRiseQuery,
    SignalThresholdSettings,
)
from ....services.rank_jump_service_db import rank_jump_service_db
from ....services.signal_calculator import SignalThresholds
from ....services.steady_rise_service_db import steady_rise_service_db


def _to_legacy_signal_thresholds(settings: SignalThresholdSettings | None) -> SignalThresholds | None:
    if settings is None:
        return None

    return SignalThresholds(
        hot_list_mode=settings.hot_list_mode,
        hot_list_version=settings.hot_list_version,
        hot_list_top=settings.hot_list_top,
        hot_list_top2=settings.hot_list_top2,
        hot_list_top3=settings.hot_list_top3,
        hot_list_top4=settings.hot_list_top4,
        rank_jump_min=settings.rank_jump_min,
        rank_jump_large=settings.rank_jump_large,
        steady_rise_days_min=settings.steady_rise_days_min,
        steady_rise_days_large=settings.steady_rise_days_large,
        price_surge_min=settings.price_surge_min,
        volume_surge_min=settings.volume_surge_min,
        volatility_surge_min=settings.volatility_surge_min,
        volatility_surge_large=settings.volatility_surge_large,
    )


class LegacyRankTrendAnalysisAdapter:
    def __init__(
        self,
        *,
        rank_jump_service=rank_jump_service_db,
        steady_rise_service=steady_rise_service_db,
    ) -> None:
        self.rank_jump_service = rank_jump_service
        self.steady_rise_service = steady_rise_service

    def analyze_rank_jump(self, query: AnalyzeRankJumpQuery):
        return self.rank_jump_service.analyze_rank_jump(
            jump_threshold=query.jump_threshold,
            board_type=query.board_type,
            sigma_multiplier=query.sigma_multiplier,
            target_date=query.target_date,
            calculate_signals=query.calculate_signals,
            signal_thresholds=_to_legacy_signal_thresholds(query.signal_thresholds),
        )

    def analyze_steady_rise(self, query: AnalyzeSteadyRiseQuery):
        return self.steady_rise_service.analyze_steady_rise(
            period=query.period,
            board_type=query.board_type,
            min_rank_improvement=query.min_rank_improvement,
            sigma_multiplier=query.sigma_multiplier,
            target_date=query.target_date,
            calculate_signals=query.calculate_signals,
            signal_thresholds=_to_legacy_signal_thresholds(query.signal_thresholds),
        )
