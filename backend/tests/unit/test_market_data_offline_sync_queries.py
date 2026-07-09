from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app.contexts.market_data.application.errors import OfflineSyncDisabledError
from app.contexts.market_data.application.offline_sync_queries import OfflineSyncQueryService
from app.contexts.market_data.application.queries import (
    GetOfflineStocksQuery,
    GetOfflineSyncStatusQuery,
    OfflineSyncUserSettings,
)
from app.contexts.market_data.infrastructure.offline_sync import LegacyOfflineSyncAdapter


class FakeOfflineSyncPort:
    def __init__(self) -> None:
        self.status_query: GetOfflineSyncStatusQuery | None = None

    def get_sync_status(self, query: GetOfflineSyncStatusQuery) -> dict:
        self.status_query = query
        return {"latest_date": None}


class FakeStockCache:
    def __init__(self) -> None:
        self.stocks = {"000001": SimpleNamespace(stock_code="000001", stock_name="Ping An", industry="Bank")}

    def get_available_dates(self):
        return [date(2026, 7, 8), date(2026, 7, 7)]


def test_offline_sync_service_delegates_to_port() -> None:
    port = FakeOfflineSyncPort()
    service = OfflineSyncQueryService(port)
    query = GetOfflineSyncStatusQuery(OfflineSyncUserSettings(offline_days=7, offline_enabled=True))

    assert service.get_sync_status(query) == {"latest_date": None}
    assert port.status_query == query


def test_legacy_offline_sync_adapter_exposes_status_and_blocks_disabled_stocks() -> None:
    adapter = LegacyOfflineSyncAdapter(stock_cache=FakeStockCache())

    status = adapter.get_sync_status(
        GetOfflineSyncStatusQuery(OfflineSyncUserSettings(offline_days=5, offline_enabled=False))
    )
    assert status["available_dates"] == 2
    assert status["total_stocks"] == 1
    assert status["user_offline_enabled"] is False

    try:
        adapter.get_stocks(GetOfflineStocksQuery(OfflineSyncUserSettings(offline_days=5, offline_enabled=False)))
    except OfflineSyncDisabledError:
        pass
    else:
        raise AssertionError("expected offline sync disabled error")
