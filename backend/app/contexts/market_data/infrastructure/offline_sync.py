"""Adapters for offline market data sync queries."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from ....services.numpy_cache_middleware import numpy_cache
from ..application.errors import InvalidOfflineSyncRequestError, OfflineSyncDisabledError
from ..application.queries import (
    GetDailySyncQuery,
    GetIncrementalSyncQuery,
    GetOfflineDatesQuery,
    GetOfflineStocksQuery,
    GetOfflineSyncStatusQuery,
    OfflineSyncUserSettings,
)


class LegacyOfflineSyncAdapter:
    def __init__(self, *, stock_cache=numpy_cache) -> None:
        self.stock_cache = stock_cache

    def get_sync_status(self, query: GetOfflineSyncStatusQuery) -> dict:
        dates = self.stock_cache.get_available_dates()
        return {
            "latest_date": dates[0] if dates else None,
            "available_dates": len(dates),
            "total_stocks": len(self.stock_cache.stocks),
            "server_time": _utcnow_naive().isoformat(),
            "user_offline_days": query.user_settings.offline_days,
            "user_offline_enabled": query.user_settings.offline_enabled,
        }

    def get_incremental_sync(self, query: GetIncrementalSyncQuery) -> dict:
        self._ensure_enabled(query.user_settings)
        try:
            since_dt = datetime.fromisoformat(query.since.replace("Z", "+00:00"))
        except ValueError as exc:
            raise InvalidOfflineSyncRequestError("无效的时间格式") from exc

        if since_dt.tzinfo is not None:
            since_dt = since_dt.astimezone(timezone.utc).replace(tzinfo=None)

        cutoff = _utcnow_naive() - timedelta(days=query.user_settings.offline_days)
        since_dt = max(since_dt, cutoff)

        all_dates = self.stock_cache.get_available_dates()
        all_dates_str = [date_item.strftime("%Y-%m-%d") for date_item in all_dates]
        sync_dates = [
            date_value
            for date_value in all_dates_str
            if datetime.strptime(date_value, "%Y-%m-%d") > since_dt
        ][:7]

        daily_data = []
        for date_value in sync_dates:
            date_obj = datetime.strptime(date_value, "%Y-%m-%d").date()
            for item in self.stock_cache.get_all_by_date(date_obj)[:1000]:
                daily_data.append(self._daily_item(item, date_value))

        stock_codes = {item["stock_code"] for item in daily_data}
        stocks_data = []
        for code in stock_codes:
            stock = self.stock_cache.stocks.get(code)
            if stock:
                stocks_data.append(
                    {
                        "stock_code": stock.stock_code,
                        "stock_name": stock.stock_name,
                        "industry": stock.industry,
                    }
                )

        return {
            "stocks": stocks_data,
            "daily_data": daily_data,
            "sync_dates": sync_dates,
            "sync_time": _utcnow_naive().isoformat(),
            "has_more": len(sync_dates) == 7,
        }

    def get_daily_sync(self, query: GetDailySyncQuery) -> dict:
        settings = query.user_settings
        if settings is None:
            raise InvalidOfflineSyncRequestError("缺少离线同步用户设置")
        self._ensure_enabled(settings)

        try:
            datetime.strptime(query.date, "%Y-%m-%d")
        except ValueError as exc:
            raise InvalidOfflineSyncRequestError("无效的日期格式，应为 YYYY-MM-DD") from exc

        cutoff = (_utcnow_naive() - timedelta(days=settings.offline_days)).strftime("%Y-%m-%d")
        if query.date < cutoff:
            raise InvalidOfflineSyncRequestError(f"日期超出离线范围，最早可同步: {cutoff}")

        date_obj = datetime.strptime(query.date, "%Y-%m-%d").date()
        date_data = self.stock_cache.get_all_by_date(date_obj)
        if not date_data:
            return {"date": query.date, "count": 0, "data": [], "has_more": False}

        total = len(date_data)
        page_data = date_data[query.offset : query.offset + query.limit]
        result_data = [
            {
                **self._daily_item(item, query.date),
                "volume": item.get("volume"),
            }
            for item in page_data
        ]
        return {
            "date": query.date,
            "total": total,
            "offset": query.offset,
            "limit": query.limit,
            "count": len(result_data),
            "data": result_data,
            "has_more": query.offset + query.limit < total,
        }

    def get_stocks(self, query: GetOfflineStocksQuery) -> dict:
        self._ensure_enabled(query.user_settings)
        stocks_data = [
            {
                "stock_code": stock.stock_code,
                "stock_name": stock.stock_name,
                "industry": stock.industry,
            }
            for stock in self.stock_cache.stocks.values()
        ]
        return {"count": len(stocks_data), "stocks": stocks_data, "sync_time": _utcnow_naive().isoformat()}

    def get_dates(self, query: GetOfflineDatesQuery) -> dict:
        all_dates = [date_item.strftime("%Y-%m-%d") for date_item in self.stock_cache.get_available_dates()]
        cutoff = (_utcnow_naive() - timedelta(days=query.user_settings.offline_days)).strftime("%Y-%m-%d")
        available_dates = [date_value for date_value in all_dates if date_value >= cutoff]
        return {
            "dates": available_dates,
            "total": len(available_dates),
            "max_days": query.user_settings.offline_days,
            "cutoff": cutoff,
        }

    @staticmethod
    def _daily_item(item: dict[str, Any], date_value: str) -> dict[str, Any]:
        return {
            "stock_code": item["stock_code"],
            "date": date_value,
            "rank": item["rank"],
            "total_score": item.get("total_score"),
            "price_change": item.get("price_change"),
            "turnover_rate_percent": item.get("turnover_rate"),
            "volume_days": item.get("volume_days"),
            "volatility": item.get("volatility"),
        }

    @staticmethod
    def _ensure_enabled(settings: OfflineSyncUserSettings) -> None:
        if not settings.offline_enabled:
            raise OfflineSyncDisabledError("离线功能未启用")


def _utcnow_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)
