"""
稳步上升分析路由
"""
from fastapi import APIRouter, HTTPException, Query
from ..services.steady_rise_service_db import steady_rise_service_db
from ..models import SteadyRiseResult
from ..services.signal_calculator import SignalThresholds

router = APIRouter(prefix="/api", tags=["steady-rise"])

# 使用数据库服务
steady_rise_service = steady_rise_service_db


@router.get("/steady-rise", response_model=SteadyRiseResult)
def analyze_steady_rise(  # ✅ 同步
    period: int = Query(default=3, ge=2, le=14, description="分析周期（天数）"),
    board_type: str = Query(default='main', description="板块类型: all/main/bjs"),
    min_rank_improvement: int = Query(default=100, ge=50, le=5000, description="最小排名提升幅度"),
    sigma_multiplier: float = Query(default=1.0, ge=0.1, le=3.0, description="σ倍数"),
    date: str = Query(default=None, description="指定日期 (YYYYMMDD格式)"),
    # 信号阈值参数
    calculate_signals: bool = Query(default=False, description="是否计算其他信号标签"),
    hot_list_mode: str = Query("frequent", description="热点榜模式: instant=总分TOP信号, frequent=最新热点TOP信号（默认）"),
    hot_list_version: str = Query("v2", description="热点榜版本: v1=原版, v2=新版（默认）"),
    hot_list_top: int = Query(default=100, ge=10, le=1000),
    rank_jump_min: int = Query(default=1000, ge=500, le=5000),
    steady_rise_days: int = Query(default=3, ge=2, le=14),
    price_surge_min: float = Query(default=5.0, ge=1.0, le=20.0),
    volume_surge_min: float = Query(default=10.0, ge=1.0, le=50.0),
    volatility_surge_min: float = Query(default=10.0, ge=10.0, le=200.0)
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
        # 构建信号阈值配置
        signal_thresholds = None
        if calculate_signals:
            signal_thresholds = SignalThresholds(
                hot_list_mode=hot_list_mode,
                hot_list_version=hot_list_version,
                hot_list_top=hot_list_top,
                hot_list_top2=500,  # 固定值
                hot_list_top3=2000,  # TOP2000固定值
                hot_list_top4=3000,  # TOP3000固定值
                rank_jump_min=rank_jump_min,
                rank_jump_large=3000,  # 固定值（与其他API保持一致）
                steady_rise_days_min=steady_rise_days,
                steady_rise_days_large=steady_rise_days * 2,
                price_surge_min=price_surge_min,
                volume_surge_min=volume_surge_min,
                volatility_surge_min=volatility_surge_min,
                volatility_surge_large=volatility_surge_min * 2
            )

        return steady_rise_service.analyze_steady_rise(
            period=period,
            board_type=board_type,
            min_rank_improvement=min_rank_improvement,
            sigma_multiplier=sigma_multiplier,
            target_date=date,
            calculate_signals=calculate_signals,
            signal_thresholds=signal_thresholds
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
