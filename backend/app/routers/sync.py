"""
数据同步路由模块
提供离线数据同步API
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..db_models import User, Stock, DailyStockData
from ..auth.dependencies import get_current_user
from ..services.numpy_cache_middleware import numpy_cache

router = APIRouter(prefix="/api/sync", tags=["数据同步"])


@router.get("/status")
def get_sync_status(  # ✅ 同步
    user: User = Depends(get_current_user)
):
    """
    获取同步状态信息
    
    返回服务端数据的最新状态，供客户端判断是否需要同步
    """
    dates = numpy_cache.get_available_dates()
    
    return {
        "latest_date": dates[0] if dates else None,
        "available_dates": len(dates),
        "total_stocks": len(numpy_cache.stocks),
        "server_time": datetime.utcnow().isoformat(),
        "user_offline_days": user.offline_days,
        "user_offline_enabled": user.offline_enabled
    }


@router.get("/incremental")
def incremental_sync(  # ✅ 同步
    since: str = Query(..., description="上次同步时间 ISO格式"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    增量同步
    
    返回指定时间之后更新的数据
    用于客户端定期同步新数据
    """
    if not user.offline_enabled:
        raise HTTPException(403, "离线功能未启用")
    
    try:
        since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(400, "无效的时间格式")
    
    # 限制同步范围（用户配置的离线天数）
    max_days = user.offline_days
    cutoff = datetime.utcnow() - timedelta(days=max_days)
    since_dt = max(since_dt, cutoff)
    
    # 获取可用日期
    all_dates = numpy_cache.get_available_dates()
    all_dates_str = [d.strftime("%Y-%m-%d") for d in all_dates]
    
    # 筛选需要同步的日期
    sync_dates = [d for d in all_dates_str if datetime.strptime(d, "%Y-%m-%d") > since_dt]
    
    # 限制单次同步量
    sync_dates = sync_dates[:7]  # 最多7天
    
    # 收集数据
    stocks_data = []
    daily_data = []
    
    for date_str in sync_dates:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        date_data = numpy_cache.get_all_by_date(date_obj)  # 返回Dict列表
        for item in date_data[:1000]:  # 每天最多1000条
            daily_data.append({
                "stock_code": item['stock_code'],
                "date": date_str,
                "rank": item['rank'],
                "total_score": item.get('total_score'),
                "price_change": item.get('price_change'),
                "turnover_rate_percent": item.get('turnover_rate'),
                "volume_days": item.get('volume_days'),
                "volatility": item.get('volatility'),
            })
    
    # 获取股票基本信息
    stock_codes = set(d["stock_code"] for d in daily_data)
    for code in stock_codes:
        stock = numpy_cache.stocks.get(code)
        if stock:
            stocks_data.append({
                "stock_code": stock.stock_code,
                "stock_name": stock.stock_name,
                "industry": stock.industry
            })
    
    return {
        "stocks": stocks_data,
        "daily_data": daily_data,
        "sync_dates": sync_dates,
        "sync_time": datetime.utcnow().isoformat(),
        "has_more": len(sync_dates) == 7  # 如果正好7天，可能还有更多
    }


@router.get("/daily/{date}")
def sync_daily(  # ✅ 同步
    date: str,
    limit: int = Query(default=1000, le=5000),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user)
):
    """
    同步指定日期的数据
    
    支持分页，用于首次全量同步或补充同步
    """
    if not user.offline_enabled:
        raise HTTPException(403, "离线功能未启用")
    
    # 验证日期格式
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "无效的日期格式，应为 YYYY-MM-DD")
    
    # 检查日期是否在允许范围内
    max_days = user.offline_days
    cutoff = (datetime.utcnow() - timedelta(days=max_days)).strftime("%Y-%m-%d")
    if date < cutoff:
        raise HTTPException(400, f"日期超出离线范围，最早可同步: {cutoff}")
    
    # 获取数据
    date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    date_data = numpy_cache.get_all_by_date(date_obj)  # 返回Dict列表
    
    if not date_data:
        return {
            "date": date,
            "count": 0,
            "data": [],
            "has_more": False
        }
    
    # 分页
    total = len(date_data)
    page_data = date_data[offset:offset + limit]
    
    result_data = []
    for item in page_data:
        result_data.append({
            "stock_code": item['stock_code'],
            "date": date,
            "rank": item['rank'],
            "total_score": item.get('total_score'),
            "price_change": item.get('price_change'),
            "turnover_rate_percent": item.get('turnover_rate'),
            "volume_days": item.get('volume_days'),
            "volatility": item.get('volatility'),
            "volume": item.get('volume'),
        })
    
    return {
        "date": date,
        "total": total,
        "offset": offset,
        "limit": limit,
        "count": len(result_data),
        "data": result_data,
        "has_more": offset + limit < total
    }


@router.get("/stocks")
def sync_stocks(  # ✅ 同步
    user: User = Depends(get_current_user)
):
    """
    同步股票基本信息
    
    返回所有股票的代码、名称、行业
    """
    if not user.offline_enabled:
        raise HTTPException(403, "离线功能未启用")
    
    stocks_data = []
    for code, stock in numpy_cache.stocks.items():
        stocks_data.append({
            "stock_code": stock.stock_code,
            "stock_name": stock.stock_name,
            "industry": stock.industry
        })
    
    return {
        "count": len(stocks_data),
        "stocks": stocks_data,
        "sync_time": datetime.utcnow().isoformat()
    }


@router.get("/dates")
def sync_dates(  # ✅ 同步
    user: User = Depends(get_current_user)
):
    """
    获取可同步的日期列表
    
    根据用户的离线天数配置返回可用日期
    """
    all_dates = [d.strftime("%Y-%m-%d") for d in numpy_cache.get_available_dates()]
    
    # 限制到用户配置的天数
    max_days = user.offline_days
    cutoff = (datetime.utcnow() - timedelta(days=max_days)).strftime("%Y-%m-%d")
    
    available_dates = [d for d in all_dates if d >= cutoff]
    
    return {
        "dates": available_dates,
        "total": len(available_dates),
        "max_days": max_days,
        "cutoff": cutoff
    }
