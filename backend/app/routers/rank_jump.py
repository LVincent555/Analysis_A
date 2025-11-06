"""
排名跳变分析路由
"""
from fastapi import APIRouter, HTTPException, Query
from app.models.stock import RankJumpResult
from app.services.rank_jump_service import rank_jump_service

router = APIRouter(prefix="/api", tags=["rank-jump"])


@router.get("/rank-jump", response_model=RankJumpResult)
async def analyze_rank_jump(
    jump_threshold: int = Query(default=2500, ge=100, le=10000, description="排名跳变阈值"),
    filter_stocks: bool = Query(default=True, description="是否过滤双创板股票"),
    sigma_multiplier: float = Query(default=1.0, ge=0.1, le=3.0, description="σ倍数")
):
    """
    分析排名跳变的股票
    
    Args:
        jump_threshold: 排名跳变阈值，默认2500
        filter_stocks: 是否过滤双创板股票，默认True
        sigma_multiplier: σ倍数，默认1.0
    
    Returns:
        排名跳变分析结果
    """
    try:
        return rank_jump_service.analyze_rank_jump(
            jump_threshold=jump_threshold,
            filter_stocks=filter_stocks,
            sigma_multiplier=sigma_multiplier
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
