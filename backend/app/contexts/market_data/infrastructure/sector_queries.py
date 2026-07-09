"""Adapters for legacy sector query services."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from ..application.errors import MarketDataNotFoundError
from ..application.queries import (
    GetSectorDetailQuery,
    GetSectorRankChangesQuery,
    GetSectorRankingQuery,
    GetSectorRawDataQuery,
    GetSectorTrendQuery,
    SearchSectorsQuery,
)
from ....services.numpy_cache_middleware import numpy_cache
from ....services.sector_service_db import sector_service_db


class LegacySectorQueryAdapter:
    def __init__(
        self,
        *,
        sector_service=sector_service_db,
        sector_cache=numpy_cache,
    ) -> None:
        self.sector_service = sector_service
        self.sector_cache = sector_cache

    def get_available_dates(self) -> list[str]:
        return self.sector_service.get_available_dates()

    def get_sector_ranking(self, query: GetSectorRankingQuery):
        return self.sector_service.get_sector_ranking(target_date=query.target_date, limit=query.limit)

    def get_sector_raw_data(self, query: GetSectorRawDataQuery) -> dict:
        if query.target_date:
            target_date = datetime.strptime(query.target_date, "%Y%m%d").date()
        else:
            target_date = self.sector_cache.get_sector_latest_date()

        if not target_date:
            raise MarketDataNotFoundError("没有可用数据")

        raw_data = self.sector_cache.get_top_n_sectors(target_date, query.limit)
        data = []
        for row in raw_data:
            sector_info = self.sector_cache.get_sector_info(row.get("sector_id"))
            data.append(
                {
                    "name": sector_info.sector_name if sector_info else f"板块{row.get('sector_id')}",
                    "rank": row.get("rank"),
                    "total_score": row.get("total_score"),
                    "price_change": row.get("price_change"),
                    "open_price": row.get("open_price"),
                    "high_price": row.get("high_price"),
                    "low_price": row.get("low_price"),
                    "close_price": row.get("close_price"),
                    "turnover_rate": row.get("turnover_rate"),
                    "volume_days": row.get("volume_days"),
                    "avg_volume_ratio_50": row.get("avg_volume_ratio_50"),
                    "volume": row.get("volume"),
                    "volatility": row.get("volatility"),
                    "beta": row.get("beta"),
                    "correlation": row.get("correlation"),
                    "long_term": row.get("long_term"),
                    "short_term": row.get("short_term"),
                    "overbought": row.get("overbought"),
                    "oversold": row.get("oversold"),
                    "macd_signal": row.get("macd_signal"),
                    "rsi": row.get("rsi"),
                    "dif": row.get("dif"),
                    "dem": row.get("dem"),
                    "adx": row.get("adx"),
                    "slowk": row.get("slowk"),
                }
            )

        return {
            "date": target_date.strftime("%Y%m%d"),
            "total_count": len(data),
            "data": data,
        }

    def search_sectors(self, query: SearchSectorsQuery) -> list[str]:
        return self.sector_service.search_sectors(query.keyword)

    def get_sector_trend(self, query: GetSectorTrendQuery) -> dict:
        if query.target_date:
            end_date = datetime.strptime(query.target_date, "%Y%m%d").date()
        else:
            end_date = self.sector_cache.get_sector_latest_date()

        if not end_date:
            raise MarketDataNotFoundError("没有可用数据")

        all_dates = self.sector_cache.get_sector_dates_range(query.days * 2)
        dates = [item for item in all_dates if item <= end_date][: query.days]
        if not dates:
            raise MarketDataNotFoundError("没有足够的历史数据")

        dates.reverse()
        latest_date = dates[-1]
        top_sectors_data = self.sector_cache.get_top_n_sectors(latest_date, query.limit)
        if not top_sectors_data:
            raise MarketDataNotFoundError("没有板块数据")

        sector_ids = [sector["sector_id"] for sector in top_sectors_data]
        sector_dict = defaultdict(lambda: {"ranks": [], "scores": []})
        date_strs = [item.strftime("%Y%m%d") for item in dates]

        for sector_id in sector_ids:
            history_data = self.sector_cache.get_sector_history(sector_id, len(dates), end_date=latest_date)
            if history_data:
                sector_info = self.sector_cache.get_sector_info(sector_id)
                sector_dict[sector_id]["name"] = sector_info.sector_name if sector_info else str(sector_id)
                sector_dict[sector_id]["ranks"] = [None] * len(dates)
                sector_dict[sector_id]["scores"] = [None] * len(dates)

                for data in history_data:
                    if data["date"] in date_strs:
                        date_index = date_strs.index(data["date"])
                        sector_dict[sector_id]["ranks"][date_index] = data["rank"]
                        sector_dict[sector_id]["scores"][date_index] = data["total_score"]

        sectors = []
        for sector_id in sector_ids:
            if sector_id in sector_dict:
                sectors.append(sector_dict[sector_id])

        return {
            "dates": date_strs,
            "sectors": sectors,
        }

    def get_sector_rank_changes(self, query: GetSectorRankChangesQuery) -> dict:
        if query.target_date:
            current_date = datetime.strptime(query.target_date, "%Y%m%d").date()
        else:
            current_date = self.sector_cache.get_sector_latest_date()

        if not current_date:
            raise MarketDataNotFoundError("没有可用数据")

        all_dates = self.sector_cache.get_sector_dates_range(30)
        available_dates = [item for item in all_dates if item < current_date]
        if not available_dates:
            raise MarketDataNotFoundError("没有足够的历史数据")

        compare_date = available_dates[min(query.compare_days - 1, len(available_dates) - 1)]
        current_data_list = self.sector_cache.get_sector_all_by_date(current_date)
        compare_data_list = self.sector_cache.get_sector_all_by_date(compare_date)
        compare_dict = {data["sector_id"]: data["rank"] for data in compare_data_list}

        statistics = {
            "new_entries": 0,
            "rank_up": 0,
            "rank_down": 0,
            "rank_same": 0,
        }
        sectors = []
        for data in current_data_list:
            previous_rank = compare_dict.get(data["sector_id"])
            if previous_rank is None:
                rank_change = None
                is_new = True
                statistics["new_entries"] += 1
            else:
                rank_change = previous_rank - data["rank"]
                is_new = False
                if rank_change > 0:
                    statistics["rank_up"] += 1
                elif rank_change < 0:
                    statistics["rank_down"] += 1
                else:
                    statistics["rank_same"] += 1

            sector_info = self.sector_cache.get_sector_info(data["sector_id"])
            sectors.append(
                {
                    "name": sector_info.sector_name if sector_info else str(data["sector_id"]),
                    "current_rank": data["rank"],
                    "previous_rank": previous_rank,
                    "rank_change": rank_change,
                    "is_new": is_new,
                    "total_score": data["total_score"],
                    "price_change": data["price_change"],
                    "volume_days": data["volume_days"],
                }
            )

        sectors.sort(key=lambda item: item["current_rank"])
        return {
            "date": current_date.strftime("%Y%m%d"),
            "compare_date": compare_date.strftime("%Y%m%d"),
            "statistics": statistics,
            "sectors": sectors,
        }

    def get_sector_detail(self, query: GetSectorDetailQuery):
        return self.sector_service.get_sector_detail(
            sector_name=query.sector_name,
            days=query.days,
            target_date=query.target_date,
        )
