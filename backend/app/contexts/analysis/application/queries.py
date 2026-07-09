"""Analysis query DTOs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SignalThresholdSettings:
    hot_list_mode: str = "frequent"
    hot_list_version: str = "v2"
    hot_list_top: int = 100
    hot_list_top2: int = 500
    hot_list_top3: int = 2000
    hot_list_top4: int = 3000
    rank_jump_min: int = 1000
    rank_jump_large: int = 3000
    steady_rise_days_min: int = 3
    steady_rise_days_large: int = 6
    price_surge_min: float = 5.0
    volume_surge_min: float = 10.0
    volatility_surge_min: float = 10.0
    volatility_surge_large: float = 20.0


@dataclass(frozen=True, slots=True)
class AnalyzeRankJumpQuery:
    jump_threshold: int = 2500
    board_type: str = "main"
    sigma_multiplier: float = 1.0
    target_date: str | None = None
    calculate_signals: bool = False
    signal_thresholds: SignalThresholdSettings | None = None


@dataclass(frozen=True, slots=True)
class AnalyzeSteadyRiseQuery:
    period: int = 3
    board_type: str = "main"
    min_rank_improvement: int = 100
    sigma_multiplier: float = 1.0
    target_date: str | None = None
    calculate_signals: bool = False
    signal_thresholds: SignalThresholdSettings | None = None


@dataclass(frozen=True, slots=True)
class AnalyzePeriodQuery:
    period: int
    max_count: int = 100
    board_type: str = "main"
    target_date: str | None = None


@dataclass(frozen=True, slots=True)
class MarketVolatilitySummaryQuery:
    days: int = 3


@dataclass(frozen=True, slots=True)
class GetIndustryStatsQuery:
    period: int = 3
    top_n: int = 20


@dataclass(frozen=True, slots=True)
class GetIndustryTrendQuery:
    period: int = 14
    top_n: int = 100
    target_date: str | None = None


@dataclass(frozen=True, slots=True)
class GetTopIndustryQuery:
    limit: int = 1000
    target_date: str | None = None


@dataclass(frozen=True, slots=True)
class GetWeightedIndustryQuery:
    target_date: str | None = None
    k: float = 0.618
    metric: str = "B1"


@dataclass(frozen=True, slots=True)
class IndustryDetailSignalThresholdSettings:
    hot_list_mode: str = "frequent"
    hot_list_version: str = "v2"
    hot_list_top: int = 100
    hot_list_top2: int = 500
    hot_list_top3: int = 2000
    hot_list_top4: int = 3000
    rank_jump_min: int = 2000
    rank_jump_large: int = 3000
    steady_rise_days_min: int = 3
    steady_rise_days_large: int = 5
    price_surge_min: float = 5.0
    volume_surge_min: float = 10.0
    volatility_surge_min: float = 10.0
    volatility_surge_large: float = 100.0


@dataclass(frozen=True, slots=True)
class GetIndustryStocksQuery:
    industry_name: str
    target_date: str | None = None
    sort_mode: str = "rank"
    calculate_signals: bool = True
    signal_thresholds: IndustryDetailSignalThresholdSettings | None = None


@dataclass(frozen=True, slots=True)
class GetIndustryDetailQuery:
    industry_name: str
    target_date: str | None = None
    k: float = 0.618


@dataclass(frozen=True, slots=True)
class GetIndustryDetailTrendQuery:
    industry_name: str
    period: int = 7
    k: float = 0.618


@dataclass(frozen=True, slots=True)
class CompareIndustriesQuery:
    industry_names: list[str]
    target_date: str | None = None
    k: float = 0.618


@dataclass(frozen=True, slots=True)
class GetNeedleUnder20StocksQuery:
    date: str | None = None
    days: int = 5
    min_score: int = 0
    pattern: str | None = None
    bbi_filter: bool = True
    max_drop_pct: float | None = None
    long_period: int = 10


@dataclass(frozen=True, slots=True)
class GetNeedleUnder20StockDetailQuery:
    stock_code: str
    date: str | None = None


@dataclass(frozen=True, slots=True)
class GetHotSpotsFullQuery:
    date: str | None = None
