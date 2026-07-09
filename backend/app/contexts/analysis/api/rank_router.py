"""Rank and trend analysis routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ....models import RankJumpResult, SteadyRiseResult
from ..application.queries import (
    AnalyzeRankJumpQuery,
    AnalyzeSteadyRiseQuery,
    SignalThresholdSettings,
)
from ..application.rank_trend_queries import AnalyzeRankJumpUseCase, AnalyzeSteadyRiseUseCase
from ..infrastructure.rank_trend_analysis import LegacyRankTrendAnalysisAdapter

rank_jump_router = APIRouter(prefix="/api", tags=["rank_jump"])
steady_rise_router = APIRouter(prefix="/api", tags=["steady-rise"])
router = APIRouter()


def _analysis_adapter() -> LegacyRankTrendAnalysisAdapter:
    return LegacyRankTrendAnalysisAdapter()


def _signal_thresholds(
    *,
    calculate_signals: bool,
    hot_list_mode: str,
    hot_list_version: str,
    hot_list_top: int,
    rank_jump_min: int,
    steady_rise_days: int,
    price_surge_min: float,
    volume_surge_min: float,
    volatility_surge_min: float,
) -> SignalThresholdSettings | None:
    if not calculate_signals:
        return None

    return SignalThresholdSettings(
        hot_list_mode=hot_list_mode,
        hot_list_version=hot_list_version,
        hot_list_top=hot_list_top,
        hot_list_top2=500,
        hot_list_top3=2000,
        hot_list_top4=3000,
        rank_jump_min=rank_jump_min,
        rank_jump_large=3000,
        steady_rise_days_min=steady_rise_days,
        steady_rise_days_large=steady_rise_days * 2,
        price_surge_min=price_surge_min,
        volume_surge_min=volume_surge_min,
        volatility_surge_min=volatility_surge_min,
        volatility_surge_large=volatility_surge_min * 2,
    )


@rank_jump_router.get("/rank_jump", response_model=RankJumpResult)
@rank_jump_router.get("/rank-jump", response_model=RankJumpResult)
def analyze_rank_jump(
    jump_threshold: int = Query(default=2500, ge=100, le=20000, description="Rank jump threshold"),
    board_type: str = Query(default="main", description="Board type: all/main/bjs"),
    sigma_multiplier: float = Query(default=1.0, ge=0.1, le=3.0, description="Sigma multiplier"),
    date: str | None = Query(default=None, description="Target date in YYYYMMDD format"),
    calculate_signals: bool = Query(default=False, description="Whether to calculate extra signal labels"),
    hot_list_mode: str = Query("frequent", description="Hot list mode: instant or frequent"),
    hot_list_version: str = Query("v2", description="Hot list version: v1 or v2"),
    hot_list_top: int = Query(default=100, ge=10, le=1000),
    rank_jump_min: int = Query(default=1000, ge=500, le=5000),
    steady_rise_days: int = Query(default=3, ge=2, le=14),
    price_surge_min: float = Query(default=5.0, ge=1.0, le=20.0),
    volume_surge_min: float = Query(default=10.0, ge=1.0, le=50.0),
    volatility_surge_min: float = Query(default=10.0, ge=10.0, le=200.0),
):
    try:
        query = AnalyzeRankJumpQuery(
            jump_threshold=jump_threshold,
            board_type=board_type,
            sigma_multiplier=sigma_multiplier,
            target_date=date,
            calculate_signals=calculate_signals,
            signal_thresholds=_signal_thresholds(
                calculate_signals=calculate_signals,
                hot_list_mode=hot_list_mode,
                hot_list_version=hot_list_version,
                hot_list_top=hot_list_top,
                rank_jump_min=rank_jump_min,
                steady_rise_days=steady_rise_days,
                price_surge_min=price_surge_min,
                volume_surge_min=volume_surge_min,
                volatility_surge_min=volatility_surge_min,
            ),
        )
        return AnalyzeRankJumpUseCase(_analysis_adapter()).execute(query)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@steady_rise_router.get("/steady-rise", response_model=SteadyRiseResult)
def analyze_steady_rise(
    period: int = Query(default=3, ge=2, le=14, description="Analysis period in days"),
    board_type: str = Query(default="main", description="Board type: all/main/bjs"),
    min_rank_improvement: int = Query(default=100, ge=50, le=5000, description="Minimum rank improvement"),
    sigma_multiplier: float = Query(default=1.0, ge=0.1, le=3.0, description="Sigma multiplier"),
    date: str | None = Query(default=None, description="Target date in YYYYMMDD format"),
    calculate_signals: bool = Query(default=False, description="Whether to calculate extra signal labels"),
    hot_list_mode: str = Query("frequent", description="Hot list mode: instant or frequent"),
    hot_list_version: str = Query("v2", description="Hot list version: v1 or v2"),
    hot_list_top: int = Query(default=100, ge=10, le=1000),
    rank_jump_min: int = Query(default=1000, ge=500, le=5000),
    steady_rise_days: int = Query(default=3, ge=2, le=14),
    price_surge_min: float = Query(default=5.0, ge=1.0, le=20.0),
    volume_surge_min: float = Query(default=10.0, ge=1.0, le=50.0),
    volatility_surge_min: float = Query(default=10.0, ge=10.0, le=200.0),
):
    try:
        query = AnalyzeSteadyRiseQuery(
            period=period,
            board_type=board_type,
            min_rank_improvement=min_rank_improvement,
            sigma_multiplier=sigma_multiplier,
            target_date=date,
            calculate_signals=calculate_signals,
            signal_thresholds=_signal_thresholds(
                calculate_signals=calculate_signals,
                hot_list_mode=hot_list_mode,
                hot_list_version=hot_list_version,
                hot_list_top=hot_list_top,
                rank_jump_min=rank_jump_min,
                steady_rise_days=steady_rise_days,
                price_surge_min=price_surge_min,
                volume_surge_min=volume_surge_min,
                volatility_surge_min=volatility_surge_min,
            ),
        )
        return AnalyzeSteadyRiseUseCase(_analysis_adapter()).execute(query)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


router.include_router(rank_jump_router)
router.include_router(steady_rise_router)
