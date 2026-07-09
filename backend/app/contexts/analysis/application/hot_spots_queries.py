"""Hot spots analysis query use cases."""

from __future__ import annotations

from typing import Any

from .ports import HotSpotsAnalysisQueryPort
from .queries import GetHotSpotsFullQuery


class GetHotSpotsFullUseCase:
    def __init__(self, hot_spots_port: HotSpotsAnalysisQueryPort) -> None:
        self.hot_spots_port = hot_spots_port

    def execute(self, query: GetHotSpotsFullQuery) -> Any | None:
        return self.hot_spots_port.get_hot_spots_full(query)
