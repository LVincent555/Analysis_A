"""Stock query routes."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Query

from ....models import StockFullHistory, StockHistory
from ..application.queries import (
    GetStockRawDataQuery,
    SearchStockFullQuery,
    SearchStockQuery,
    StockSignalThresholdSettings,
)
from ..application.stock_queries import (
    GetStockRawDataUseCase,
    SearchStockFullUseCase,
    SearchStockUseCase,
)
from ..infrastructure.stock_queries import LegacyStockQueryAdapter

router = APIRouter(prefix="/api", tags=["stock"])


def _stock_query_adapter() -> LegacyStockQueryAdapter:
    return LegacyStockQueryAdapter()


@router.get("/stocks/raw-data")
def get_stock_raw_data(
    date: str | None = Query(default=None, description="指定日期 (YYYYMMDD格式)"),
    limit: int = Query(default=5000, ge=10, le=10000, description="返回数量"),
):
    try:
        result = GetStockRawDataUseCase(_stock_query_adapter()).execute(
            GetStockRawDataQuery(target_date=date, limit=limit)
        )
        if result is None:
            raise HTTPException(status_code=404, detail="没有可用数据")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/stock/search", response_model=List[StockFullHistory])
def search_stock_full(
    q: str = Query(..., min_length=1, description="股票代码或名称（模糊匹配）"),
    limit: int = Query(5, ge=1, le=20, description="返回的最大匹配数量"),
):
    try:
        return SearchStockFullUseCase(_stock_query_adapter()).execute(
            SearchStockFullQuery(keyword=q, limit=limit)
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/stock/{stock_code}", response_model=StockHistory)
def query_stock(
    stock_code: str,
    date: str | None = None,
    hot_list_mode: str = Query("frequent", description="热点榜模式: instant=总分TOP信号, frequent=最新热点TOP信号（默认）"),
    hot_list_version: str = Query("v2", description="热点榜版本: v1=原版, v2=新版（默认）"),
    hot_list_top: int = Query(100, ge=50, le=500, description="热点榜阈值（TOP N）"),
    rank_jump_min: int = Query(1000, ge=100, le=5000, description="排名跳变最小阈值"),
    steady_rise_days: int = Query(3, ge=2, le=7, description="稳步上升天数"),
    price_surge_min: float = Query(5.0, ge=1.0, le=10.0, description="涨幅榜最小阈值 %"),
    volume_surge_min: float = Query(10.0, ge=5.0, le=20.0, description="成交量榜最小阈值 %"),
    volatility_surge_min: float = Query(10.0, ge=10.0, le=200.0, description="波动率上升阈值（百分比变化 %）"),
):
    try:
        thresholds = StockSignalThresholdSettings(
            hot_list_mode=hot_list_mode,
            hot_list_version=hot_list_version,
            hot_list_top=hot_list_top,
            hot_list_top2=500,
            hot_list_top3=2000,
            hot_list_top4=3000,
            rank_jump_min=rank_jump_min,
            rank_jump_large=3000,
            steady_rise_days_min=steady_rise_days,
            price_surge_min=price_surge_min,
            volume_surge_min=volume_surge_min,
            volatility_surge_min=volatility_surge_min,
        )
        result = SearchStockUseCase(_stock_query_adapter()).execute(
            SearchStockQuery(keyword=stock_code, target_date=date, signal_thresholds=thresholds)
        )
        if not result:
            raise HTTPException(status_code=404, detail=f"未找到股票: {stock_code}")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
