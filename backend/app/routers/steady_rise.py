"""
稳步上升分析路由
"""
from fastapi import APIRouter, HTTPException, Query
from ..services.steady_rise_service_db import steady_rise_service_db
from ..models import SteadyRiseResult

router = APIRouter(prefix="/api", tags=["steady-rise"])

# 使用数据库服务
steady_rise_service = steady_rise_service_db


@router.get("/steady-rise", response_model=SteadyRiseResult)
async def analyze_steady_rise(
    period: int = Query(default=3, ge=2, le=14, description="分析周期（天数）"),
    filter_stocks: bool = Query(default=True, description="是否过滤双创板股票"),
    min_rank_improvement: int = Query(default=100, ge=50, le=5000, description="最小排名提升幅度"),
    sigma_multiplier: float = Query(default=1.0, ge=0.1, le=3.0, description="σ倍数")
):
    """
    分析稳步上升的股票
    
    Args:
        period: 分析周期（天数）
        filter_stocks: 是否过滤双创板股票，默认True
        min_rank_improvement: 最小排名提升幅度，默认100
        sigma_multiplier: σ倍数，默认1.0
    
    Returns:
        稳步上升分析结果
    """
    try:
        return steady_rise_service.analyze_steady_rise(
            period=period,
            filter_stocks=filter_stocks,
            min_rank_improvement=min_rank_improvement,
            sigma_multiplier=sigma_multiplier
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
