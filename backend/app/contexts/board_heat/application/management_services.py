"""Board heat management use cases."""

from __future__ import annotations

from typing import Any

from .commands import (
    CalculateBoardHeatCommand,
    ListExternalBoardsQuery,
    ListSyncHistoryQuery,
    SyncExternalBoardsCommand,
)
from .ports import BoardHeatManagementPort


class BoardHeatManagementService:
    def __init__(self, management_port: BoardHeatManagementPort) -> None:
        self.management_port = management_port

    async def start_sync(self, command: SyncExternalBoardsCommand) -> Any:
        return await self.management_port.start_sync(command)

    def get_sync_status(self) -> Any:
        return self.management_port.get_sync_status()

    def cancel_sync(self) -> Any:
        return self.management_port.cancel_sync()

    async def start_heat_calculation(self, command: CalculateBoardHeatCommand) -> Any:
        return await self.management_port.start_heat_calculation(command)

    def get_heat_status(self) -> Any:
        return self.management_port.get_heat_status()

    def cancel_heat_calculation(self) -> Any:
        return self.management_port.cancel_heat_calculation()

    def auto_mapping(self) -> Any:
        return self.management_port.auto_mapping()

    def get_sync_history(self, query: ListSyncHistoryQuery) -> Any:
        return self.management_port.get_sync_history(query)

    def get_stats(self) -> Any:
        return self.management_port.get_stats()

    def get_boards(self, query: ListExternalBoardsQuery) -> Any:
        return self.management_port.get_boards(query)
