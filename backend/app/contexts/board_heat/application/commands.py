"""Board heat command DTOs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SyncExternalBoardsCommand:
    provider: str = "all"
    force: bool = False
    use_proxy: bool = True
    date: str | None = None
    board_type: str = "all"
    delay: float = 1.0
    concurrent: bool = False
    workers: int = 10
    max_ips: int = 200
    ip_ttl: float = 50.0
    req_delay_min: float = 1.0
    req_delay_max: float = 3.0
    limit: int | None = None
    skip_cons: bool = False
    skip_map: bool = False


@dataclass(frozen=True, slots=True)
class CalculateBoardHeatCommand:
    date: str | None = None
    calc_all: bool = False
    force: bool = False
    allow_fallback: bool = True


@dataclass(frozen=True, slots=True)
class ListSyncHistoryQuery:
    limit: int = 30


@dataclass(frozen=True, slots=True)
class ListExternalBoardsQuery:
    provider: str | None = None
    board_type: str | None = None
    search: str | None = None
    page: int = 1
    page_size: int = 50
