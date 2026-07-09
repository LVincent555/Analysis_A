"""Adapters for legacy hot spots query services."""

from __future__ import annotations

import logging
from typing import Any

from ....core.caching import cache
from ....services.hot_spots_cache import HotSpotsCache
from ....services.numpy_cache_middleware import numpy_cache
from ..application.queries import GetHotSpotsFullQuery

logger = logging.getLogger(__name__)

HOT_SPOTS_CACHE_TTL = 90000


class LegacyHotSpotsAnalysisAdapter:
    def __init__(
        self,
        *,
        numpy_cache_backend=numpy_cache,
        hot_spots_cache=HotSpotsCache,
        api_cache=cache,
    ) -> None:
        self.numpy_cache = numpy_cache_backend
        self.hot_spots_cache = hot_spots_cache
        self.api_cache = api_cache

    def get_hot_spots_full(self, query: GetHotSpotsFullQuery) -> dict[str, Any] | None:
        date_value = query.date
        if not date_value:
            latest_date = self.numpy_cache.get_latest_date()
            if not latest_date:
                return None
            date_value = latest_date.strftime("%Y%m%d")

        cache_key = f"hotspots_full_{date_value}"
        cached = self.api_cache.get_api_cache("hotspots", cache_key)
        if cached:
            logger.debug("Hot spots cache hit: %s", date_value)
            return cached

        stocks = self.hot_spots_cache.get_full_data(date_value)
        result = {
            "date": date_value,
            "total_count": len(stocks),
            "stocks": stocks,
        }
        self.api_cache.set_api_cache("hotspots", cache_key, result, ttl=HOT_SPOTS_CACHE_TTL)
        return result
