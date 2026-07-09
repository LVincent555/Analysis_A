"""Adapters for legacy industry analysis services."""

from __future__ import annotations

import ast
from collections import Counter, defaultdict
from datetime import datetime

from ..application.errors import AnalysisDataNotFoundError
from ..application.queries import (
    GetIndustryStatsQuery,
    GetIndustryTrendQuery,
    GetTopIndustryQuery,
    GetWeightedIndustryQuery,
)
from ....core.caching import cache
from ....models import IndustryStats, IndustryStatsWeighted
from ....models.industry import IndustryStatWeighted
from ....services.industry_service_db import industry_service_db
from ....services.numpy_cache_middleware import numpy_cache


def _normalize_industry(industry) -> str:
    if isinstance(industry, list) and industry:
        return industry[0]
    if isinstance(industry, str):
        if industry.startswith("["):
            try:
                industry_list = ast.literal_eval(industry)
                return industry_list[0] if industry_list else "未知"
            except Exception:
                return industry.strip("[]").strip("'\"")
        return industry or "未知"
    return "未知"


class LegacyIndustryAnalysisAdapter:
    def __init__(
        self,
        *,
        industry_service=industry_service_db,
        stock_cache=numpy_cache,
        api_cache=cache,
    ) -> None:
        self.industry_service = industry_service
        self.stock_cache = stock_cache
        self.cache = api_cache

    def get_industry_stats(self, query: GetIndustryStatsQuery):
        return self.industry_service.analyze_industry(period=query.period, top_n=query.top_n)

    def get_industry_trend(self, query: GetIndustryTrendQuery) -> dict:
        cache_key = f"industry_trend:{query.period}:{query.top_n}:{query.target_date or 'latest'}"
        cached_result = self.cache.get_api_cache("industry_trend", cache_key)
        if cached_result is not None:
            return cached_result

        if query.target_date:
            target_date = datetime.strptime(query.target_date, "%Y%m%d").date()
        else:
            target_date = self.stock_cache.get_latest_date()

        if not target_date:
            return {"data": [], "industries": []}

        all_dates = self.stock_cache.get_dates_range(query.period * 2)
        target_dates = [item for item in all_dates if item <= target_date][: query.period]
        if not target_dates:
            return {"data": [], "industries": []}

        all_stock_codes = set()
        date_stocks_map = {}
        for date_obj in target_dates:
            top_stocks = self.stock_cache.get_top_n_by_rank(date_obj, query.top_n)
            date_stocks_map[date_obj] = top_stocks
            all_stock_codes.update(stock["stock_code"] for stock in top_stocks)

        stocks_info = self.stock_cache.get_stocks_batch(list(all_stock_codes))
        date_industry_map = {}
        all_industries = set()

        for date_obj, top_stocks in date_stocks_map.items():
            date_str = date_obj.strftime("%Y%m%d")
            date_industry_map[date_str] = Counter()
            for stock_data in top_stocks:
                stock_info = stocks_info.get(stock_data["stock_code"])
                if stock_info and stock_info.industry:
                    industry = _normalize_industry(stock_info.industry)
                    all_industries.add(industry)
                    date_industry_map[date_str][industry] += 1

        result = {
            "data": [
                {
                    "date": date_str,
                    "industry_counts": dict(date_industry_map[date_str]),
                }
                for date_str in sorted(date_industry_map.keys())
            ],
            "industries": sorted(list(all_industries)),
        }
        self.cache.set_api_cache("industry_trend", cache_key, result, ttl=300)
        return result

    def get_top_industry(self, query: GetTopIndustryQuery) -> IndustryStats:
        if query.target_date:
            target_date = datetime.strptime(query.target_date, "%Y%m%d").date()
        else:
            target_date = self.stock_cache.get_latest_date()

        if not target_date:
            raise AnalysisDataNotFoundError("没有可用数据")

        stats = self.industry_service.analyze_industry(period=1, top_n=query.limit, target_date=target_date)
        return IndustryStats(
            date=target_date.strftime("%Y%m%d"),
            total_stocks=sum(item.count for item in stats),
            stats=stats,
        )

    def get_weighted_industry(self, query: GetWeightedIndustryQuery) -> IndustryStatsWeighted:
        if query.target_date:
            target_date = datetime.strptime(query.target_date, "%Y%m%d").date()
        else:
            target_date = self.stock_cache.get_latest_date()

        if not target_date:
            raise AnalysisDataNotFoundError("没有可用数据")

        date_str = target_date.strftime("%Y%m%d")
        cache_key = f"weighted_{date_str}_{query.k}_{query.metric}"
        cached = self.cache.get_api_cache("industry_weighted", cache_key)
        if cached is not None:
            return cached

        all_stocks = self.stock_cache.get_all_by_date(target_date)
        if not all_stocks:
            raise AnalysisDataNotFoundError("该日期没有数据")

        stock_codes = [stock["stock_code"] for stock in all_stocks]
        stocks_info = self.stock_cache.get_stocks_batch(stock_codes)
        rows = []
        for stock_data in all_stocks:
            stock_info = stocks_info.get(stock_data["stock_code"])
            if stock_info and stock_info.industry:
                rows.append((stock_data["rank"], stock_data["total_score"], stock_info.industry))

        if not rows:
            raise AnalysisDataNotFoundError("该日期没有数据")

        industry_data = defaultdict(lambda: {"count": 0, "total_heat_rank": 0.0, "total_score": 0.0})
        total_stocks = len(rows)
        for rank, score, industry in rows:
            normalized = _normalize_industry(industry)
            industry_data[normalized]["count"] += 1
            industry_data[normalized]["total_heat_rank"] += 1.0 / (rank ** query.k)
            industry_data[normalized]["total_score"] += float(score) if score else 0.0

        stats = []
        for industry, data in industry_data.items():
            count = data["count"]
            stats.append(
                IndustryStatWeighted(
                    industry=industry,
                    count=count,
                    percentage=round(count / total_stocks * 100, 2),
                    total_heat_rank=data["total_heat_rank"],
                    avg_heat_rank=data["total_heat_rank"] / count,
                    total_score=data["total_score"],
                    avg_score=data["total_score"] / count,
                )
            )

        if query.metric == "B1":
            stats.sort(key=lambda item: item.total_heat_rank, reverse=True)
        elif query.metric == "B2":
            stats.sort(key=lambda item: item.avg_heat_rank, reverse=True)
        elif query.metric == "C1":
            stats.sort(key=lambda item: item.total_score, reverse=True)
        elif query.metric == "C2":
            stats.sort(key=lambda item: item.avg_score, reverse=True)

        result = IndustryStatsWeighted(
            date=date_str,
            total_stocks=total_stocks,
            k_value=query.k,
            metric_type=query.metric,
            stats=stats,
        )
        self.cache.set_api_cache("industry_weighted", cache_key, result, ttl=90000)
        return result
