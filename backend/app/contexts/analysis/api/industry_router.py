"""Industry analysis routes."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException

from ....models import IndustryStat, IndustryStats, IndustryStatsWeighted
from ..application.errors import AnalysisDataNotFoundError
from ..application.industry_queries import (
    GetIndustryStatsUseCase,
    GetIndustryTrendUseCase,
    GetTopIndustryUseCase,
    GetWeightedIndustryUseCase,
)
from ..application.queries import (
    GetIndustryStatsQuery,
    GetIndustryTrendQuery,
    GetTopIndustryQuery,
    GetWeightedIndustryQuery,
)
from ..infrastructure.industry_queries import LegacyIndustryAnalysisAdapter

router = APIRouter(prefix="/api", tags=["industry"])


def _industry_adapter() -> LegacyIndustryAnalysisAdapter:
    return LegacyIndustryAnalysisAdapter()


@router.get("/industry/stats", response_model=List[IndustryStat])
def get_industry_stats(period: int = 3, top_n: int = 20):
    try:
        return GetIndustryStatsUseCase(_industry_adapter()).execute(
            GetIndustryStatsQuery(period=period, top_n=top_n)
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/industry/trend")
def get_industry_trend(period: int = 14, top_n: int = 100, date: str | None = None):
    try:
        return GetIndustryTrendUseCase(_industry_adapter()).execute(
            GetIndustryTrendQuery(period=period, top_n=top_n, target_date=date)
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/industry/top1000", response_model=IndustryStats)
def get_top1000_industry(limit: int = 1000, date: str | None = None):
    try:
        if limit not in [1000, 2000, 3000, 5000]:
            limit = 1000

        return GetTopIndustryUseCase(_industry_adapter()).execute(
            GetTopIndustryQuery(limit=limit, target_date=date)
        )
    except AnalysisDataNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/industry/weighted", response_model=IndustryStatsWeighted)
def get_industry_weighted(date: str | None = None, k: float = 0.618, metric: str = "B1"):
    try:
        if k < 0.3 or k > 2.0:
            raise HTTPException(status_code=400, detail="k值必须在0.3-2.0之间")
        if metric not in ["B1", "B2", "C1", "C2"]:
            raise HTTPException(status_code=400, detail="metric必须是B1/B2/C1/C2之一")

        return GetWeightedIndustryUseCase(_industry_adapter()).execute(
            GetWeightedIndustryQuery(target_date=date, k=k, metric=metric)
        )
    except HTTPException:
        raise
    except AnalysisDataNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
