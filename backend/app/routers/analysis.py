"""
分析相关API路由
"""
from fastapi import APIRouter, HTTPException
from ..services.analysis_service_db import analysis_service_db
from ..services.hot_spots_cache import HotSpotsCache
from ..services.numpy_cache_middleware import numpy_cache  # ✅ 迁移到新架构
from ..models import AnalysisResult, AvailableDates

router = APIRouter(prefix="/api", tags=["analysis"])

# 使用数据库服务
analysis_service = analysis_service_db


@router.get("/dates", response_model=AvailableDates)
def get_available_dates():  # ✅ 改为同步，避免阻塞事件循环
    """获取可用的日期列表"""
    try:
        dates = analysis_service.get_available_dates()
        return AvailableDates(
            dates=dates,
            latest_date=dates[0] if dates else ""
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/analyze/{period}", response_model=AnalysisResult)
def analyze_period(period: int, board_type: str = 'main', top_n: int = 100, date: str = None):  # ✅ 同步
    """
    分析指定周期的股票重复情况
    
    Args:
        period: 分析周期（天数）
        board_type: 板块类型 ('all': 全部, 'main': 主板, 'bjs': 北交所)
        top_n: 每天分析前N个股票，默认100，可选100/200/400/600/800/1000/2000/3000
        date: 指定日期 (YYYYMMDD格式)，不传则使用最新日期
    """
    try:
        import logging
        import sys
        logger = logging.getLogger(__name__)
        
        # 详细日志：记录原始参数
        sys.stderr.write(f"\n🔍 Router层收到参数:\n")
        sys.stderr.write(f"   period={period} (type: {type(period).__name__})\n")
        sys.stderr.write(f"   top_n={top_n} (type: {type(top_n).__name__})\n")
        sys.stderr.write(f"   board_type={board_type} (type: {type(board_type).__name__})\n")
        sys.stderr.flush()
        
        # 确保top_n是整数（FastAPI应该已经转换了，但以防万一）
        top_n = int(top_n)
        
        # 参数验证
        if top_n not in [100, 200, 400, 600, 800, 1000, 2000, 3000]:
            sys.stderr.write(f"⚠️  警告: top_n={top_n} 不在允许范围内，使用默认值100\n")
            sys.stderr.flush()
            top_n = 100  # 默认值
        
        logger.info(f"🎯 API调用参数: period={period}, top_n={top_n}, board_type={board_type}, date={date}")
        
        return analysis_service.analyze_period(period, max_count=top_n, board_type=board_type, target_date=date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hot-spots/full")
def get_hot_spots_full(date: str = None):  # ✅ 同步
    """
    获取完整热点榜数据（带rank_label）
    
    v0.5.0: 使用统一缓存系统
    
    返回14天TOP1000热点榜，包含排名标签和出现次数
    用于前端搜索功能
    
    Args:
        date: 指定日期 (YYYYMMDD格式)，不传则使用最新日期
    
    Returns:
        {
            "date": "20251107",
            "total_count": 1000,
            "stocks": [...]
        }
    """
    try:
        import logging
        from ..core.caching import cache
        logger = logging.getLogger(__name__)
        
        # 获取目标日期
        if not date:
            from ..services.numpy_cache_middleware import numpy_cache
            latest_date_obj = numpy_cache.get_latest_date()
            if latest_date_obj:
                date = latest_date_obj.strftime('%Y%m%d')
            else:
                raise HTTPException(status_code=404, detail="无可用日期")
        
        # v0.5.0: 优先从统一缓存读取
        cache_key = f"hotspots_full_{date}"
        cached = cache.get_api_cache("hotspots", cache_key)
        if cached:
            logger.debug(f"✨ 热点榜缓存命中: {date}")
            return cached
        
        logger.info(f"获取热点榜完整数据: date={date}")
        
        # 从 HotSpotsCache 获取数据
        stocks = HotSpotsCache.get_full_data(date)
        
        result = {
            "date": date,
            "total_count": len(stocks),
            "stocks": stocks
        }
        
        # 存入统一缓存 (TTL=25小时)
        cache.set_api_cache("hotspots", cache_key, result, ttl=90000)
        
        return result
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"获取热点榜数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market/volatility-summary")
def get_market_volatility_summary(days: int = 3):  # ✅ 同步
    """
    获取市场波动率汇总数据
    
    返回最近N天的全市场平均波动率，用于顶栏展示
    
    Args:
        days: 返回最近N天的数据，默认3天
    
    Returns:
        {
            "current": 2.35,
            "days": [
                {"date": "20251127", "avg_volatility": 2.35, "stock_count": 5000},
                {"date": "20251126", "avg_volatility": 2.42, "stock_count": 5000},
                {"date": "20251125", "avg_volatility": 2.18, "stock_count": 5000}
            ],
            "trend": "down",  // up/down/flat
            "stock_count": 5435
        }
    """
    try:
        result = numpy_cache.get_market_volatility_summary(days=days)
        
        if 'error' in result:
            raise HTTPException(status_code=500, detail=result['error'])
        
        return result
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"获取市场波动率数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
