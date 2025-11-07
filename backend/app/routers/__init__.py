"""
API路由包
"""
from .analysis import router as analysis_router
from .stock import router as stock_router
from .industry import router as industry_router
from .rank_jump import router as rank_jump_router
from .steady_rise import router as steady_rise_router
from .sector import router as sector_router

__all__ = [
    "analysis_router",
    "stock_router",
    "industry_router",
    "rank_jump_router",
    "steady_rise_router",
    "sector_router",
]
