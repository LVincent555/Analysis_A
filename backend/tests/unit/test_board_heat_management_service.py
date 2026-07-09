from __future__ import annotations

import asyncio

from app.contexts.board_heat.application.commands import (
    CalculateBoardHeatCommand,
    SyncExternalBoardsCommand,
)
from app.contexts.board_heat.application.management_services import BoardHeatManagementService


class FakeBoardHeatManagementPort:
    def __init__(self) -> None:
        self.sync_command: SyncExternalBoardsCommand | None = None
        self.heat_command: CalculateBoardHeatCommand | None = None

    async def start_sync(self, command: SyncExternalBoardsCommand) -> dict:
        self.sync_command = command
        return {"task_id": "sync"}

    async def start_heat_calculation(self, command: CalculateBoardHeatCommand) -> dict:
        self.heat_command = command
        return {"task_id": "heat"}


def test_board_heat_management_service_delegates_task_commands() -> None:
    port = FakeBoardHeatManagementPort()
    service = BoardHeatManagementService(port)
    sync_command = SyncExternalBoardsCommand(provider="em", force=True)
    heat_command = CalculateBoardHeatCommand(date="2026-07-08", force=True)

    assert asyncio.run(service.start_sync(sync_command)) == {"task_id": "sync"}
    assert asyncio.run(service.start_heat_calculation(heat_command)) == {"task_id": "heat"}
    assert port.sync_command == sync_command
    assert port.heat_command == heat_command
