"""Board heat query routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ....auth.dependencies import get_current_user
from ....database import get_db
from ..application.errors import BoardHeatDataNotFoundError
from ..application.queries import (
    GetBoardDetailQuery,
    GetBoardHeatRankingQuery,
    GetBoardHistoryQuery,
    GetMarketTreemapQuery,
    GetMiningHiddenGemsQuery,
    GetMiningResonanceQuery,
    GetSectorMatrixQuery,
    GetStockBoardDnaQuery,
    GetStocksBoardSignalsBatchQuery,
)
from ..application.query_services import BoardHeatQueryService
from ..infrastructure.queries import SqlBoardHeatQueryAdapter

router = APIRouter(prefix="/api/board-heat", tags=["板块热度"])


class BoardHeatItem(BaseModel):
    board_id: int
    board_code: str
    board_name: str
    board_type: str
    stock_count: int
    heat_pct: float
    b1_rank_sum: float | None = None
    c2_score_avg: float | None = None
    is_blacklisted: bool = False


class BoardHeatRankingResponse(BaseModel):
    trade_date: str
    snap_date: str
    total_count: int
    items: list[BoardHeatItem]


class BoardStockItem(BaseModel):
    stock_code: str
    stock_name: str
    board_rank: int | None = None
    share_weight: float | None = None
    contribution_score: float | None = None
    total_score: float | None = None
    market_rank: int | None = None
    price_change: float | None = None
    close_price: float | None = None
    turnover_rate: float | None = None
    volatility: float | None = None
    signal_level: str = "NONE"
    signal_count: int | None = None
    final_score: float | None = None


class BoardDetailResponse(BaseModel):
    board_id: int
    board_code: str
    board_name: str
    board_type: str
    trade_date: str
    stock_count: int
    heat_pct: float
    heat_raw: float
    b1_rank_sum: float
    b2_rank_avg: float
    c1_score_sum: float
    c2_score_avg: float
    top100_count: int
    hotlist_count: int
    multi_signal_count: int
    avg_price_change: float | None = None
    avg_turnover: float | None = None
    signal_strength: float
    top_stocks: list[BoardStockItem]


class StockDNAResponse(BaseModel):
    stock_code: str
    stock_name: str
    trade_date: str
    signal_level: str
    final_score: float
    final_score_pct: float
    fallback_reason: str | None
    dna_json: dict[str, Any]
    all_related_boards: list[dict[str, Any]] | None = None


class MarketTreemapItem(BaseModel):
    board_id: int
    name: str
    value: float
    heat_pct: float
    type: str


class MarketSignalBarResponse(BaseModel):
    trade_date: str
    distribution: dict[str, int]
    total: int
    sentiment: str


class SectorMatrixItem(BaseModel):
    board_id: int
    name: str
    x: float
    y: float
    size: float
    type: str


class MiningStockItem(BaseModel):
    stock_code: str
    stock_name: str
    reason: str
    signal_level: str
    final_score: float
    market_rank: int
    board_name: str


def _query_service(db: Session) -> BoardHeatQueryService:
    return BoardHeatQueryService(SqlBoardHeatQueryAdapter(db))


def _not_found_error(exc: BoardHeatDataNotFoundError) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


@router.get("/ranking", response_model=BoardHeatRankingResponse)
async def get_board_heat_ranking(
    trade_date: str | None = Query(None, description="Trade date YYYY-MM-DD"),
    board_type: str | None = Query(None, description="Board type: industry/concept"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    exclude_blacklist: bool = Query(True),
    max_stock_count: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return _query_service(db).get_board_heat_ranking(
            GetBoardHeatRankingQuery(
                trade_date=trade_date,
                board_type=board_type,
                limit=limit,
                offset=offset,
                exclude_blacklist=exclude_blacklist,
                max_stock_count=max_stock_count,
            )
        )
    except BoardHeatDataNotFoundError as exc:
        raise _not_found_error(exc) from exc


@router.get("/stock/{stock_code}/dna", response_model=StockDNAResponse)
async def get_stock_board_dna(
    stock_code: str,
    trade_date: str | None = Query(None),
    min_price: float | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return _query_service(db).get_stock_board_dna(
            GetStockBoardDnaQuery(stock_code=stock_code, trade_date=trade_date, min_price=min_price)
        )
    except BoardHeatDataNotFoundError as exc:
        raise _not_found_error(exc) from exc


@router.post("/stocks/batch")
async def get_stocks_board_signals_batch(
    stock_codes: list[str],
    trade_date: str | None = None,
    min_price: float | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return _query_service(db).get_stocks_board_signals_batch(
        GetStocksBoardSignalsBatchQuery(stock_codes=stock_codes, trade_date=trade_date, min_price=min_price)
    )


@router.get("/board/{board_id}", response_model=BoardDetailResponse)
async def get_board_detail(
    board_id: int,
    trade_date: str | None = Query(None),
    limit: int = Query(50, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("contribution", description="contribution/rank/score"),
    min_price: float | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return _query_service(db).get_board_detail(
            GetBoardDetailQuery(
                board_id=board_id,
                trade_date=trade_date,
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                min_price=min_price,
            )
        )
    except BoardHeatDataNotFoundError as exc:
        raise _not_found_error(exc) from exc


@router.get("/dates")
async def get_available_dates(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return _query_service(db).get_available_dates()


@router.get("/market/treemap", response_model=list[MarketTreemapItem])
async def get_market_treemap(
    trade_date: str | None = Query(None),
    min_size: float = Query(0),
    max_stock_count: int | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return _query_service(db).get_market_treemap(
        GetMarketTreemapQuery(trade_date=trade_date, min_size=min_size, max_stock_count=max_stock_count)
    )


@router.get("/market/signal-bar", response_model=MarketSignalBarResponse)
async def get_market_signal_bar(
    trade_date: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        return _query_service(db).get_market_signal_bar(trade_date)
    except BoardHeatDataNotFoundError as exc:
        raise _not_found_error(exc) from exc


@router.get("/market/sector-matrix", response_model=list[SectorMatrixItem])
async def get_sector_matrix(
    trade_date: str | None = Query(None),
    limit: int = Query(100),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return _query_service(db).get_sector_matrix(GetSectorMatrixQuery(trade_date=trade_date, limit=limit))


@router.get("/mining/resonance", response_model=list[MiningStockItem])
async def get_mining_resonance(
    trade_date: str | None = Query(None),
    limit: int = Query(50),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return _query_service(db).get_mining_resonance(GetMiningResonanceQuery(trade_date=trade_date, limit=limit))


@router.get("/mining/hidden-gems", response_model=list[MiningStockItem])
async def get_mining_hidden_gems(
    trade_date: str | None = Query(None),
    min_score: float = Query(85),
    min_rank: int = Query(500),
    limit: int = Query(50),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return _query_service(db).get_mining_hidden_gems(
        GetMiningHiddenGemsQuery(trade_date=trade_date, min_score=min_score, min_rank=min_rank, limit=limit)
    )


@router.get("/board/{board_id}/history")
async def get_board_history(
    board_id: int,
    days: int = Query(30, ge=7, le=365),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return _query_service(db).get_board_history(
        GetBoardHistoryQuery(board_id=board_id, days=days, end_date=end_date)
    )
