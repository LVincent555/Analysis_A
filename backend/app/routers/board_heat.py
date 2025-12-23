"""
板块热度 API
提供外部板块热度数据查询接口
"""
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session
import json
import hashlib
import logging

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.core.caching import cache  # v0.6.0: 接入统一缓存

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/board-heat", tags=["板块热度"])

# ========== 缓存配置 ==========
BOARD_HEAT_CACHE_TTL = 300  # 5分钟
BOARD_DETAIL_CACHE_TTL = 180  # 3分钟
BATCH_SIGNAL_CACHE_TTL = 120  # 2分钟

# ========== Pydantic Models ==========

class BoardHeatItem(BaseModel):
    """板块热度项"""
    board_id: int
    board_code: str
    board_name: str
    board_type: str
    stock_count: int
    heat_pct: float
    b1_rank_sum: Optional[float] = None
    c2_score_avg: Optional[float] = None
    is_blacklisted: bool = False


class BoardHeatRankingResponse(BaseModel):
    """板块热度榜单响应"""
    trade_date: str
    snap_date: str  # 实际使用的关系快照日期
    total_count: int
    items: List[BoardHeatItem]


class BoardStockItem(BaseModel):
    """板块成分股项"""
    stock_code: str
    stock_name: str
    board_rank: Optional[int] = None
    share_weight: Optional[float] = None
    contribution_score: Optional[float] = None
    total_score: Optional[float] = None
    market_rank: Optional[int] = None
    price_change: Optional[float] = None
    close_price: Optional[float] = None
    turnover_rate: Optional[float] = None
    volatility: Optional[float] = None
    signal_level: str = "NONE"
    signal_count: Optional[int] = None
    final_score: Optional[float] = None


class BoardDetailResponse(BaseModel):
    """板块详情响应"""
    board_id: int
    board_code: str
    board_name: str
    board_type: str
    trade_date: str
    stock_count: int
    heat_pct: float
    heat_raw: float
    b1_rank_sum: float
    b2_rank_avg: float
    c1_score_sum: float
    c2_score_avg: float
    top100_count: int
    hotlist_count: int
    multi_signal_count: int
    avg_price_change: Optional[float] = None
    avg_turnover: Optional[float] = None
    signal_strength: float
    top_stocks: List[BoardStockItem]


class StockDNAResponse(BaseModel):
    """个股DNA诊断响应"""
    stock_code: str
    stock_name: str
    trade_date: str
    signal_level: str
    final_score: float
    final_score_pct: float
    fallback_reason: Optional[str]
    dna_json: Dict[str, Any]
    all_related_boards: Optional[List[Dict[str, Any]]] = None


class MarketTreemapItem(BaseModel):
    """市场热力云图项"""
    board_id: int
    name: str
    value: float  # c1_score_sum (资金总量/面积)
    heat_pct: float # 热度 (颜色)
    type: str # industry/concept


class MarketSignalBarResponse(BaseModel):
    """市场信号分布响应"""
    trade_date: str
    distribution: Dict[str, int] # S/A/B/NONE counts
    total: int
    sentiment: str # 市场情绪评价


class SectorMatrixItem(BaseModel):
    """板块风格罗盘项"""
    board_id: int
    name: str
    x: float # b2_density (头部强度)
    y: float # c2_quality (平均分)
    size: float # heat_pct or stock_count
    type: str # industry/concept


class MiningStockItem(BaseModel):
    """挖掘个股项"""
    stock_code: str
    stock_name: str
    reason: str
    signal_level: str
    final_score: float
    market_rank: int
    board_name: str


# ========== Helper Functions ==========

def get_config_value(db: Session, key: str, default: float) -> float:
    """获取配置值"""
    result = db.execute(
        text("SELECT config_value FROM system_configs WHERE config_key = :k"),
        {"k": key}
    ).fetchone()
    return float(result[0]) if result else default


# ========== API Endpoints ==========

