"""
板块数据API路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List
from ..services.sector_service_db import sector_service_db
from ..models import SectorRankingResult, SectorDetail

router = APIRouter(prefix="/api", tags=["sector"])

# 使用数据库服务
sector_service = sector_service_db


@router.get("/sectors/dates", response_model=List[str])
async def get_available_dates():
    """
    获取所有可用的数据日期
    
    Returns:
        日期列表（降序）
    """
    try:
        return sector_service.get_available_dates()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectors/ranking", response_model=SectorRankingResult)
@router.get("/sector-ranking", response_model=SectorRankingResult)  # 兼容连字符格式
async def get_sector_ranking(
    date: str = Query(default=None, description="指定日期 (YYYYMMDD格式)"),
    limit: int = Query(default=100, ge=10, le=500, description="返回的板块数量")
):
    """
    获取板块排名
    
    Args:
        date: 指定日期 (YYYYMMDD格式)，不传则使用最新日期
        limit: 返回的板块数量，默认100
    
    Returns:
        板块排名结果
    """
    try:
        return sector_service.get_sector_ranking(
            target_date=date,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectors/raw-data")
async def get_sector_raw_data(
    date: str = Query(default=None, description="指定日期 (YYYYMMDD格式)"),
    limit: int = Query(default=600, ge=10, le=1000, description="返回数量")
):
    """
    获取当日板块原始数据（Excel 原始字段）
    """
    try:
        from datetime import datetime
        from ..services.memory_cache import memory_cache
        from ..database import SessionLocal
        from ..db_models import SectorDailyData, Sector
        
        # 获取日期
        if date:
            target_date = datetime.strptime(date, '%Y%m%d').date()
        else:
            target_date = memory_cache.get_sector_latest_date()
        
        if not target_date:
            raise HTTPException(404, "没有可用数据")
        
        db = SessionLocal()
        try:
            # 查询原始数据
            query = db.query(SectorDailyData, Sector.sector_name).join(
                Sector, SectorDailyData.sector_id == Sector.id
            ).filter(
                SectorDailyData.date == target_date
            ).order_by(SectorDailyData.rank).limit(limit)
            
            results = query.all()
            
            data = []
            for row, sector_name in results:
                item = {
                    'name': sector_name,
                    'rank': row.rank,
                    'total_score': float(row.total_score) if row.total_score else None,
                    'price_change': float(row.price_change) if row.price_change else None,
                    'open_price': float(row.open_price) if row.open_price else None,
                    'high_price': float(row.high_price) if row.high_price else None,
                    'low_price': float(row.low_price) if row.low_price else None,
                    'close_price': float(row.close_price) if row.close_price else None,
                    'turnover_rate': float(row.turnover_rate_percent) if row.turnover_rate_percent else None,
                    'volume_days': float(row.volume_days) if row.volume_days else None,
                    'avg_volume_ratio_50': float(row.avg_volume_ratio_50) if row.avg_volume_ratio_50 else None,
                    'volume': float(row.volume) if row.volume else None,
                    'volatility': float(row.volatility) if row.volatility else None,
                    'beta': float(row.beta) if row.beta else None,
                    'correlation': float(row.correlation) if row.correlation else None,
                    'long_term': row.long_term,
                    'short_term': row.short_term,
                    'overbought': row.overbought,
                    'oversold': row.oversold,
                    'macd_signal': row.macd_signal,
                    'rsi': float(row.rsi) if row.rsi else None,
                    'dif': float(row.dif) if row.dif else None,
                    'dem': float(row.dem) if row.dem else None,
                    'adx': float(row.adx) if row.adx else None,
                    'slowk': float(row.slowk) if row.slowk else None,
                }
                data.append(item)
            
            return {
                'date': target_date.strftime('%Y%m%d'),
                'total_count': len(data),
                'data': data
            }
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectors/search/{keyword}", response_model=List[str])
async def search_sectors(keyword: str):
    """
    搜索板块
    
    Args:
        keyword: 搜索关键词
    
    Returns:
        匹配的板块名称列表
    """
    try:
        return sector_service.search_sectors(keyword)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectors/trend")
async def get_sector_trend(
    days: int = Query(default=7, ge=3, le=60, description="显示天数"),
    limit: int = Query(default=10, ge=5, le=30, description="前N个板块"),
    date: str = Query(default=None, description="结束日期 (YYYYMMDD格式)")
):
    """
    获取板块趋势变化数据（多日期对比）
    
    Args:
        days: 显示天数，默认7天
        limit: 前N个板块，默认10个
        date: 结束日期，不传则使用最新日期
    
    Returns:
        {
            "dates": ["20251103", "20251104", ...],
            "sectors": [
                {
                    "name": "专用设备",
                    "ranks": [12, 8, 10, ...],
                    "scores": [95.2, 96.1, ...]
                }
            ]
        }
    """
    try:
        from datetime import datetime
        from collections import defaultdict
        from ..services.memory_cache import memory_cache
        
        # 1. 从内存缓存获取日期范围
        if date:
            end_date = datetime.strptime(date, '%Y%m%d').date()
        else:
            end_date = memory_cache.get_sector_latest_date()
        
        if not end_date:
            raise HTTPException(404, "没有可用数据")
        
        # 获取最近N天的日期
        all_dates = memory_cache.get_sector_dates_range(days * 2)
        dates = [d for d in all_dates if d <= end_date][:days]
        
        if not dates:
            raise HTTPException(404, "没有足够的历史数据")
        
        dates.reverse()  # 按时间正序
        
        # 2. 从内存缓存获取最新日期的前N个板块
        latest_date = dates[-1]
        top_sectors_data = memory_cache.get_top_n_sectors(latest_date, limit)
        
        if not top_sectors_data:
            raise HTTPException(404, "没有板块数据")
        
        # 获取板块ID列表
        sector_ids = [s.sector_id for s in top_sectors_data]
        
        # 3. 从内存缓存获取这些板块在所有日期的数据
        sector_dict = defaultdict(lambda: {'ranks': [], 'scores': []})
        
        for sector_id in sector_ids:
            history_data = memory_cache.get_sector_history(sector_id, dates)
            
            if history_data:
                # 从内存缓存获取板块基础信息
                sector_info = memory_cache.get_sector_info(sector_id)
                sector_name = sector_info.sector_name if sector_info else str(sector_id)
                sector_dict[sector_id]['name'] = sector_name
                
                # 初始化数组
                sector_dict[sector_id]['ranks'] = [None] * len(dates)
                sector_dict[sector_id]['scores'] = [None] * len(dates)
                
                # 填充数据
                for data in history_data:
                    if data.date in dates:
                        date_index = dates.index(data.date)
                        sector_dict[sector_id]['ranks'][date_index] = data.rank
                        sector_dict[sector_id]['scores'][date_index] = float(data.total_score) if data.total_score else None
        
        # 4. 转换为列表（按原始排序）
        sectors = []
        for sector_id in sector_ids:
            if sector_id in sector_dict:
                sectors.append(sector_dict[sector_id])
        
        return {
            "dates": [d.strftime('%Y%m%d') for d in dates],
            "sectors": sectors
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectors/rank-changes")
async def get_sector_rank_changes(
    date: str = Query(default=None, description="对比日期 (YYYYMMDD格式)"),
    compare_days: int = Query(default=1, ge=1, le=7, description="对比天数（1=昨天）")
):
    """
    获取板块排名变化统计
    
    Args:
        date: 对比日期，不传则使用最新日期
        compare_days: 对比天数，1=昨天，7=上周
    
    Returns:
        {
            "date": "20251107",
            "compare_date": "20251106",
            "statistics": {
                "new_entries": 5,
                "rank_up": 23,
                "rank_down": 18,
                "rank_same": 4
            },
            "sectors": [...]
        }
    """
    try:
        from datetime import datetime
        from ..services.memory_cache import memory_cache
        
        # 1. 从内存缓存获取当前日期
        if date:
            current_date = datetime.strptime(date, '%Y%m%d').date()
        else:
            current_date = memory_cache.get_sector_latest_date()
        
        if not current_date:
            raise HTTPException(404, "没有可用数据")
        
        # 2. 获取对比日期（从所有可用日期中找到比当前日期早的日期）
        all_dates = memory_cache.sector_dates  # 所有日期（降序排列）
        available_dates = [d for d in all_dates if d < current_date]
        
        if not available_dates:
            raise HTTPException(404, "没有足够的历史数据")
        
        # 找到第 compare_days 个早于当前日期的日期
        compare_date = available_dates[min(compare_days - 1, len(available_dates) - 1)]
        
        # 3. 从内存缓存获取当前日期的数据
        current_data_list = memory_cache.get_sector_daily_data_by_date(current_date)
        
        # 4. 从内存缓存获取对比日期的数据
        compare_data_list = memory_cache.get_sector_daily_data_by_date(compare_date)
        
        # 构建对比字典 {sector_id: rank}
        compare_dict = {data.sector_id: data.rank for data in compare_data_list}
        
        # 5. 计算变化
        statistics = {
            'new_entries': 0,
            'rank_up': 0,
            'rank_down': 0,
            'rank_same': 0
        }
        
        sectors = []
        for data in current_data_list:
            previous_rank = compare_dict.get(data.sector_id)
            
            if previous_rank is None:
                rank_change = None
                is_new = True
                statistics['new_entries'] += 1
            else:
                rank_change = previous_rank - data.rank  # 正数=上升
                is_new = False
                if rank_change > 0:
                    statistics['rank_up'] += 1
                elif rank_change < 0:
                    statistics['rank_down'] += 1
                else:
                    statistics['rank_same'] += 1
            
            # 从内存缓存获取板块名称
            sector_info = memory_cache.get_sector_info(data.sector_id)
            sector_name = sector_info.sector_name if sector_info else str(data.sector_id)
            
            sectors.append({
                'name': sector_name,
                'current_rank': data.rank,
                'previous_rank': previous_rank,
                'rank_change': rank_change,
                'is_new': is_new,
                'total_score': float(data.total_score) if data.total_score else None,
                'price_change': float(data.price_change) if data.price_change else None,
                'volume_days': float(data.volume_days) if data.volume_days else None
            })
        
        # 按当前排名排序
        sectors.sort(key=lambda x: x['current_rank'])
        
        return {
            'date': current_date.strftime('%Y%m%d'),
            'compare_date': compare_date.strftime('%Y%m%d'),
            'statistics': statistics,
            'sectors': sectors
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ⚠️ 重要：通用路由 {sector_name} 必须放在最后，否则会拦截其他路由
@router.get("/sectors/{sector_name}", response_model=SectorDetail)
@router.get("/sector/{sector_name}", response_model=SectorDetail)  # 兼容单数形式
async def get_sector_detail(
    sector_name: str,
    days: int = Query(default=30, ge=7, le=365, description="返回的历史天数"),
    date: str = Query(default=None, description="指定日期 (YYYYMMDD格式)")
):
    """
    获取板块详细信息和历史数据
    
    Args:
        sector_name: 板块名称
        days: 返回的历史天数，默认30天
        date: 指定日期 (YYYYMMDD格式)，不传则使用最新日期
    
    Returns:
        板块详细信息
    """
    try:
        result = sector_service.get_sector_detail(
            sector_name=sector_name,
            days=days,
            target_date=date
        )
        
        if not result:
            raise HTTPException(status_code=404, detail=f"板块不存在: {sector_name}")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
