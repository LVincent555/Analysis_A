"""Strategy analysis query use cases."""

from __future__ import annotations

from typing import Any

from .ports import StrategyAnalysisQueryPort
from .queries import GetNeedleUnder20StockDetailQuery, GetNeedleUnder20StocksQuery


class GetNeedleUnder20StocksUseCase:
    def __init__(self, strategy_port: StrategyAnalysisQueryPort) -> None:
        self.strategy_port = strategy_port

    async def execute(self, query: GetNeedleUnder20StocksQuery) -> Any:
        return await self.strategy_port.get_needle_under_20_stocks(query)


class GetNeedleUnder20StockDetailUseCase:
    def __init__(self, strategy_port: StrategyAnalysisQueryPort) -> None:
        self.strategy_port = strategy_port

    def execute(self, query: GetNeedleUnder20StockDetailQuery) -> Any | None:
        return self.strategy_port.get_needle_under_20_stock_detail(query)
