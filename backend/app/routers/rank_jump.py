"""
排名跳变分析路由
"""
from fastapi import APIRouter, HTTPException, Query
from ..services.rank_jump_service_db import rank_jump_service_db
from ..models import RankJumpResult

router = APIRouter(prefix="/api", tags=["rank_jump"])

# 使用数据库服务
rank_jump_service = rank_jump_service_db

@router.get("/rank_jump", response_model=RankJumpResult)
@router.get("/rank-jump", response_model=RankJumpResult)  # 兼容前端的连字符格式
async def analyze_rank_jump(
    jump_threshold: int = Query(default=2500, ge=100, le=10000, description="排名跳变阈值"),
    board_type: str = Query(default='main', description="板块类型: all/main/bjs"),
    sigma_multiplier: float = Query(default=1.0, ge=0.1, le=3.0, description="σ倍数")
):
    """
    分析排名跳变的股票
    
    Args:
        jump_threshold: 排名跳变阈值，默认2500
        board_type: 板块类型 ('all': 全部, 'main': 主板, 'bjs': 北交所)
        sigma_multiplier: σ倍数，默认1.0
    
    Returns:
        排名跳变分析结果
    """
    try:
        return rank_jump_service.analyze_rank_jump(
            jump_threshold=jump_threshold,
            board_type=board_type,
            sigma_multiplier=sigma_multiplier
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
