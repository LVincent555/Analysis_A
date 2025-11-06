"""
分析相关API路由
"""
from fastapi import APIRouter, HTTPException
from ..services.analysis_service_db import analysis_service_db
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
async def analyze_period(period: int, board_type: str = 'main'):
    """
    分析指定周期的股票重复情况
    
    Args:
        period: 分析周期（天数）
        board_type: 板块类型 ('all': 全部, 'main': 主板, 'bjs': 北交所)
    """
    try:
        return analysis_service.analyze_period(period, board_type=board_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
