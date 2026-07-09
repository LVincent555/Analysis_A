"""Board heat query DTOs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GetBoardHeatRankingQuery:
    trade_date: str | None = None
    board_type: str | None = None
    limit: int = 50
    offset: int = 0
    exclude_blacklist: bool = True
    max_stock_count: int | None = None


@dataclass(frozen=True, slots=True)
class GetStockBoardDnaQuery:
    stock_code: str
    trade_date: str | None = None
    min_price: float | None = None


@dataclass(frozen=True, slots=True)
class GetStocksBoardSignalsBatchQuery:
    stock_codes: list[str]
    trade_date: str | None = None
    min_price: float | None = None


@dataclass(frozen=True, slots=True)
class GetBoardDetailQuery:
    board_id: int
    trade_date: str | None = None
    limit: int = 50
    offset: int = 0
    sort_by: str = "contribution"
    min_price: float | None = None


@dataclass(frozen=True, slots=True)
class GetMarketTreemapQuery:
    trade_date: str | None = None
    min_size: float = 0
    max_stock_count: int | None = None


@dataclass(frozen=True, slots=True)
class GetSectorMatrixQuery:
    trade_date: str | None = None
    limit: int = 100


@dataclass(frozen=True, slots=True)
class GetMiningResonanceQuery:
    trade_date: str | None = None
    limit: int = 50


@dataclass(frozen=True, slots=True)
class GetMiningHiddenGemsQuery:
    trade_date: str | None = None
    min_score: float = 85
    min_rank: int = 500
    limit: int = 50


@dataclass(frozen=True, slots=True)
class GetBoardHistoryQuery:
    board_id: int
    days: int = 30
    end_date: str | None = None
