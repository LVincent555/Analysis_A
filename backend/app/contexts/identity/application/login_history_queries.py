"""Login history query use cases."""

from __future__ import annotations

from typing import Any

from .ports import LoginHistoryQueryPort
from .queries import GetLoginHistoryQuery


class GetLoginHistoryUseCase:
    def __init__(self, history_port: LoginHistoryQueryPort) -> None:
        self.history_port = history_port

    def execute(self, query: GetLoginHistoryQuery) -> Any:
        return self.history_port.get_login_history()
