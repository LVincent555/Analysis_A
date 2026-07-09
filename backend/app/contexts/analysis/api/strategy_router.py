"""Strategy analysis routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from ..application.queries import GetNeedleUnder20StockDetailQuery, GetNeedleUnder20StocksQuery
from ..application.strategy_queries import (
    GetNeedleUnder20StockDetailUseCase,
    GetNeedleUnder20StocksUseCase,
)
from ..infrastructure.strategy_queries import LegacyNeedleUnder20StrategyAdapter

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


def _strategy_adapter() -> LegacyNeedleUnder20StrategyAdapter:
    return LegacyNeedleUnder20StrategyAdapter()


@router.get("/needle-under-20")
async def get_needle_under_20_stocks(
    date: str | None = Query(None, description="Date in YYYYMMDD format; defaults to latest"),
    days: int = Query(5, description="Analysis day range"),
    min_score: int = Query(0, description="Minimum score threshold"),
    pattern: str | None = Query(None, description="Pattern filter: sky_refuel/bottom_volume"),
    bbi_filter: bool = Query(True, description="Whether to filter BBI break stocks"),
    max_drop_pct: float | None = Query(None, description="Maximum price drop threshold"),
    long_period: int = Query(10, description="Calculation period"),
):
    try:
        return await GetNeedleUnder20StocksUseCase(_strategy_adapter()).execute(
            GetNeedleUnder20StocksQuery(
                date=date,
                days=days,
                min_score=min_score,
                pattern=pattern,
                bbi_filter=bbi_filter,
                max_drop_pct=max_drop_pct,
                long_period=long_period,
            )
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/needle-under-20/{stock_code}")
def get_stock_needle_detail(
    stock_code: str,
    date: str | None = Query(None, description="Date in YYYYMMDD format"),
):
    try:
        result = GetNeedleUnder20StockDetailUseCase(_strategy_adapter()).execute(
            GetNeedleUnder20StockDetailQuery(stock_code=stock_code, date=date)
        )
        if result is None:
            raise HTTPException(status_code=404, detail="Stock data is unavailable or insufficient")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
