"""Adapters for legacy basic analysis query services."""

from __future__ import annotations

from ..application.queries import AnalyzePeriodQuery, MarketVolatilitySummaryQuery
from ....services.analysis_service_db import analysis_service_db
from ....services.numpy_cache_middleware import numpy_cache


class LegacyBasicAnalysisQueryAdapter:
    def __init__(
        self,
        *,
        analysis_service=analysis_service_db,
        volatility_cache=numpy_cache,
    ) -> None:
        self.analysis_service = analysis_service
        self.volatility_cache = volatility_cache

    def get_available_dates(self) -> list[str]:
        return self.analysis_service.get_available_dates()

    def analyze_period(self, query: AnalyzePeriodQuery):
        return self.analysis_service.analyze_period(
            query.period,
            max_count=query.max_count,
            board_type=query.board_type,
            target_date=query.target_date,
        )

    def get_market_volatility_summary(self, query: MarketVolatilitySummaryQuery) -> dict:
        return self.volatility_cache.get_market_volatility_summary(days=query.days)
