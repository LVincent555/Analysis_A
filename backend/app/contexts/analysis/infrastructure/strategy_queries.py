"""Adapters for legacy strategy analysis services."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime
from typing import Any

from ....core.caching import cache
from ....services.numpy_cache_middleware import numpy_cache
from ....services.strategies.needle_under_20 import NeedleUnder20Strategy, get_washout_detector
from ..application.queries import GetNeedleUnder20StockDetailQuery, GetNeedleUnder20StocksQuery

logger = logging.getLogger(__name__)

STRATEGY_CACHE_TTL = 90000


class LegacyNeedleUnder20StrategyAdapter:
    def __init__(
        self,
        *,
        numpy_cache_backend=numpy_cache,
        api_cache=cache,
        strategy_factory=NeedleUnder20Strategy,
        detector_factory=get_washout_detector,
    ) -> None:
        self.numpy_cache = numpy_cache_backend
        self.api_cache = api_cache
        self.strategy_factory = strategy_factory
        self.detector_factory = detector_factory

    async def get_needle_under_20_stocks(self, query: GetNeedleUnder20StocksQuery) -> dict[str, Any]:
        target_date = self._resolve_target_date(query.date)
        if not target_date:
            return self._empty_response()

        date_str = target_date.strftime("%Y%m%d")
        cache_key = (
            f"needle20:{date_str}:{query.days}:{query.min_score}:{query.pattern}:"
            f"{query.bbi_filter}:{query.max_drop_pct}:{query.long_period}"
        )
        cached = self.api_cache.get_api_cache("needle20", cache_key)
        if cached:
            logger.info("Strategy cache hit: %s", cache_key)
            return cached

        return await asyncio.to_thread(
            self._compute_needle_under_20,
            target_date,
            query,
            cache_key,
        )

    def get_needle_under_20_stock_detail(self, query: GetNeedleUnder20StockDetailQuery) -> dict[str, Any] | None:
        target_date = self._resolve_target_date(query.date)
        if not target_date:
            return None

        stock_data = self.numpy_cache.get_stock_data_for_strategy(query.stock_code, target_date, lookback_days=30)
        if not stock_data:
            return None

        strategy = self.strategy_factory()
        result = strategy.analyze(
            stock_code=stock_data["stock_code"],
            stock_name=stock_data["stock_name"],
            signal_date=stock_data["signal_date"],
            closes=stock_data["closes"],
            highs=stock_data["highs"],
            lows=stock_data["lows"],
            opens=stock_data["opens"],
            volumes=stock_data["volumes"],
            turnovers=stock_data["turnovers"],
            ranks=stock_data["ranks"],
        )

        stock_info = self.numpy_cache.get_stock_info(query.stock_code)
        result_dict = result.to_dict()
        result_dict["industry"] = stock_info.industry if stock_info else "鏈煡"
        return result_dict

    def _resolve_target_date(self, date_value: str | None):
        if date_value:
            return datetime.strptime(date_value, "%Y%m%d").date()
        return self.numpy_cache.get_latest_date()

    def _get_detector(self, long_period: int):
        return self.detector_factory(short_period=3, long_period=long_period)

    def _compute_needle_under_20(
        self,
        target_date,
        query: GetNeedleUnder20StocksQuery,
        cache_key: str,
    ) -> dict[str, Any]:
        start_time = time.time()
        signal_dates = [target_date]
        all_dates = self.numpy_cache.get_dates_range(query.days * 2)
        display_dates = [date_item for date_item in all_dates if date_item <= target_date][: query.days]

        if not signal_dates:
            return self._empty_response()

        results: list[dict[str, Any]] = []
        industry_count: dict[str, int] = {}
        seen_stocks: set[str] = set()

        available_dates = self.numpy_cache.get_dates_range(50)
        data_days = len(available_dates)
        required_days = query.long_period + 7
        data_sufficient = data_days >= required_days

        for check_date in signal_dates:
            for stock_code in self.numpy_cache.get_all_stocks().keys():
                if stock_code in seen_stocks:
                    continue

                try:
                    stock_data = self.numpy_cache.get_stock_data_for_strategy(
                        stock_code,
                        check_date,
                        lookback_days=30,
                    )
                    if not stock_data:
                        continue

                    price_changes = stock_data.get("price_changes", [])
                    if price_changes:
                        today_pct = price_changes[-1]
                        if today_pct > 5:
                            continue
                        if query.max_drop_pct is not None and today_pct < -query.max_drop_pct:
                            continue

                    if len(stock_data["closes"]) < required_days:
                        continue

                    washout = self._get_detector(query.long_period).detect(
                        stock_data["closes"],
                        stock_data["highs"],
                        stock_data["lows"],
                        stock_data.get("bbis", []),
                    )
                    if not washout or not washout.is_valid:
                        continue

                    if query.bbi_filter and washout.bbi_break:
                        continue

                    today_change_pct = price_changes[-1] if price_changes else washout.price_change_pct
                    if query.max_drop_pct is not None and today_change_pct < -query.max_drop_pct:
                        continue

                    if query.pattern and washout.pattern.value != query.pattern:
                        continue

                    seen_stocks.add(stock_code)
                    stock_info = self.numpy_cache.get_stock_info(stock_code)

                    washout_dict = washout.to_dict()
                    washout_dict["鑲′环娑ㄨ穼"] = f"{today_change_pct:+.2f}%"

                    result_dict = {
                        "stock_code": stock_data["stock_code"],
                        "stock_name": stock_data["stock_name"],
                        "signal_date": stock_data["signal_date"],
                        "is_triggered": True,
                        "pattern": washout.pattern.value,
                        "pattern_name": washout.pattern_name,
                        "total_score": washout.score,
                        "industry": stock_info.industry if stock_info else "鏈煡",
                        "latest_rank": stock_data["ranks"][-1] if stock_data["ranks"] else 0,
                        "washout_analysis": washout_dict,
                    }
                    results.append(result_dict)

                    industry = result_dict["industry"]
                    industry_count[industry] = industry_count.get(industry, 0) + 1
                except Exception as exc:
                    logger.debug("Failed to analyze stock %s on %s: %s", stock_code, check_date, exc)
                    continue

        results.sort(key=lambda item: (-item["total_score"], item.get("latest_rank", 9999)))
        for index, result in enumerate(results, 1):
            result["rank"] = index

        response = {
            "data": results,
            "total_count": len(results),
            "date_range": [date_item.strftime("%Y%m%d") for date_item in display_dates],
            "industry_distribution": industry_count,
            "long_period": query.long_period,
            "data_days": data_days,
            "required_days": required_days,
            "data_sufficient": data_sufficient,
        }

        self.api_cache.set_api_cache("needle20", cache_key, response, ttl=STRATEGY_CACHE_TTL)
        logger.info("Strategy calculation completed: %s rows in %.2fs", len(results), time.time() - start_time)
        return response

    @staticmethod
    def _empty_response() -> dict[str, Any]:
        return {"data": [], "total_count": 0, "date_range": [], "industry_distribution": {}}
