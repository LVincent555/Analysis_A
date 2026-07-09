"""Board heat query use cases."""

from __future__ import annotations

from typing import Any

from .ports import BoardHeatQueryPort
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


class BoardHeatQueryService:
    def __init__(self, query_port: BoardHeatQueryPort) -> None:
        self.query_port = query_port

    def get_board_heat_ranking(self, query: GetBoardHeatRankingQuery) -> Any:
        return self.query_port.get_board_heat_ranking(query)

    def get_stock_board_dna(self, query: GetStockBoardDnaQuery) -> Any:
        return self.query_port.get_stock_board_dna(query)

    def get_stocks_board_signals_batch(self, query: GetStocksBoardSignalsBatchQuery) -> Any:
        return self.query_port.get_stocks_board_signals_batch(query)

    def get_board_detail(self, query: GetBoardDetailQuery) -> Any:
        return self.query_port.get_board_detail(query)

    def get_available_dates(self) -> Any:
        return self.query_port.get_available_dates()

    def get_market_treemap(self, query: GetMarketTreemapQuery) -> Any:
        return self.query_port.get_market_treemap(query)

    def get_market_signal_bar(self, trade_date: str | None = None) -> Any:
        return self.query_port.get_market_signal_bar(trade_date)

    def get_sector_matrix(self, query: GetSectorMatrixQuery) -> Any:
        return self.query_port.get_sector_matrix(query)

    def get_mining_resonance(self, query: GetMiningResonanceQuery) -> Any:
        return self.query_port.get_mining_resonance(query)

    def get_mining_hidden_gems(self, query: GetMiningHiddenGemsQuery) -> Any:
        return self.query_port.get_mining_hidden_gems(query)

    def get_board_history(self, query: GetBoardHistoryQuery) -> Any:
        return self.query_port.get_board_history(query)
