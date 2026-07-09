from __future__ import annotations

from app.contexts.board_heat.application.queries import (
    GetBoardHeatRankingQuery,
    GetStockBoardDnaQuery,
)
from app.contexts.board_heat.application.query_services import BoardHeatQueryService


class FakeBoardHeatQueryPort:
    def __init__(self) -> None:
        self.ranking_query: GetBoardHeatRankingQuery | None = None
        self.dna_query: GetStockBoardDnaQuery | None = None

    def get_board_heat_ranking(self, query: GetBoardHeatRankingQuery) -> dict:
        self.ranking_query = query
        return {"items": []}

    def get_stock_board_dna(self, query: GetStockBoardDnaQuery) -> dict:
        self.dna_query = query
        return {"stock_code": query.stock_code}


def test_board_heat_query_service_delegates_ranking_and_dna_queries() -> None:
    port = FakeBoardHeatQueryPort()
    service = BoardHeatQueryService(port)
    ranking_query = GetBoardHeatRankingQuery(trade_date="2026-07-08", board_type="concept", limit=20)
    dna_query = GetStockBoardDnaQuery(stock_code="000001", min_price=3.5)

    assert service.get_board_heat_ranking(ranking_query) == {"items": []}
    assert service.get_stock_board_dna(dna_query) == {"stock_code": "000001"}
    assert port.ranking_query == ranking_query
    assert port.dna_query == dna_query
