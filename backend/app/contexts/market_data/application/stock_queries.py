"""Stock query use cases."""

from __future__ import annotations

from typing import Any

from .ports import StockQueryPort
from .queries import GetStockRawDataQuery, SearchStockFullQuery, SearchStockQuery


class GetStockRawDataUseCase:
    def __init__(self, stock_port: StockQueryPort) -> None:
        self.stock_port = stock_port

    def execute(self, query: GetStockRawDataQuery) -> dict | None:
        return self.stock_port.get_stock_raw_data(query)


class SearchStockFullUseCase:
    def __init__(self, stock_port: StockQueryPort) -> None:
        self.stock_port = stock_port

    def execute(self, query: SearchStockFullQuery) -> list[Any]:
        return self.stock_port.search_stock_full(query)


class SearchStockUseCase:
    def __init__(self, stock_port: StockQueryPort) -> None:
        self.stock_port = stock_port

    def execute(self, query: SearchStockQuery) -> Any | None:
        return self.stock_port.search_stock(query)
