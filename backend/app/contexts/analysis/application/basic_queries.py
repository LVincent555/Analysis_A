"""Basic analysis query use cases."""

from __future__ import annotations

from typing import Any

from .ports import BasicAnalysisQueryPort
from .queries import AnalyzePeriodQuery, MarketVolatilitySummaryQuery


class ListAvailableDatesUseCase:
    def __init__(self, analysis_port: BasicAnalysisQueryPort) -> None:
        self.analysis_port = analysis_port

    def execute(self) -> list[str]:
        return self.analysis_port.get_available_dates()


class AnalyzePeriodUseCase:
    def __init__(self, analysis_port: BasicAnalysisQueryPort) -> None:
        self.analysis_port = analysis_port

    def execute(self, query: AnalyzePeriodQuery) -> Any:
        return self.analysis_port.analyze_period(query)


class GetMarketVolatilitySummaryUseCase:
    def __init__(self, analysis_port: BasicAnalysisQueryPort) -> None:
        self.analysis_port = analysis_port

    def execute(self, query: MarketVolatilitySummaryQuery) -> dict:
        return self.analysis_port.get_market_volatility_summary(query)
