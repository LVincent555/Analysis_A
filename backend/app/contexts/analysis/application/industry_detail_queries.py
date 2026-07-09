"""Industry detail analysis query use cases."""

from __future__ import annotations

from typing import Any

from .ports import IndustryDetailAnalysisQueryPort
from .queries import (
    CompareIndustriesQuery,
    GetIndustryDetailQuery,
    GetIndustryDetailTrendQuery,
    GetIndustryStocksQuery,
)


class GetIndustryStocksUseCase:
    def __init__(self, industry_port: IndustryDetailAnalysisQueryPort) -> None:
        self.industry_port = industry_port

    def execute(self, query: GetIndustryStocksQuery) -> Any | None:
        return self.industry_port.get_industry_stocks(query)


class GetIndustryDetailUseCase:
    def __init__(self, industry_port: IndustryDetailAnalysisQueryPort) -> None:
        self.industry_port = industry_port

    def execute(self, query: GetIndustryDetailQuery) -> Any | None:
        return self.industry_port.get_industry_detail(query)


class GetIndustryDetailTrendUseCase:
    def __init__(self, industry_port: IndustryDetailAnalysisQueryPort) -> None:
        self.industry_port = industry_port

    def execute(self, query: GetIndustryDetailTrendQuery) -> Any | None:
        return self.industry_port.get_industry_trend(query)


class CompareIndustriesUseCase:
    def __init__(self, industry_port: IndustryDetailAnalysisQueryPort) -> None:
        self.industry_port = industry_port

    def execute(self, query: CompareIndustriesQuery) -> Any:
        return self.industry_port.compare_industries(query)
