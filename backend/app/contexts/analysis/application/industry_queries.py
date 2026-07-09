"""Industry analysis query use cases."""

from __future__ import annotations

from typing import Any

from .ports import IndustryAnalysisQueryPort
from .queries import (
    GetIndustryStatsQuery,
    GetIndustryTrendQuery,
    GetTopIndustryQuery,
    GetWeightedIndustryQuery,
)


class GetIndustryStatsUseCase:
    def __init__(self, industry_port: IndustryAnalysisQueryPort) -> None:
        self.industry_port = industry_port

    def execute(self, query: GetIndustryStatsQuery) -> Any:
        return self.industry_port.get_industry_stats(query)


class GetIndustryTrendUseCase:
    def __init__(self, industry_port: IndustryAnalysisQueryPort) -> None:
        self.industry_port = industry_port

    def execute(self, query: GetIndustryTrendQuery) -> dict:
        return self.industry_port.get_industry_trend(query)


class GetTopIndustryUseCase:
    def __init__(self, industry_port: IndustryAnalysisQueryPort) -> None:
        self.industry_port = industry_port

    def execute(self, query: GetTopIndustryQuery) -> Any:
        return self.industry_port.get_top_industry(query)


class GetWeightedIndustryUseCase:
    def __init__(self, industry_port: IndustryAnalysisQueryPort) -> None:
        self.industry_port = industry_port

    def execute(self, query: GetWeightedIndustryQuery) -> Any:
        return self.industry_port.get_weighted_industry(query)
