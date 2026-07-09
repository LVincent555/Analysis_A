"""Analysis application ports."""

from __future__ import annotations

from typing import Any, Protocol

from .queries import (
    AnalyzePeriodQuery,
    AnalyzeRankJumpQuery,
    AnalyzeSteadyRiseQuery,
    GetIndustryStatsQuery,
    GetIndustryTrendQuery,
    CompareIndustriesQuery,
    GetIndustryDetailQuery,
    GetIndustryDetailTrendQuery,
    GetIndustryStocksQuery,
    GetHotSpotsFullQuery,
    GetNeedleUnder20StockDetailQuery,
    GetNeedleUnder20StocksQuery,
    GetTopIndustryQuery,
    GetWeightedIndustryQuery,
    MarketVolatilitySummaryQuery,
)


class RankJumpAnalysisPort(Protocol):
    def analyze_rank_jump(self, query: AnalyzeRankJumpQuery) -> Any:
        ...


class SteadyRiseAnalysisPort(Protocol):
    def analyze_steady_rise(self, query: AnalyzeSteadyRiseQuery) -> Any:
        ...


class BasicAnalysisQueryPort(Protocol):
    def get_available_dates(self) -> list[str]:
        ...

    def analyze_period(self, query: AnalyzePeriodQuery) -> Any:
        ...

    def get_market_volatility_summary(self, query: MarketVolatilitySummaryQuery) -> dict:
        ...


class IndustryAnalysisQueryPort(Protocol):
    def get_industry_stats(self, query: GetIndustryStatsQuery) -> Any:
        ...

    def get_industry_trend(self, query: GetIndustryTrendQuery) -> dict:
        ...

    def get_top_industry(self, query: GetTopIndustryQuery) -> Any:
        ...

    def get_weighted_industry(self, query: GetWeightedIndustryQuery) -> Any:
        ...


class IndustryDetailAnalysisQueryPort(Protocol):
    def get_industry_stocks(self, query: GetIndustryStocksQuery) -> Any | None:
        ...

    def get_industry_detail(self, query: GetIndustryDetailQuery) -> Any | None:
        ...

    def get_industry_trend(self, query: GetIndustryDetailTrendQuery) -> Any | None:
        ...

    def compare_industries(self, query: CompareIndustriesQuery) -> Any:
        ...


class StrategyAnalysisQueryPort(Protocol):
    async def get_needle_under_20_stocks(self, query: GetNeedleUnder20StocksQuery) -> Any:
        ...

    def get_needle_under_20_stock_detail(self, query: GetNeedleUnder20StockDetailQuery) -> Any | None:
        ...


class HotSpotsAnalysisQueryPort(Protocol):
    def get_hot_spots_full(self, query: GetHotSpotsFullQuery) -> Any | None:
        ...
