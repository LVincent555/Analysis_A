"""Adapters for legacy industry detail analysis services."""

from __future__ import annotations

from ..application.queries import (
    CompareIndustriesQuery,
    GetIndustryDetailQuery,
    GetIndustryDetailTrendQuery,
    GetIndustryStocksQuery,
    IndustryDetailSignalThresholdSettings,
)
from ....services.industry_detail_service import industry_detail_service
from ....services.signal_calculator import SignalThresholds


def _to_legacy_signal_thresholds(
    settings: IndustryDetailSignalThresholdSettings | None,
) -> SignalThresholds | None:
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


class LegacyIndustryDetailAnalysisAdapter:
    def __init__(self, *, industry_service=industry_detail_service) -> None:
        self.industry_service = industry_service

    def get_industry_stocks(self, query: GetIndustryStocksQuery):
        return self.industry_service.get_industry_stocks(
            industry_name=query.industry_name,
            target_date=query.target_date,
            sort_mode=query.sort_mode,
            calculate_signals=query.calculate_signals,
            signal_thresholds=_to_legacy_signal_thresholds(query.signal_thresholds),
        )

    def get_industry_detail(self, query: GetIndustryDetailQuery):
        return self.industry_service.get_industry_detail(
            industry_name=query.industry_name,
            target_date=query.target_date,
            k_value=query.k,
        )

    def get_industry_trend(self, query: GetIndustryDetailTrendQuery):
        return self.industry_service.get_industry_trend(
            industry_name=query.industry_name,
            period=query.period,
            k_value=query.k,
        )

    def compare_industries(self, query: CompareIndustriesQuery):
        return self.industry_service.compare_industries(
            industry_names=query.industry_names,
            target_date=query.target_date,
            k_value=query.k,
        )
