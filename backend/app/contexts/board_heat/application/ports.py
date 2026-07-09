"""Board heat application ports."""

from __future__ import annotations

from typing import Any, Protocol

from .commands import (
    CalculateBoardHeatCommand,
    ListExternalBoardsQuery,
    ListSyncHistoryQuery,
    SyncExternalBoardsCommand,
)
from .queries import (
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


class BoardHeatQueryPort(Protocol):
    def get_board_heat_ranking(self, query: GetBoardHeatRankingQuery) -> Any:
        ...

    def get_stock_board_dna(self, query: GetStockBoardDnaQuery) -> Any:
        ...

    def get_stocks_board_signals_batch(self, query: GetStocksBoardSignalsBatchQuery) -> Any:
        ...

    def get_board_detail(self, query: GetBoardDetailQuery) -> Any:
        ...

    def get_available_dates(self) -> Any:
        ...

    def get_market_treemap(self, query: GetMarketTreemapQuery) -> Any:
        ...

    def get_market_signal_bar(self, trade_date: str | None = None) -> Any:
        ...

    def get_sector_matrix(self, query: GetSectorMatrixQuery) -> Any:
        ...

    def get_mining_resonance(self, query: GetMiningResonanceQuery) -> Any:
        ...

    def get_mining_hidden_gems(self, query: GetMiningHiddenGemsQuery) -> Any:
        ...

    def get_board_history(self, query: GetBoardHistoryQuery) -> Any:
        ...


class BoardHeatManagementPort(Protocol):
    async def start_sync(self, command: SyncExternalBoardsCommand) -> Any:
        ...

    def get_sync_status(self) -> Any:
        ...

    def cancel_sync(self) -> Any:
        ...

    async def start_heat_calculation(self, command: CalculateBoardHeatCommand) -> Any:
        ...

    def get_heat_status(self) -> Any:
        ...

    def cancel_heat_calculation(self) -> Any:
        ...

    def auto_mapping(self) -> Any:
        ...

    def get_sync_history(self, query: ListSyncHistoryQuery) -> Any:
        ...

    def get_stats(self) -> Any:
        ...

    def get_boards(self, query: ListExternalBoardsQuery) -> Any:
        ...
