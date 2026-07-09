"""Adapters for legacy stock query services."""

from __future__ import annotations

from datetime import datetime

from ..application.queries import (
    GetStockRawDataQuery,
    SearchStockFullQuery,
    SearchStockQuery,
    StockSignalThresholdSettings,
)
from ....services.numpy_cache_middleware import numpy_cache
from ....services.signal_calculator import SignalThresholds
from ....services.stock_service_db import stock_service_db


def _to_legacy_signal_thresholds(settings: StockSignalThresholdSettings | None) -> SignalThresholds | None:
    if settings is None:
        return None

    return SignalThresholds(
        hot_list_mode=settings.hot_list_mode,
        hot_list_version=settings.hot_list_version,
        hot_list_top=settings.hot_list_top,
        hot_list_top2=settings.hot_list_top2,
        hot_list_top3=settings.hot_list_top3,
        hot_list_top4=settings.hot_list_top4,
        rank_jump_min=settings.rank_jump_min,
        rank_jump_large=settings.rank_jump_large,
        steady_rise_days_min=settings.steady_rise_days_min,
        price_surge_min=settings.price_surge_min,
        volume_surge_min=settings.volume_surge_min,
        volatility_surge_min=settings.volatility_surge_min,
    )


class LegacyStockQueryAdapter:
    def __init__(
        self,
        *,
        stock_service=stock_service_db,
        stock_cache=numpy_cache,
    ) -> None:
        self.stock_service = stock_service
        self.stock_cache = stock_cache

    def get_stock_raw_data(self, query: GetStockRawDataQuery) -> dict | None:
        if query.target_date:
            target_date = datetime.strptime(query.target_date, "%Y%m%d").date()
        else:
            target_date = self.stock_cache.get_latest_date()

        if not target_date:
            return None

        raw_data = self.stock_cache.get_top_n_by_rank(target_date, query.limit)
        data = []
        for row in raw_data:
            stock_info = self.stock_cache.get_stock_info(row["stock_code"])
            data.append(
                {
                    "code": row["stock_code"],
                    "name": stock_info.stock_name if stock_info else "",
                    "industry": stock_info.industry if stock_info else "未知",
                    "rank": row["rank"],
                    "total_score": row.get("total_score"),
                    "price_change": row.get("price_change"),
                    "close_price": row.get("close_price"),
                    "turnover_rate": row.get("turnover_rate"),
                    "volume_days": row.get("volume_days"),
                    "avg_volume_ratio_50": row.get("avg_volume_ratio_50"),
                    "volatility": row.get("volatility"),
                    "market_cap": row.get("market_cap"),
                }
            )

        return {
            "date": target_date.strftime("%Y%m%d"),
            "total_count": len(data),
            "data": data,
        }

    def search_stock_full(self, query: SearchStockFullQuery):
        return self.stock_service.search_stock_full(query.keyword, query.limit)

    def search_stock(self, query: SearchStockQuery):
        return self.stock_service.search_stock(
            query.keyword,
            target_date=query.target_date,
            signal_thresholds=_to_legacy_signal_thresholds(query.signal_thresholds),
        )
