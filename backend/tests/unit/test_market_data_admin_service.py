from __future__ import annotations

import pytest

from app.contexts.market_data.application.admin_commands import UploadDataFileCommand
from app.contexts.market_data.application.admin_services import MarketDataAdminService
from app.contexts.market_data.infrastructure import data_admin


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


def test_runtime_cache_reload_runs_remaining_steps_after_api_cache_failure(monkeypatch) -> None:
    calls: list[str] = []

    def fail_api_cache() -> None:
        calls.append("api")
        raise RuntimeError("bad api cache")

    monkeypatch.setattr(data_admin.cache, "clear_api_cache", fail_api_cache)
    monkeypatch.setattr(data_admin.HotSpotsCache, "clear_cache", lambda: calls.append("hotspots"))

    class FakeNumpyCache:
        def reload(self, days: int) -> None:
            calls.append(f"numpy:{days}")

    monkeypatch.setenv("NUMPY_PRELOAD_DAYS", "7")
    monkeypatch.setattr("app.services.numpy_cache_middleware.numpy_cache", FakeNumpyCache())
    monkeypatch.setattr("app.core.startup._preload_hotspots", lambda days: calls.append(f"hotspots_preload:{days}"))

    with pytest.raises(RuntimeError, match="bad api cache"):
        data_admin._perform_runtime_cache_reload()

    assert calls == ["api", "hotspots", "numpy:7", "hotspots_preload:3"]
