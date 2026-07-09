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


def test_import_status_exposes_cache_refresh_state() -> None:
    adapter = data_admin.MarketDataAdminAdapter()
    original = dict(data_admin.cache_refresh_status)
    try:
        data_admin.cache_refresh_status.update(
            {
                "is_refreshing": True,
                "current_step": "重载 Numpy 缓存",
                "start_time": "2026-07-09T21:00:00",
                "end_time": None,
                "last_result": None,
                "last_error": None,
                "logs": [{"message": "refreshing"}],
            }
        )

        result = adapter.get_import_status()

        assert result["cache_refresh"]["is_refreshing"] is True
        assert result["cache_refresh"]["current_step"] == "重载 Numpy 缓存"
        assert result["cache_refresh"]["logs"] == [{"message": "refreshing"}]
    finally:
        data_admin.cache_refresh_status.clear()
        data_admin.cache_refresh_status.update(original)


def test_reload_runtime_caches_runs_remaining_steps_after_api_cache_failure(monkeypatch) -> None:
    calls: list[str] = []

    def fail_api_cache() -> None:
        calls.append("api")
        raise RuntimeError("bad api cache")

    monkeypatch.setattr(data_admin.cache, "clear_api_cache", fail_api_cache)
    monkeypatch.setattr(data_admin.HotSpotsCache, "clear_cache", lambda: calls.append("hotspots"))

    from app.core import startup

    monkeypatch.setattr(startup, "preload_cache", lambda: calls.append("numpy"))

    with pytest.raises(RuntimeError, match="bad api cache"):
        data_admin._reload_runtime_caches()

    assert calls == ["api", "hotspots", "numpy"]
