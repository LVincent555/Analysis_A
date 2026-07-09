from __future__ import annotations

import asyncio
import sys

from app.contexts.board_heat.application.commands import (
    CalculateBoardHeatCommand,
    SyncExternalBoardsCommand,
)
from app.contexts.board_heat.application.management_services import BoardHeatManagementService
from app.contexts.board_heat.infrastructure import management


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


def test_external_board_process_timeout_resets_sync_status(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("EXT_BOARD_TASK_TIMEOUT_SECONDS", "1")
    status = {
        "is_syncing": True,
        "task_id": "unit-test",
        "process": None,
        "task": None,
        "cancel_requested": False,
        "start_time": None,
        "provider": "em",
        "logs": [],
    }
    cmd = [
        sys.executable,
        "-c",
        "import time; print('started', flush=True); time.sleep(5)",
    ]

    management._run_process_blocking(
        cmd,
        str(tmp_path),
        status,
        done_message="done",
        fail_message="failed",
    )

    assert status["is_syncing"] is False
    assert status["process"] is None
    assert status["cancel_requested"] is False
    assert any("超时" in line or "自动终止" in line for line in status["logs"])
