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
def analyze_steady_rise(  # ✅ 同步
    period: int = Query(default=3, ge=2, le=14, description="分析周期（天数）"),
    board_type: str = Query(default='main', description="板块类型: all/main/bjs"),
    min_rank_improvement: int = Query(default=100, ge=50, le=5000, description="最小排名提升幅度"),
    sigma_multiplier: float = Query(default=1.0, ge=0.1, le=3.0, description="σ倍数"),
    date: str = Query(default=None, description="指定日期 (YYYYMMDD格式)")
):
    """
    分析稳步上升的股票
    
    Args:
        period: 分析周期（天数）
        board_type: 板块类型 ('all': 全部, 'main': 主板, 'bjs': 北交所)
        min_rank_improvement: 最小排名提升幅度，默认100
        sigma_multiplier: σ倍数，默认1.0
        date: 指定日期 (YYYYMMDD格式)，不传则使用最新日期
    
    Returns:
        稳步上升分析结果
    """
    try:
        return steady_rise_service.analyze_steady_rise(
            period=period,
            board_type=board_type,
            min_rank_improvement=min_rank_improvement,
            sigma_multiplier=sigma_multiplier,
            target_date=date
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
