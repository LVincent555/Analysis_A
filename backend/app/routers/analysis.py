"""
分析相关API路由
"""
from fastapi import APIRouter, HTTPException
from ..services.analysis_service_db import analysis_service_db
from ..services.hot_spots_cache import HotSpotsCache
from ..models import AnalysisResult, AvailableDates

router = APIRouter(prefix="/api", tags=["analysis"])

# 使用数据库服务
analysis_service = analysis_service_db


@router.get("/dates", response_model=AvailableDates)
async def get_available_dates():
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
async def analyze_period(period: int, board_type: str = 'main', top_n: int = 100, date: str = None):
    """
    分析指定周期的股票重复情况
    
    Args:
        period: 分析周期（天数）
        board_type: 板块类型 ('all': 全部, 'main': 主板, 'bjs': 北交所)
        top_n: 每天分析前N个股票，默认100，可选100/200/400/600/800/1000
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
        if top_n not in [100, 200, 400, 600, 800, 1000]:
            sys.stderr.write(f"⚠️  警告: top_n={top_n} 不在允许范围内，使用默认值100\n")
            sys.stderr.flush()
            top_n = 100  # 默认值
        
        logger.info(f"🎯 API调用参数: period={period}, top_n={top_n}, board_type={board_type}, date={date}")
        
        return analysis_service.analyze_period(period, max_count=top_n, board_type=board_type, target_date=date)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/hot-spots/full")
async def get_hot_spots_full(date: str = None):
    """
    获取完整热点榜数据（带rank_label）
    
    返回14天TOP1000热点榜，包含排名标签和出现次数
    用于前端搜索功能
    
    Args:
        date: 指定日期 (YYYYMMDD格式)，不传则使用最新日期
    
    Returns:
        {
            "date": "20251107",
            "total_count": 1000,
            "stocks": [
                {
                    "code": "920961",
                    "name": "创远信科",
                    "rank": 1,
                    "rank_label": "TOP100·12次",
                    "hit_count": 12,
                    ...
                }
            ]
        }
    """
    try:
        import logging
        logger = logging.getLogger(__name__)
        
        # 获取目标日期
        if not date:
            from ..services.memory_cache import memory_cache
            latest_date_obj = memory_cache.get_latest_date()
            if latest_date_obj:
                date = latest_date_obj.strftime('%Y%m%d')
            else:
                raise HTTPException(status_code=404, detail="无可用日期")
        
        logger.info(f"获取热点榜完整数据: date={date}")
        
        # 从缓存获取完整数据
        stocks = HotSpotsCache.get_full_data(date)
        
        return {
            "date": date,
            "total_count": len(stocks),
            "stocks": stocks
        }
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"获取热点榜数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
