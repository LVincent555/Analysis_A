"""Basic analysis query routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from ....models import AnalysisResult, AvailableDates
from ..application.basic_queries import (
    AnalyzePeriodUseCase,
    GetMarketVolatilitySummaryUseCase,
    ListAvailableDatesUseCase,
)
from ..application.queries import AnalyzePeriodQuery, MarketVolatilitySummaryQuery
from ..infrastructure.basic_analysis import LegacyBasicAnalysisQueryAdapter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analysis"])


def _analysis_query_adapter() -> LegacyBasicAnalysisQueryAdapter:
    return LegacyBasicAnalysisQueryAdapter()


@router.get("/dates", response_model=AvailableDates)
def get_available_dates():
    try:
        dates = ListAvailableDatesUseCase(_analysis_query_adapter()).execute()
        return AvailableDates(dates=dates, latest_date=dates[0] if dates else "")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/analyze/{period}", response_model=AnalysisResult)
def analyze_period(period: int, board_type: str = "main", top_n: int = 100, date: str | None = None):
    try:
        top_n = int(top_n)
        if top_n not in [100, 200, 400, 600, 800, 1000, 2000, 3000]:
            logger.warning("Invalid top_n=%s, falling back to 100", top_n)
            top_n = 100

        query = AnalyzePeriodQuery(
            period=period,
            max_count=top_n,
            board_type=board_type,
            target_date=date,
        )
        return AnalyzePeriodUseCase(_analysis_query_adapter()).execute(query)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/market/volatility-summary")
def get_market_volatility_summary(days: int = 3):
    try:
        result = GetMarketVolatilitySummaryUseCase(_analysis_query_adapter()).execute(
            MarketVolatilitySummaryQuery(days=days)
        )
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get market volatility summary: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
