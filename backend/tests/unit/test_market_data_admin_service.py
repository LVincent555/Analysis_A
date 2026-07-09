from __future__ import annotations

from app.contexts.market_data.infrastructure import data_admin
from app.contexts.market_data.application.admin_commands import UploadDataFileCommand
from app.contexts.market_data.application.admin_services import MarketDataAdminService


class FakeMarketDataAdminPort:
    def __init__(self) -> None:
        self.upload_command: UploadDataFileCommand | None = None

    def upload_file(self, command: UploadDataFileCommand) -> dict:
        self.upload_command = command
        return {"success": True}


def test_market_data_admin_service_delegates_upload_command() -> None:
    port = FakeMarketDataAdminPort()
    service = MarketDataAdminService(port)
    command = UploadDataFileCommand(filename="a.xlsx", content="AA==", username="admin")

    assert service.upload_file(command) == {"success": True}
    assert port.upload_command == command


def test_runtime_cache_refresh_is_scheduled_and_updates_status(monkeypatch) -> None:
    calls: list[str] = []

    def fake_reload() -> None:
        calls.append("reloaded")

    monkeypatch.setattr(data_admin, "_perform_runtime_cache_reload", fake_reload)
    data_admin.import_status["cache_refresh"] = {
        "is_refreshing": False,
        "started_at": None,
        "finished_at": None,
        "success": None,
        "error": None,
        "reason": None,
    }

    thread = data_admin._schedule_runtime_cache_reload("unit-test")

    assert thread is not None
    thread.join(timeout=2)
    assert calls == ["reloaded"]
    assert data_admin.import_status["cache_refresh"]["is_refreshing"] is False
    assert data_admin.import_status["cache_refresh"]["success"] is True
    assert data_admin.import_status["cache_refresh"]["reason"] == "unit-test"
