"""
排名跳变分析路由
"""
from fastapi import APIRouter, HTTPException, Query
from ..services.rank_jump_service_db import rank_jump_service_db
from ..models import RankJumpResult
from ..services.signal_calculator import SignalThresholds

router = APIRouter(prefix="/api", tags=["rank_jump"])

# 使用数据库服务
rank_jump_service = rank_jump_service_db

@router.get("/rank_jump", response_model=RankJumpResult)
@router.get("/rank-jump", response_model=RankJumpResult)  # 兼容前端的连字符格式
async def analyze_rank_jump(
    jump_threshold: int = Query(default=2500, ge=100, le=20000, description="排名跳变阈值"),
    board_type: str = Query(default='main', description="板块类型: all/main/bjs"),
    sigma_multiplier: float = Query(default=1.0, ge=0.1, le=3.0, description="σ倍数"),
    date: str = Query(default=None, description="指定日期 (YYYYMMDD格式)"),
    # 信号阈值参数
    calculate_signals: bool = Query(default=False, description="是否计算其他信号标签"),
    hot_list_top: int = Query(default=100, ge=10, le=1000),
    rank_jump_min: int = Query(default=1000, ge=500, le=5000),  # 跳变阈值改为1000
    steady_rise_days: int = Query(default=3, ge=2, le=14),
    price_surge_min: float = Query(default=5.0, ge=1.0, le=20.0),
    volume_surge_min: float = Query(default=10.0, ge=1.0, le=50.0),
    volatility_surge_min: float = Query(default=30.0, ge=10.0, le=200.0)
):
    """
    分析排名跳变的股票
    
    Args:
        jump_threshold: 排名跳变阈值，默认2500
        board_type: 板块类型 ('all': 全部, 'main': 主板, 'bjs': 北交所)
        sigma_multiplier: σ倍数，默认1.0
        date: 指定日期 (YYYYMMDD格式)，不传则使用最新日期
        calculate_signals: 是否计算其他信号标签
        其他信号阈值参数...
    
    Returns:
        排名跳变分析结果
    """
    try:
        # 构建信号阈值配置
        signal_thresholds = None
        if calculate_signals:
            signal_thresholds = SignalThresholds(
                hot_list_top=hot_list_top,
                rank_jump_min=rank_jump_min,
                rank_jump_large=rank_jump_min * 1.5,
                steady_rise_days_min=steady_rise_days,
                steady_rise_days_large=steady_rise_days * 2,
                price_surge_min=price_surge_min,
                volume_surge_min=volume_surge_min,
                volatility_surge_min=volatility_surge_min,
                volatility_surge_large=volatility_surge_min * 2
            )
        
        return rank_jump_service.analyze_rank_jump(
            jump_threshold=jump_threshold,
            board_type=board_type,
            sigma_multiplier=sigma_multiplier,
            target_date=date,
            calculate_signals=calculate_signals,
            signal_thresholds=signal_thresholds
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
