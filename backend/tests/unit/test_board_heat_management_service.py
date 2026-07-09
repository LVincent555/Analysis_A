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


def test_sync_task_schedules_executor_without_kwargs_error(monkeypatch, tmp_path) -> None:
    script_path = tmp_path / "sync_ext_boards.py"
    script_path.write_text("print('ok')", encoding="utf-8")
    status = {
        "is_syncing": True,
        "task_id": "sync",
        "process": None,
        "task": None,
        "cancel_requested": False,
        "start_time": None,
        "provider": "em",
        "logs": [],
    }

    def fake_run_process(cmd, cwd, run_status, *, done_message, fail_message, timeout_seconds=None):
        run_status["logs"].append(done_message)
        run_status["is_syncing"] = False

    monkeypatch.setattr(management, "_sync_script_path", lambda: script_path)
    monkeypatch.setattr(management, "_sync_task_status", status)
    monkeypatch.setattr(management, "_run_process_blocking", fake_run_process)

    async def run_task() -> None:
        await management.BoardHeatManagementAdapter()._run_sync_task(SyncExternalBoardsCommand(provider="em"))
        for _ in range(20):
            if not status["is_syncing"]:
                break
            await asyncio.sleep(0.01)

    asyncio.run(run_task())

    assert status["is_syncing"] is False
    assert "同步完成" in status["logs"]


def test_run_process_blocking_timeout_resets_running_state(tmp_path) -> None:
    status = {
        "is_running": True,
        "process": None,
        "cancel_requested": False,
        "logs": [],
    }

    management._run_process_blocking(
        [sys.executable, "-c", "import time; time.sleep(2)"],
        str(tmp_path),
        status,
        done_message="done",
        fail_message="failed",
        timeout_seconds=1,
    )

    assert status["is_running"] is False
    assert status["process"] is None
    assert any("超时" in line for line in status["logs"])