@router.get("/ranking", response_model=BoardHeatRankingResponse)
async def get_board_heat_ranking(
    trade_date: Optional[str] = Query(None, description="交易日期 YYYY-MM-DD"),
    board_type: Optional[str] = Query(None, description="板块类型: industry/concept"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    exclude_blacklist: bool = Query(True, description="是否过滤黑名单"),
    max_stock_count: Optional[int] = Query(None, description="最大成分股数量（过滤 stock_count 过大的板块）"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取板块热度榜单
    """
    # 获取最新日期
    if not trade_date:
        result = db.execute(text("SELECT MAX(trade_date) FROM ext_board_heat_daily")).fetchone()
        if not result or not result[0]:
            raise HTTPException(status_code=404, detail="暂无热度数据")
        trade_date = result[0].strftime('%Y-%m-%d') if hasattr(result[0], 'strftime') else str(result[0])
    
    # v0.6.0: 缓存查询
    cache_key = f"{trade_date}_{board_type}_{limit}_{offset}_{exclude_blacklist}_{max_stock_count}"
    cached = cache.get_api_cache("board_ranking", cache_key)
    if cached:
        logger.info(f"✨ 缓存命中: board_ranking/{cache_key}")
        return cached
    
    # 获取快照日期
    snap_result = db.execute(
        text("SELECT MAX(date) FROM ext_board_daily_snap WHERE date <= :d"),
        {"d": trade_date}
    ).fetchone()
    snap_date = snap_result[0].strftime('%Y-%m-%d') if snap_result and snap_result[0] else trade_date
    
    # 构建查询
    where_conditions = ["h.trade_date = :trade_date"]
    params = {"trade_date": trade_date, "limit": limit, "offset": offset}
    
    if board_type:
        where_conditions.append("b.board_type = :board_type")
        params["board_type"] = board_type
        
    if exclude_blacklist:
        # 简单过滤：只要在 board_blacklist 表里且 level='BLACK' 就不显示
        # 或者使用 ext_board_list.is_broad_index (如果是为了过滤宽指)
        # 这里用 V4.0 的 board_blacklist 表关联过滤
        where_conditions.append("""
            NOT EXISTS (
                SELECT 1 FROM board_blacklist bl 
                WHERE b.board_name LIKE '%' || bl.keyword || '%' 
                AND bl.level = 'BLACK' AND bl.is_active = TRUE
            )
        """)

    if max_stock_count is not None:
        where_conditions.append("h.stock_count <= :max_stock_count")
        params["max_stock_count"] = max_stock_count
    
    where_clause = "WHERE " + " AND ".join(where_conditions)
    
    # 获取黑名单标记 (LEFT JOIN 判定)
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
    
    result = db.execute(text(sql), params).fetchall()
    
    # 统计总数
    count_sql = f"""
    SELECT COUNT(*) FROM ext_board_heat_daily h
    JOIN ext_board_list b ON h.board_id = b.id
    {where_clause}
    """
    total = db.execute(text(count_sql), params).scalar()
    
    items = [
        BoardHeatItem(
            board_id=row[0],
            board_code=row[1],
            board_name=row[2],
            board_type=row[3],
            stock_count=row[4],
            heat_pct=float(row[5]) if row[5] else 0,
            b1_rank_sum=float(row[6]) if row[6] else None,
            c2_score_avg=float(row[7]) if row[7] else None,
            is_blacklisted=row[8]
        )
        for row in result
    ]
    
    result_response = BoardHeatRankingResponse(
        trade_date=trade_date,
        snap_date=snap_date,
        total_count=total or 0,
        items=items
    )
    
    # v0.6.0: 写入缓存
    cache.set_api_cache("board_ranking", cache_key, result_response, ttl=BOARD_HEAT_CACHE_TTL)
    return result_response


@router.get("/stock/{stock_code}/dna", response_model=StockDNAResponse)
async def get_stock_board_dna(
    stock_code: str,
    trade_date: Optional[str] = Query(None, description="交易日期"),
    min_price: Optional[float] = Query(None, description="最低股价（低于该价格的股票视为噪音，信号强制为 NONE）"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    【V4.0 新增】获取个股板块DNA诊断信息 (透明化逻辑)
    """
    if not trade_date:
        result = db.execute(text("SELECT MAX(trade_date) FROM cache_stock_board_signal")).fetchone()
        if not result or not result[0]:
             raise HTTPException(status_code=404, detail="暂无信号数据")
        trade_date = str(result[0])
        
    sql = """
    SELECT 
        stock_code, stock_name, signal_level, final_score, 
        final_score_pct, fallback_reason, dna_json
    FROM cache_stock_board_signal
    WHERE stock_code = :stock_code AND trade_date = :trade_date
    """
    result = db.execute(text(sql), {"stock_code": stock_code, "trade_date": trade_date}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="未找到该股信号数据")
        
    dna_data = {}
    if result[6]:
        try:
            dna_data = json.loads(result[6])
        except:
            pass

    # 低价股过滤：只影响信号展示，不改热度计算
    close_price_row = db.execute(
        text("SELECT close_price FROM daily_stock_data WHERE stock_code = :stock_code AND date = :trade_date"),
        {"stock_code": stock_code, "trade_date": trade_date}
    ).fetchone()
    close_price = float(close_price_row[0]) if close_price_row and close_price_row[0] is not None else None

    signal_level = result[2] or 'NONE'
    fallback_reason = result[5]
    if min_price is not None and close_price is not None and close_price < float(min_price):
        signal_level = 'NONE'
        if fallback_reason:
            fallback_reason = f"{fallback_reason} | 低价过滤(<{float(min_price):.2f})"
        else:
            fallback_reason = f"低价过滤(<{float(min_price):.2f})"

    # 生成“完整板块链条”（按热度排序）
    snap_row = db.execute(
        text("SELECT MAX(date) FROM ext_board_daily_snap WHERE date <= :d"),
        {"d": trade_date}
    ).fetchone()
    snap_date = snap_row[0] if snap_row and snap_row[0] else None

    all_related_boards = []
    if snap_date:
        rel_sql = """
        SELECT 
            s.board_id,
            b.board_name,
            b.board_type,
            h.heat_pct,
            s.board_rank
        FROM ext_board_daily_snap s
        JOIN ext_board_list b ON s.board_id = b.id
        LEFT JOIN ext_board_heat_daily h ON h.board_id = s.board_id AND h.trade_date = :trade_date
        WHERE s.stock_code = :stock_code AND s.date = :snap_date
        ORDER BY COALESCE(h.heat_pct, 0) DESC
        LIMIT 200
        """
        rel_rows = db.execute(text(rel_sql), {
            "stock_code": stock_code,
            "trade_date": trade_date,
            "snap_date": snap_date
        }).fetchall()
        all_related_boards = [
            {
                "board_id": r[0],
                "board_name": r[1],
                "board_type": r[2],
                "heat_pct": float(r[3]) if r[3] is not None else None,
                "board_rank": r[4]
            }
            for r in rel_rows
        ]
            
    return StockDNAResponse(
        stock_code=result[0],
        stock_name=result[1],
        trade_date=trade_date,
        signal_level=signal_level,
        final_score=float(result[3]) if result[3] else 0.0,
        final_score_pct=float(result[4]) if result[4] else 0.0,
        fallback_reason=fallback_reason,
        dna_json=dna_data,
        all_related_boards=all_related_boards
    )


@router.post("/stocks/batch")
async def get_stocks_board_signals_batch(
    stock_codes: List[str],
    trade_date: Optional[str] = None,
    min_price: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    批量获取个股板块信号
    """
    if not stock_codes:
        return {"stocks": []}
    
    # 获取最新日期
    if not trade_date:
        result = db.execute(text("SELECT MAX(trade_date) FROM cache_stock_board_signal")).fetchone()
        if not result or not result[0]:
            return {"stocks": [], "trade_date": None}
        trade_date = result[0].strftime('%Y-%m-%d') if hasattr(result[0], 'strftime') else str(result[0])
    
    # v0.6.0: 缓存查询（使用股票代码列表的哈希）
    codes_hash = hashlib.md5('|'.join(sorted(stock_codes)).encode()).hexdigest()[:12]
    cache_key = f"{trade_date}_{codes_hash}_{min_price}"
    cached = cache.get_api_cache("batch_signal", cache_key)
    if cached:
        logger.info(f"✨ 缓存命中: batch_signal/{cache_key}")
        return cached
    
    # 批量查询
    placeholders = ', '.join([f':code_{i}' for i in range(len(stock_codes))])
    params = {"trade_date": trade_date}
    for i, code in enumerate(stock_codes):
        params[f"code_{i}"] = code
    
    sql = f"""
    SELECT 
        c.stock_code, c.signal_level, c.max_driver_name, c.max_driver_board_id,
        c.max_driver_type, c.max_driver_heat_pct, c.industry_safe, c.final_score,
        d.close_price
    FROM cache_stock_board_signal c
    LEFT JOIN daily_stock_data d ON c.stock_code = d.stock_code AND d.date = :trade_date
    WHERE c.trade_date = :trade_date AND c.stock_code IN ({placeholders})
    """
    
    result = db.execute(text(sql), params).fetchall()
    
    stocks = [
        {
            "stock_code": row[0],
            "board_signal_level": ("NONE" if (min_price is not None and row[8] is not None and float(row[8]) < float(min_price)) else (row[1] or "NONE")),
            "board_signal_label": row[2] or "",
            "max_concept_board_id": row[3],
            "max_concept_board_type": row[4],
            "max_concept_heat_pct": float(row[5]) if row[5] else None,
            "industry_safe": row[6] or False,
            "final_score": float(row[7]) if row[7] else None
        }
        for row in result
    ]
    
    # v0.6.0: 写入缓存
    response = {"stocks": stocks, "trade_date": trade_date}
    cache.set_api_cache("batch_signal", cache_key, response, ttl=BATCH_SIGNAL_CACHE_TTL)
    return response


@router.get("/board/{board_id}", response_model=BoardDetailResponse)
async def get_board_detail(
    board_id: int,
    trade_date: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=5000), # V4.0 支持大分页
    offset: int = Query(0, ge=0),
    sort_by: str = Query('contribution', description="contribution/rank/score"),
    min_price: Optional[float] = Query(None, description="最低股价（仅过滤成分股展示，不影响板块热度计算）"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取板块详情（包含成分股，支持分页和高级排序）
    """
    # 获取最新日期
    if not trade_date:
        result = db.execute(text("SELECT MAX(trade_date) FROM ext_board_heat_daily")).fetchone()
        if not result or not result[0]:
            raise HTTPException(status_code=404, detail="暂无热度数据")
        trade_date = result[0].strftime('%Y-%m-%d') if hasattr(result[0], 'strftime') else str(result[0])
    
    # v0.6.0: 缓存查询
    cache_key = f"{board_id}_{trade_date}_{limit}_{offset}_{sort_by}_{min_price}"
    cached = cache.get_api_cache("board_detail", cache_key)
    if cached:
        logger.info(f"✨ 缓存命中: board_detail/{cache_key}")
        return cached
    
    # 获取板块热度信息
    sql = """
    SELECT 
        h.board_id, b.board_code, b.board_name, b.board_type,
        h.trade_date, h.stock_count, h.heat_pct, h.heat_raw,
        h.b1_rank_sum, h.b2_rank_avg, h.c1_score_sum, h.c2_score_avg
    FROM ext_board_heat_daily h
    JOIN ext_board_list b ON h.board_id = b.id
    WHERE h.board_id = :board_id AND h.trade_date = :trade_date
    """
    
    result = db.execute(text(sql), {"board_id": board_id, "trade_date": trade_date}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="板块热度数据不存在")
    
    # 获取快照日期
    snap_result = db.execute(
        text("SELECT MAX(date) FROM ext_board_daily_snap WHERE date <= :d"),
        {"d": trade_date}
    ).fetchone()
    snap_date = snap_result[0] if snap_result and snap_result[0] else trade_date
    
    # 获取成分股统计
    stats_sql = """
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
    stats = db.execute(text(stats_sql), {
        "board_id": board_id, 
        "trade_date": trade_date,
        "snap_date": snap_date
    }).fetchone()
    
    top100_count = stats[1] or 0 if stats else 0
    hotlist_count = stats[2] or 0 if stats else 0
    avg_price_change = float(stats[3]) if stats and stats[3] else None
    avg_turnover = float(stats[4]) if stats and stats[4] else None
    
    # 计算多信号股票数
    multi_signal_sql = """
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
    multi_result = db.execute(text(multi_signal_sql), {
        "board_id": board_id, 
        "trade_date": trade_date,
        "snap_date": snap_date
    }).fetchone()
    multi_signal_count = multi_result[0] if multi_result else 0
    
    # 计算信号强度
    signal_strength = min(100, (top100_count / max(1, result[5] or 1)) * 100 * 3) if result[5] else 0
    
    # 获取成分股（V4.0: 支持 contribution 排序）
    order_clause = "s.contribution_score DESC NULLS LAST"
    if sort_by == 'rank':
        order_clause = "d.rank ASC NULLS LAST"
    elif sort_by == 'score':
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
    
    stocks_result = db.execute(text(stocks_sql), {
        "board_id": board_id, 
        "trade_date": trade_date,
        "snap_date": snap_date,
        "min_price": min_price,
        "limit": limit,
        "offset": offset
    }).fetchall()
    
    top_stocks = [
        {
            "stock_code": row[0],
            "stock_name": row[1] or row[0],
            "board_rank": row[2],
            "share_weight": float(row[3]) if row[3] else 0.0, # V4.0
            "contribution_score": float(row[4]) if row[4] else 0.0, # V4.0
            "total_score": float(row[5]) if row[5] else None,
            "market_rank": row[6],
            "price_change": float(row[7]) if row[7] else None,
            "close_price": float(row[13]) if row[13] is not None else None,
            "turnover_rate": float(row[8]) if row[8] else None,
            "volatility": float(row[9]) if row[9] else None,
            "signal_level": row[10] or "NONE",
            "signal_count": row[11] or 0,
            "final_score": float(row[12]) if row[12] else None
        }
        for row in stocks_result
    ]
    
    # v0.6.0: 构建响应并缓存
    response = BoardDetailResponse(
        board_id=result[0],
        board_code=result[1],
        board_name=result[2],
        board_type=result[3],
        trade_date=result[4].strftime('%Y-%m-%d') if hasattr(result[4], 'strftime') else str(result[4]),
        stock_count=result[5] or 0,
        heat_pct=float(result[6]) if result[6] else 0,
        heat_raw=float(result[7]) if result[7] else 0,
        b1_rank_sum=float(result[8]) if result[8] else 0,
        b2_rank_avg=float(result[9]) if result[9] else 0,
        c1_score_sum=float(result[10]) if result[10] else 0,
        c2_score_avg=float(result[11]) if result[11] else 0,
        top100_count=top100_count,
        hotlist_count=hotlist_count,
        multi_signal_count=multi_signal_count,
        avg_price_change=avg_price_change,
        avg_turnover=avg_turnover,
        signal_strength=round(signal_strength, 1),
        top_stocks=top_stocks
    )
    cache.set_api_cache("board_detail", cache_key, response, ttl=BOARD_DETAIL_CACHE_TTL)
    return response


@router.get("/dates")
async def get_available_dates(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取可用的热度数据日期
    """
    sql = """
    SELECT DISTINCT trade_date 
    FROM ext_board_heat_daily 
    ORDER BY trade_date DESC 
    LIMIT 30
    """
    result = db.execute(text(sql)).fetchall()
    
    return {
        "dates": [row[0].strftime('%Y-%m-%d') if hasattr(row[0], 'strftime') else str(row[0]) for row in result]
    }


# ========== V4.0 Specialized Views ==========

@router.get("/market/treemap", response_model=List[MarketTreemapItem])
async def get_market_treemap(
    trade_date: Optional[str] = Query(None),
    min_size: float = Query(0, description="过滤小板块"),
    max_stock_count: Optional[int] = Query(None, description="最大成分股数量（过滤 stock_count 过大的板块）"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    【V4.0】全市场热力云图数据
    Size = c1_score_sum (资金总量)
    Color = heat_pct
    """
    if not trade_date:
        result = db.execute(text("SELECT MAX(trade_date) FROM ext_board_heat_daily")).fetchone()
        if not result or not result[0]:
            return []
        trade_date = str(result[0])
    
    # v0.6.0: 缓存查询
    cache_key = f"{trade_date}_{min_size}_{max_stock_count}"
    cached = cache.get_api_cache("market_treemap", cache_key)
    if cached:
        logger.info(f"✨ 缓存命中: market_treemap/{cache_key}")
        return cached
        
    sql = """
    SELECT 
        h.board_id, 
        b.board_name, 
        -- 保障 size > 0，使用绝对值避免负数导致前端空图
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
    
    result = db.execute(text(sql), {"trade_date": trade_date, "min_size": min_size, "max_stock_count": max_stock_count}).fetchall()
    excluded_in_top = 0
    if max_stock_count is not None:
        try:
            excluded_in_top = sum(1 for r in result if r[5] is not None and int(r[5]) > int(max_stock_count))
        except Exception:
            excluded_in_top = 0
    print(f"[treemap] trade_date={trade_date} min_size={min_size} max_stock_count={max_stock_count} rows={len(result)} excluded_in_top={excluded_in_top}")
    
    items = [
        MarketTreemapItem(
            board_id=row[0],
            name=row[1],
            value=float(row[2]) if row[2] else 0.0001,
            heat_pct=float(row[3]) if row[3] else 0,
            type=row[4]
        )
        for row in result
    ]
    
    # v0.6.0: 写入缓存
    cache.set_api_cache("market_treemap", cache_key, items, ttl=BOARD_HEAT_CACHE_TTL)
    return items


@router.get("/market/signal-bar", response_model=MarketSignalBarResponse)
async def get_market_signal_bar(
    trade_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    【V4.0】市场信号体检仪
    """
    if not trade_date:
        result = db.execute(text("SELECT MAX(trade_date) FROM cache_stock_board_signal")).fetchone()
        if not result or not result[0]:
            raise HTTPException(status_code=404, detail="No Data")
        trade_date = str(result[0])
    
    # v0.6.0: 缓存查询
    cache_key = f"{trade_date}"
    cached = cache.get_api_cache("market_signal_bar", cache_key)
    if cached:
        logger.info(f"✨ 缓存命中: market_signal_bar/{cache_key}")
        return cached
        
    sql = """
    SELECT signal_level, COUNT(*) 
    FROM cache_stock_board_signal 
    WHERE trade_date = :trade_date 
    GROUP BY signal_level
    """
    
    rows = db.execute(text(sql), {"trade_date": trade_date}).fetchall()
    
    dist = {"S": 0, "A": 0, "B": 0, "NONE": 0}
    total = 0
    for row in rows:
        level = row[0] or "NONE"
        count = row[1]
        dist[level] = count
        total += count
        
    s_pct = dist["S"] / total if total > 0 else 0
    
    sentiment = "垃圾时间"
    if s_pct >= 0.05:
        sentiment = "进攻日 (S级>5%)"
    elif s_pct >= 0.02:
        sentiment = "结构性行情"
    elif s_pct <= 0.01:
        sentiment = "冰点退潮 (S级<1%)"
        
    response = MarketSignalBarResponse(
        trade_date=trade_date,
        distribution=dist,
        total=total,
        sentiment=sentiment
    )
    
    # v0.6.0: 写入缓存
    cache.set_api_cache("market_signal_bar", cache_key, response, ttl=BOARD_HEAT_CACHE_TTL)
    return response


@router.get("/market/sector-matrix", response_model=List[SectorMatrixItem])
async def get_sector_matrix(
    trade_date: Optional[str] = Query(None),
    limit: int = Query(100),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    【V4.0】板块风格罗盘数据
    X = b2_rank_avg (密度)
    Y = c2_score_avg (质量)
    """
    if not trade_date:
        result = db.execute(text("SELECT MAX(trade_date) FROM ext_board_heat_daily")).fetchone()
        if not result or not result[0]:
            return []
        trade_date = str(result[0])
    
    # v0.6.0: 缓存查询
    cache_key = f"{trade_date}_{limit}"
    cached = cache.get_api_cache("sector_matrix", cache_key)
    if cached:
        logger.info(f"✨ 缓存命中: sector_matrix/{cache_key}")
        return cached
        
    sql = """
    SELECT 
        h.board_id, b.board_name, h.b2_rank_avg, h.c2_score_avg, h.heat_pct, b.board_type
    FROM ext_board_heat_daily h
    JOIN ext_board_list b ON h.board_id = b.id
    WHERE h.trade_date = :trade_date
    ORDER BY h.heat_pct DESC
    LIMIT :limit
    """
    
    result = db.execute(text(sql), {"trade_date": trade_date, "limit": limit}).fetchall()
    
    print(f"[sector-matrix] trade_date={trade_date} rows={len(result)}")
    
    items = [
        SectorMatrixItem(
            board_id=row[0],
            name=row[1],
            x=float(row[2]) if row[2] else 0,
            y=float(row[3]) if row[3] else 0,
            size=float(row[4]) if row[4] else 0,
            type=row[5]
        )
        for row in result
    ]
    
    # v0.6.0: 写入缓存
    cache.set_api_cache("sector_matrix", cache_key, items, ttl=BOARD_HEAT_CACHE_TTL)
    return items


@router.get("/mining/resonance", response_model=List[MiningStockItem])
async def get_mining_resonance(
    trade_date: Optional[str] = Query(None),
    limit: int = Query(50),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    【V4.0】双S级共振猎手
    逻辑: 行业 S 级 AND 概念 S 级
    """
    if not trade_date:
        trade_date = datetime.now().strftime('%Y-%m-%d') # Placeholder
        res = db.execute(text("SELECT MAX(trade_date) FROM cache_stock_board_signal")).fetchone()
        if res and res[0]: trade_date = str(res[0])
        
    sql = """
    SELECT 
        stock_code, stock_name, signal_level, final_score, market_rank, 
        max_driver_name
    FROM cache_stock_board_signal
    WHERE trade_date = :trade_date
      AND signal_level = 'S'
      AND industry_safe = TRUE -- 行业安全(S/A)
    ORDER BY final_score DESC
    LIMIT :limit
    """
    
    result = db.execute(text(sql), {"trade_date": trade_date, "limit": limit}).fetchall()
    
    print(f"[mining-resonance] trade_date={trade_date} rows={len(result)}")
    
    return [
        MiningStockItem(
            stock_code=row[0],
            stock_name=row[1],
            reason="行业+概念双S共振",
            signal_level=row[2],
            final_score=float(row[3]),
            market_rank=row[4],
            board_name=row[5]
        )
        for row in result
    ]


@router.get("/mining/hidden-gems", response_model=List[MiningStockItem])
async def get_mining_hidden_gems(
    trade_date: Optional[str] = Query(None),
    min_score: float = Query(85),
    min_rank: int = Query(500),
    limit: int = Query(50),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    【V4.0】隐形冠军挖掘机 (补涨)
    逻辑: 板块S级(max_driver) + 个股分高 + 排名靠后
    """
    if not trade_date:
        res = db.execute(text("SELECT MAX(trade_date) FROM cache_stock_board_signal")).fetchone()
        if res and res[0]: trade_date = str(res[0])
        else: return []
        
    sql = """
    SELECT 
        stock_code, stock_name, signal_level, final_score, market_rank, 
        max_driver_name
    FROM cache_stock_board_signal
    WHERE trade_date = :trade_date
      AND max_driver_heat_pct >= 0.95 -- 板块很热
      AND total_score >= :min_score   -- 个股质地好
      AND market_rank >= :min_rank    -- 排名靠后(未启动)
    ORDER BY final_score DESC
    LIMIT :limit
    """
    
    result = db.execute(text(sql), {
        "trade_date": trade_date, 
        "min_score": min_score, 
        "min_rank": min_rank,
        "limit": limit
    }).fetchall()
    
    print(f"[mining-hidden] trade_date={trade_date} rows={len(result)}")
    
    return [
        MiningStockItem(
            stock_code=row[0],
            stock_name=row[1],
            reason=f"板块S级补涨 (分>{min_score} 排名>{min_rank})",
            signal_level=row[2] or 'NONE',
            final_score=float(row[3]) if row[3] else 0,
            market_rank=row[4],
            board_name=row[5] or ''
        )
        for row in result
    ]


@router.get("/board/{board_id}/history")
async def get_board_history(
    board_id: int,
    days: int = Query(30, ge=7, le=365),
    end_date: Optional[str] = Query(None, description="截止日期 YYYY-MM-DD"),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    获取板块历史走势
    """
    # 计算起始日期
    if end_date:
        try:
            date_end = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            date_end = datetime.now().date()
    else:
        date_end = datetime.now().date()
        
    start_date = date_end - timedelta(days=days)
    
    sql = """
    SELECT 
        trade_date, 
        heat_pct, 
        heat_raw,
        c1_score_sum, 
        b2_rank_avg,
        stock_count
    FROM ext_board_heat_daily
    WHERE board_id = :board_id 
      AND trade_date >= :start_date
      AND trade_date <= :end_date
    ORDER BY trade_date ASC
    """
    
    rows = db.execute(text(sql), {
        "board_id": board_id, 
        "start_date": start_date,
        "end_date": date_end
    }).fetchall()
    
    return [
        {
            "trade_date": row[0].strftime('%Y-%m-%d') if hasattr(row[0], 'strftime') else str(row[0]),
            "heat_pct": float(row[1]) if row[1] else 0,
            "heat_raw": float(row[2]) if row[2] else 0,
            "funds": float(row[3]) if row[3] else 0,
            "density": float(row[4]) if row[4] else 0,
            "stock_count": int(row[5]) if row[5] else 0
        }
        for row in rows
    ]
