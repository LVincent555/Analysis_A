"""SQL adapters for board heat queries."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ....core.caching import cache
from ..application.errors import BoardHeatDataNotFoundError
from ..application.queries import (
    GetBoardDetailQuery,
    GetBoardHeatRankingQuery,
    GetBoardHistoryQuery,
    GetMarketTreemapQuery,
    GetMiningHiddenGemsQuery,
    GetMiningResonanceQuery,
    GetSectorMatrixQuery,
    GetStockBoardDnaQuery,
    GetStocksBoardSignalsBatchQuery,
)

BOARD_HEAT_CACHE_TTL = 300
BOARD_DETAIL_CACHE_TTL = 180
BATCH_SIGNAL_CACHE_TTL = 120


def _date_to_string(value: Any) -> str:
    return value.strftime("%Y-%m-%d") if hasattr(value, "strftime") else str(value)


def _float_or_none(value: Any) -> float | None:
    return float(value) if value is not None else None


def _float_or_zero(value: Any) -> float:
    return float(value) if value is not None else 0.0


class SqlBoardHeatQueryAdapter:
    def __init__(self, db: Session, *, api_cache=cache) -> None:
        self.db = db
        self.api_cache = api_cache

    def get_board_heat_ranking(self, query: GetBoardHeatRankingQuery) -> dict[str, Any]:
        trade_date = query.trade_date
        if not trade_date:
            result = self.db.execute(text("SELECT MAX(trade_date) FROM ext_board_heat_daily")).fetchone()
            if not result or not result[0]:
                raise BoardHeatDataNotFoundError("暂无热度数据")
            trade_date = _date_to_string(result[0])

        cache_key = (
            f"{trade_date}_{query.board_type}_{query.limit}_{query.offset}_"
            f"{query.exclude_blacklist}_{query.max_stock_count}"
        )
        cached = self.api_cache.get_api_cache("board_ranking", cache_key)
        if cached:
            return cached

        snap_result = self.db.execute(
            text("SELECT MAX(date) FROM ext_board_daily_snap WHERE date <= :d"),
            {"d": trade_date},
        ).fetchone()
        snap_date = _date_to_string(snap_result[0]) if snap_result and snap_result[0] else trade_date

        where_conditions = ["h.trade_date = :trade_date"]
        params: dict[str, Any] = {"trade_date": trade_date, "limit": query.limit, "offset": query.offset}

        if query.board_type:
            where_conditions.append("b.board_type = :board_type")
            params["board_type"] = query.board_type

        if query.exclude_blacklist:
            where_conditions.append(
                """
                NOT EXISTS (
                    SELECT 1 FROM board_blacklist bl
                    WHERE b.board_name LIKE '%' || bl.keyword || '%'
                    AND bl.level = 'BLACK' AND bl.is_active = TRUE
                )
                """
            )

        if query.max_stock_count is not None:
            where_conditions.append("h.stock_count <= :max_stock_count")
            params["max_stock_count"] = query.max_stock_count

        where_clause = "WHERE " + " AND ".join(where_conditions)
        sql = f"""
        SELECT
            h.board_id, b.board_code, b.board_name, b.board_type,
            h.stock_count, h.heat_pct, h.b1_rank_sum, h.c2_score_avg,
            CASE WHEN bl.id IS NOT NULL THEN TRUE ELSE FALSE END as is_blacklisted
        FROM ext_board_heat_daily h
        JOIN ext_board_list b ON h.board_id = b.id
        LEFT JOIN board_blacklist bl ON b.board_name LIKE '%' || bl.keyword || '%' AND bl.level = 'BLACK'
        {where_clause}
        ORDER BY h.heat_pct DESC
        LIMIT :limit OFFSET :offset
        """
        rows = self.db.execute(text(sql), params).fetchall()

        count_sql = f"""
        SELECT COUNT(*) FROM ext_board_heat_daily h
        JOIN ext_board_list b ON h.board_id = b.id
        {where_clause}
        """
        total = self.db.execute(text(count_sql), params).scalar()

        response = {
            "trade_date": trade_date,
            "snap_date": snap_date,
            "total_count": total or 0,
            "items": [
                {
                    "board_id": row[0],
                    "board_code": row[1],
                    "board_name": row[2],
                    "board_type": row[3],
                    "stock_count": row[4],
                    "heat_pct": _float_or_zero(row[5]),
                    "b1_rank_sum": _float_or_none(row[6]),
                    "c2_score_avg": _float_or_none(row[7]),
                    "is_blacklisted": row[8],
                }
                for row in rows
            ],
        }
        self.api_cache.set_api_cache("board_ranking", cache_key, response, ttl=BOARD_HEAT_CACHE_TTL)
        return response

    def get_stock_board_dna(self, query: GetStockBoardDnaQuery) -> dict[str, Any]:
        trade_date = query.trade_date
        if not trade_date:
            result = self.db.execute(text("SELECT MAX(trade_date) FROM cache_stock_board_signal")).fetchone()
            if not result or not result[0]:
                raise BoardHeatDataNotFoundError("暂无信号数据")
            trade_date = str(result[0])

        result = self.db.execute(
            text(
                """
                SELECT stock_code, stock_name, signal_level, final_score,
                       final_score_pct, fallback_reason, dna_json
                FROM cache_stock_board_signal
                WHERE stock_code = :stock_code AND trade_date = :trade_date
                """
            ),
            {"stock_code": query.stock_code, "trade_date": trade_date},
        ).fetchone()
        if not result:
            raise BoardHeatDataNotFoundError("未找到该股信号数据")

        dna_data: dict[str, Any] = {}
        if result[6]:
            try:
                dna_data = json.loads(result[6])
            except Exception:
                dna_data = {}

        close_price_row = self.db.execute(
            text("SELECT close_price FROM daily_stock_data WHERE stock_code = :stock_code AND date = :trade_date"),
            {"stock_code": query.stock_code, "trade_date": trade_date},
        ).fetchone()
        close_price = _float_or_none(close_price_row[0]) if close_price_row else None

        signal_level = result[2] or "NONE"
        fallback_reason = result[5]
        if query.min_price is not None and close_price is not None and close_price < float(query.min_price):
            signal_level = "NONE"
            reason = f"低价过滤(<{float(query.min_price):.2f})"
            fallback_reason = f"{fallback_reason} | {reason}" if fallback_reason else reason

        snap_row = self.db.execute(
            text("SELECT MAX(date) FROM ext_board_daily_snap WHERE date <= :d"),
            {"d": trade_date},
        ).fetchone()
        snap_date = snap_row[0] if snap_row and snap_row[0] else None

        all_related_boards = []
        if snap_date:
            rel_rows = self.db.execute(
                text(
                    """
                    SELECT s.board_id, b.board_name, b.board_type, h.heat_pct, s.board_rank
                    FROM ext_board_daily_snap s
                    JOIN ext_board_list b ON s.board_id = b.id
                    LEFT JOIN ext_board_heat_daily h ON h.board_id = s.board_id AND h.trade_date = :trade_date
                    WHERE s.stock_code = :stock_code AND s.date = :snap_date
                    ORDER BY COALESCE(h.heat_pct, 0) DESC
                    LIMIT 200
                    """
                ),
                {"stock_code": query.stock_code, "trade_date": trade_date, "snap_date": snap_date},
            ).fetchall()
            all_related_boards = [
                {
                    "board_id": row[0],
                    "board_name": row[1],
                    "board_type": row[2],
                    "heat_pct": _float_or_none(row[3]),
                    "board_rank": row[4],
                }
                for row in rel_rows
            ]

        return {
            "stock_code": result[0],
            "stock_name": result[1],
            "trade_date": trade_date,
            "signal_level": signal_level,
            "final_score": _float_or_zero(result[3]),
            "final_score_pct": _float_or_zero(result[4]),
            "fallback_reason": fallback_reason,
            "dna_json": dna_data,
            "all_related_boards": all_related_boards,
        }

    def get_stocks_board_signals_batch(self, query: GetStocksBoardSignalsBatchQuery) -> dict[str, Any]:
        if not query.stock_codes:
            return {"stocks": []}

        trade_date = query.trade_date
        if not trade_date:
            result = self.db.execute(text("SELECT MAX(trade_date) FROM cache_stock_board_signal")).fetchone()
            if not result or not result[0]:
                return {"stocks": [], "trade_date": None}
            trade_date = _date_to_string(result[0])

        codes_hash = hashlib.md5("|".join(sorted(query.stock_codes)).encode()).hexdigest()[:12]
        cache_key = f"{trade_date}_{codes_hash}_{query.min_price}"
        cached = self.api_cache.get_api_cache("batch_signal", cache_key)
        if cached:
            return cached

        placeholders = ", ".join([f":code_{index}" for index in range(len(query.stock_codes))])
        params: dict[str, Any] = {"trade_date": trade_date}
        for index, code in enumerate(query.stock_codes):
            params[f"code_{index}"] = code

        sql = f"""
        SELECT
            c.stock_code, c.signal_level, c.max_driver_name, c.max_driver_board_id,
            c.max_driver_type, c.max_driver_heat_pct, c.industry_safe, c.final_score,
            d.close_price
        FROM cache_stock_board_signal c
        LEFT JOIN daily_stock_data d ON c.stock_code = d.stock_code AND d.date = :trade_date
        WHERE c.trade_date = :trade_date AND c.stock_code IN ({placeholders})
        """
        rows = self.db.execute(text(sql), params).fetchall()

        response = {
            "stocks": [
                {
                    "stock_code": row[0],
                    "board_signal_level": (
                        "NONE"
                        if query.min_price is not None and row[8] is not None and float(row[8]) < float(query.min_price)
                        else (row[1] or "NONE")
                    ),
                    "board_signal_label": row[2] or "",
                    "max_concept_board_id": row[3],
                    "max_concept_board_type": row[4],
                    "max_concept_heat_pct": _float_or_none(row[5]),
                    "industry_safe": row[6] or False,
                    "final_score": _float_or_none(row[7]),
                }
                for row in rows
            ],
            "trade_date": trade_date,
        }
        self.api_cache.set_api_cache("batch_signal", cache_key, response, ttl=BATCH_SIGNAL_CACHE_TTL)
        return response

    def get_board_detail(self, query: GetBoardDetailQuery) -> dict[str, Any]:
        trade_date = query.trade_date
        if not trade_date:
            result = self.db.execute(text("SELECT MAX(trade_date) FROM ext_board_heat_daily")).fetchone()
            if not result or not result[0]:
                raise BoardHeatDataNotFoundError("暂无热度数据")
            trade_date = _date_to_string(result[0])

        cache_key = f"{query.board_id}_{trade_date}_{query.limit}_{query.offset}_{query.sort_by}_{query.min_price}"
        cached = self.api_cache.get_api_cache("board_detail", cache_key)
        if cached:
            return cached

        result = self.db.execute(
            text(
                """
                SELECT
                    h.board_id, b.board_code, b.board_name, b.board_type,
                    h.trade_date, h.stock_count, h.heat_pct, h.heat_raw,
                    h.b1_rank_sum, h.b2_rank_avg, h.c1_score_sum, h.c2_score_avg
                FROM ext_board_heat_daily h
                JOIN ext_board_list b ON h.board_id = b.id
                WHERE h.board_id = :board_id AND h.trade_date = :trade_date
                """
            ),
            {"board_id": query.board_id, "trade_date": trade_date},
        ).fetchone()
        if not result:
            raise BoardHeatDataNotFoundError("板块热度数据不存在")

        snap_result = self.db.execute(
            text("SELECT MAX(date) FROM ext_board_daily_snap WHERE date <= :d"),
            {"d": trade_date},
        ).fetchone()
        snap_date = snap_result[0] if snap_result and snap_result[0] else trade_date

        stats = self.db.execute(
            text(
                """
                SELECT
                    COUNT(*) as total,
                    COUNT(CASE WHEN d.rank <= 100 THEN 1 END) as top100_count,
                    COUNT(CASE WHEN d.rank <= 500 THEN 1 END) as hotlist_count,
                    AVG(d.price_change) as avg_price_change,
                    AVG(d.turnover_rate_percent) as avg_turnover
                FROM ext_board_daily_snap s
                LEFT JOIN daily_stock_data d ON s.stock_code = d.stock_code AND d.date = :trade_date
                WHERE s.board_id = :board_id AND s.date = :snap_date
                """
            ),
            {"board_id": query.board_id, "trade_date": trade_date, "snap_date": snap_date},
        ).fetchone()
        top100_count = stats[1] or 0 if stats else 0
        hotlist_count = stats[2] or 0 if stats else 0
        avg_price_change = _float_or_none(stats[3]) if stats else None
        avg_turnover = _float_or_none(stats[4]) if stats else None

        multi_result = self.db.execute(
            text(
                """
                SELECT COUNT(DISTINCT c.stock_code)
                FROM cache_stock_board_signal c
                WHERE c.trade_date = :trade_date
                  AND c.stock_code IN (
                      SELECT stock_code FROM ext_board_daily_snap
                      WHERE board_id = :board_id AND date = :snap_date
                  )
                  AND c.board_count >= 2
                  AND c.signal_level IN ('S', 'A')
                """
            ),
            {"board_id": query.board_id, "trade_date": trade_date, "snap_date": snap_date},
        ).fetchone()
        multi_signal_count = multi_result[0] if multi_result else 0
        signal_strength = min(100, (top100_count / max(1, result[5] or 1)) * 100 * 3) if result[5] else 0

        order_clause = "s.contribution_score DESC NULLS LAST"
        if query.sort_by == "rank":
            order_clause = "d.rank ASC NULLS LAST"
        elif query.sort_by == "score":
            order_clause = "d.total_score DESC NULLS LAST"

        stocks_sql = f"""
        SELECT
            s.stock_code, st.stock_name, s.board_rank, s.weight, s.contribution_score,
            d.total_score, d.rank, d.price_change, d.turnover_rate_percent, d.volatility,
            c.signal_level, c.board_count, c.final_score, d.close_price
        FROM ext_board_daily_snap s
        LEFT JOIN stocks st ON s.stock_code = st.stock_code
        LEFT JOIN daily_stock_data d ON s.stock_code = d.stock_code AND d.date = :trade_date
        LEFT JOIN cache_stock_board_signal c ON s.stock_code = c.stock_code AND c.trade_date = :trade_date
        WHERE s.board_id = :board_id AND s.date = :snap_date
          AND (:min_price IS NULL OR d.close_price >= :min_price)
        ORDER BY {order_clause}
        LIMIT :limit OFFSET :offset
        """
        stock_rows = self.db.execute(
            text(stocks_sql),
            {
                "board_id": query.board_id,
                "trade_date": trade_date,
                "snap_date": snap_date,
                "min_price": query.min_price,
                "limit": query.limit,
                "offset": query.offset,
            },
        ).fetchall()

        response = {
            "board_id": result[0],
            "board_code": result[1],
            "board_name": result[2],
            "board_type": result[3],
            "trade_date": _date_to_string(result[4]),
            "stock_count": result[5] or 0,
            "heat_pct": _float_or_zero(result[6]),
            "heat_raw": _float_or_zero(result[7]),
            "b1_rank_sum": _float_or_zero(result[8]),
            "b2_rank_avg": _float_or_zero(result[9]),
            "c1_score_sum": _float_or_zero(result[10]),
            "c2_score_avg": _float_or_zero(result[11]),
            "top100_count": top100_count,
            "hotlist_count": hotlist_count,
            "multi_signal_count": multi_signal_count,
            "avg_price_change": avg_price_change,
            "avg_turnover": avg_turnover,
            "signal_strength": round(signal_strength, 1),
            "top_stocks": [
                {
                    "stock_code": row[0],
                    "stock_name": row[1] or row[0],
                    "board_rank": row[2],
                    "share_weight": _float_or_zero(row[3]),
                    "contribution_score": _float_or_zero(row[4]),
                    "total_score": _float_or_none(row[5]),
                    "market_rank": row[6],
                    "price_change": _float_or_none(row[7]),
                    "close_price": _float_or_none(row[13]),
                    "turnover_rate": _float_or_none(row[8]),
                    "volatility": _float_or_none(row[9]),
                    "signal_level": row[10] or "NONE",
                    "signal_count": row[11] or 0,
                    "final_score": _float_or_none(row[12]),
                }
                for row in stock_rows
            ],
        }
        self.api_cache.set_api_cache("board_detail", cache_key, response, ttl=BOARD_DETAIL_CACHE_TTL)
        return response

    def get_available_dates(self) -> dict[str, Any]:
        rows = self.db.execute(
            text(
                """
                SELECT DISTINCT trade_date
                FROM ext_board_heat_daily
                ORDER BY trade_date DESC
                LIMIT 30
                """
            )
        ).fetchall()
        return {"dates": [_date_to_string(row[0]) for row in rows]}

    def get_market_treemap(self, query: GetMarketTreemapQuery) -> list[dict[str, Any]]:
        trade_date = query.trade_date
        if not trade_date:
            result = self.db.execute(text("SELECT MAX(trade_date) FROM ext_board_heat_daily")).fetchone()
            if not result or not result[0]:
                return []
            trade_date = str(result[0])

        cache_key = f"{trade_date}_{query.min_size}_{query.max_stock_count}"
        cached = self.api_cache.get_api_cache("market_treemap", cache_key)
        if cached:
            return cached

        rows = self.db.execute(
            text(
                """
                SELECT
                    h.board_id,
                    b.board_name,
                    GREATEST(ABS(COALESCE(h.c1_score_sum, 0)), 0.0001) AS size_val,
                    h.heat_pct,
                    b.board_type,
                    h.stock_count
                FROM ext_board_heat_daily h
                JOIN ext_board_list b ON h.board_id = b.id
                WHERE h.trade_date = :trade_date
                  AND GREATEST(ABS(COALESCE(h.c1_score_sum, 0)), 0.0001) >= :min_size
                  AND (:max_stock_count IS NULL OR h.stock_count <= :max_stock_count)
                ORDER BY size_val DESC
                LIMIT 100
                """
            ),
            {"trade_date": trade_date, "min_size": query.min_size, "max_stock_count": query.max_stock_count},
        ).fetchall()
        items = [
            {
                "board_id": row[0],
                "name": row[1],
                "value": _float_or_zero(row[2]) or 0.0001,
                "heat_pct": _float_or_zero(row[3]),
                "type": row[4],
            }
            for row in rows
        ]
        self.api_cache.set_api_cache("market_treemap", cache_key, items, ttl=BOARD_HEAT_CACHE_TTL)
        return items

    def get_market_signal_bar(self, trade_date: str | None = None) -> dict[str, Any]:
        if not trade_date:
            result = self.db.execute(text("SELECT MAX(trade_date) FROM cache_stock_board_signal")).fetchone()
            if not result or not result[0]:
                raise BoardHeatDataNotFoundError("No Data")
            trade_date = str(result[0])

        cache_key = f"{trade_date}"
        cached = self.api_cache.get_api_cache("market_signal_bar", cache_key)
        if cached:
            return cached

        rows = self.db.execute(
            text(
                """
                SELECT signal_level, COUNT(*)
                FROM cache_stock_board_signal
                WHERE trade_date = :trade_date
                GROUP BY signal_level
                """
            ),
            {"trade_date": trade_date},
        ).fetchall()
        distribution = {"S": 0, "A": 0, "B": 0, "NONE": 0}
        total = 0
        for row in rows:
            level = row[0] or "NONE"
            count = row[1]
            distribution[level] = count
            total += count

        s_pct = distribution["S"] / total if total > 0 else 0
        sentiment = "垃圾时间"
        if s_pct >= 0.05:
            sentiment = "进攻日 (S级>5%)"
        elif s_pct >= 0.02:
            sentiment = "结构性行情"
        elif s_pct <= 0.01:
            sentiment = "冰点退潮 (S级<1%)"

        response = {"trade_date": trade_date, "distribution": distribution, "total": total, "sentiment": sentiment}
        self.api_cache.set_api_cache("market_signal_bar", cache_key, response, ttl=BOARD_HEAT_CACHE_TTL)
        return response

    def get_sector_matrix(self, query: GetSectorMatrixQuery) -> list[dict[str, Any]]:
        trade_date = query.trade_date
        if not trade_date:
            result = self.db.execute(text("SELECT MAX(trade_date) FROM ext_board_heat_daily")).fetchone()
            if not result or not result[0]:
                return []
            trade_date = str(result[0])

        cache_key = f"{trade_date}_{query.limit}"
        cached = self.api_cache.get_api_cache("sector_matrix", cache_key)
        if cached:
            return cached

        rows = self.db.execute(
            text(
                """
                SELECT h.board_id, b.board_name, h.b2_rank_avg, h.c2_score_avg, h.heat_pct, b.board_type
                FROM ext_board_heat_daily h
                JOIN ext_board_list b ON h.board_id = b.id
                WHERE h.trade_date = :trade_date
                ORDER BY h.heat_pct DESC
                LIMIT :limit
                """
            ),
            {"trade_date": trade_date, "limit": query.limit},
        ).fetchall()
        items = [
            {
                "board_id": row[0],
                "name": row[1],
                "x": _float_or_zero(row[2]),
                "y": _float_or_zero(row[3]),
                "size": _float_or_zero(row[4]),
                "type": row[5],
            }
            for row in rows
        ]
        self.api_cache.set_api_cache("sector_matrix", cache_key, items, ttl=BOARD_HEAT_CACHE_TTL)
        return items

    def get_mining_resonance(self, query: GetMiningResonanceQuery) -> list[dict[str, Any]]:
        trade_date = query.trade_date
        if not trade_date:
            result = self.db.execute(text("SELECT MAX(trade_date) FROM cache_stock_board_signal")).fetchone()
            trade_date = str(result[0]) if result and result[0] else datetime.now().strftime("%Y-%m-%d")

        rows = self.db.execute(
            text(
                """
                SELECT stock_code, stock_name, signal_level, final_score, market_rank, max_driver_name
                FROM cache_stock_board_signal
                WHERE trade_date = :trade_date
                  AND signal_level = 'S'
                  AND industry_safe = TRUE
                ORDER BY final_score DESC
                LIMIT :limit
                """
            ),
            {"trade_date": trade_date, "limit": query.limit},
        ).fetchall()
        return [
            {
                "stock_code": row[0],
                "stock_name": row[1],
                "reason": "行业+概念双S共振",
                "signal_level": row[2],
                "final_score": float(row[3]),
                "market_rank": row[4],
                "board_name": row[5],
            }
            for row in rows
        ]

    def get_mining_hidden_gems(self, query: GetMiningHiddenGemsQuery) -> list[dict[str, Any]]:
        trade_date = query.trade_date
        if not trade_date:
            result = self.db.execute(text("SELECT MAX(trade_date) FROM cache_stock_board_signal")).fetchone()
            if result and result[0]:
                trade_date = str(result[0])
            else:
                return []

        rows = self.db.execute(
            text(
                """
                SELECT stock_code, stock_name, signal_level, final_score, market_rank, max_driver_name
                FROM cache_stock_board_signal
                WHERE trade_date = :trade_date
                  AND max_driver_heat_pct >= 0.95
                  AND total_score >= :min_score
                  AND market_rank >= :min_rank
                ORDER BY final_score DESC
                LIMIT :limit
                """
            ),
            {
                "trade_date": trade_date,
                "min_score": query.min_score,
                "min_rank": query.min_rank,
                "limit": query.limit,
            },
        ).fetchall()
        return [
            {
                "stock_code": row[0],
                "stock_name": row[1],
                "reason": f"板块S级补涨 (分>{query.min_score} 排名>{query.min_rank})",
                "signal_level": row[2] or "NONE",
                "final_score": _float_or_zero(row[3]),
                "market_rank": row[4],
                "board_name": row[5] or "",
            }
            for row in rows
        ]

    def get_board_history(self, query: GetBoardHistoryQuery) -> list[dict[str, Any]]:
        if query.end_date:
            try:
                date_end = datetime.strptime(query.end_date, "%Y-%m-%d").date()
            except ValueError:
                date_end = datetime.now().date()
        else:
            date_end = datetime.now().date()
        start_date = date_end - timedelta(days=query.days)

        rows = self.db.execute(
            text(
                """
                SELECT trade_date, heat_pct, heat_raw, c1_score_sum, b2_rank_avg, stock_count
                FROM ext_board_heat_daily
                WHERE board_id = :board_id
                  AND trade_date >= :start_date
                  AND trade_date <= :end_date
                ORDER BY trade_date ASC
                """
            ),
            {"board_id": query.board_id, "start_date": start_date, "end_date": date_end},
        ).fetchall()
        return [
            {
                "trade_date": _date_to_string(row[0]),
                "heat_pct": _float_or_zero(row[1]),
                "heat_raw": _float_or_zero(row[2]),
                "funds": _float_or_zero(row[3]),
                "density": _float_or_zero(row[4]),
                "stock_count": int(row[5]) if row[5] else 0,
            }
            for row in rows
        ]
