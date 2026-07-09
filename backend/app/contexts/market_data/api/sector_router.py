"""Sector query routes."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Query

from ....models import SectorDetail, SectorRankingResult
from ..application.errors import MarketDataNotFoundError
from ..application.queries import (
    GetSectorDetailQuery,
    GetSectorRankChangesQuery,
    GetSectorRankingQuery,
    GetSectorRawDataQuery,
    GetSectorTrendQuery,
    SearchSectorsQuery,
)
from ..application.sector_queries import (
    GetSectorAvailableDatesUseCase,
    GetSectorDetailUseCase,
    GetSectorRankChangesUseCase,
    GetSectorRankingUseCase,
    GetSectorRawDataUseCase,
    GetSectorTrendUseCase,
    SearchSectorsUseCase,
)
from ..infrastructure.sector_queries import LegacySectorQueryAdapter

router = APIRouter(prefix="/api", tags=["sector"])


def _sector_query_adapter() -> LegacySectorQueryAdapter:
    return LegacySectorQueryAdapter()


def _not_found(exc: MarketDataNotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


@router.get("/sectors/dates", response_model=List[str])
def get_available_dates():
    try:
        return GetSectorAvailableDatesUseCase(_sector_query_adapter()).execute()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/sectors/ranking", response_model=SectorRankingResult)
@router.get("/sector-ranking", response_model=SectorRankingResult)
def get_sector_ranking(
    date: str | None = Query(default=None, description="指定日期 (YYYYMMDD格式)"),
    limit: int = Query(default=100, ge=10, le=500, description="返回的板块数量"),
):
    try:
        return GetSectorRankingUseCase(_sector_query_adapter()).execute(
            GetSectorRankingQuery(target_date=date, limit=limit)
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/sectors/raw-data")
def get_sector_raw_data(
    date: str | None = Query(default=None, description="指定日期 (YYYYMMDD格式)"),
    limit: int = Query(default=600, ge=10, le=1000, description="返回数量"),
):
    try:
        return GetSectorRawDataUseCase(_sector_query_adapter()).execute(
            GetSectorRawDataQuery(target_date=date, limit=limit)
        )
    except MarketDataNotFoundError as exc:
        raise _not_found(exc) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/sectors/search/{keyword}", response_model=List[str])
def search_sectors(keyword: str):
    try:
        return SearchSectorsUseCase(_sector_query_adapter()).execute(SearchSectorsQuery(keyword=keyword))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/sectors/trend")
def get_sector_trend(
    days: int = Query(default=7, ge=3, le=60, description="显示天数"),
    limit: int = Query(default=10, ge=5, le=30, description="前N个板块"),
    date: str | None = Query(default=None, description="结束日期 (YYYYMMDD格式)"),
):
    try:
        return GetSectorTrendUseCase(_sector_query_adapter()).execute(
            GetSectorTrendQuery(days=days, limit=limit, target_date=date)
        )
    except MarketDataNotFoundError as exc:
        raise _not_found(exc) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/sectors/rank-changes")
def get_sector_rank_changes(
    date: str | None = Query(default=None, description="对比日期 (YYYYMMDD格式)"),
    compare_days: int = Query(default=1, ge=1, le=7, description="对比天数（1=昨天）"),
):
    try:
        return GetSectorRankChangesUseCase(_sector_query_adapter()).execute(
            GetSectorRankChangesQuery(target_date=date, compare_days=compare_days)
        )
    except MarketDataNotFoundError as exc:
        raise _not_found(exc) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/sectors/{sector_name}", response_model=SectorDetail)
@router.get("/sector/{sector_name}", response_model=SectorDetail)
def get_sector_detail(
    sector_name: str,
    days: int = Query(default=30, ge=7, le=365, description="返回的历史天数"),
    date: str | None = Query(default=None, description="指定日期 (YYYYMMDD格式)"),
):
    try:
        result = GetSectorDetailUseCase(_sector_query_adapter()).execute(
            GetSectorDetailQuery(sector_name=sector_name, days=days, target_date=date)
        )
        if not result:
            raise HTTPException(status_code=404, detail=f"板块不存在: {sector_name}")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
