"""
股票查询相关API路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from ..services.stock_service_db import stock_service_db
from ..services.signal_calculator import SignalThresholds
from ..models import StockHistory

router = APIRouter(prefix="/api", tags=["stock"])

# 使用数据库服务
stock_service = stock_service_db


@router.get("/stock/{stock_code}", response_model=StockHistory)
async def query_stock(
    stock_code: str, 
    date: str = None,
    # 信号阈值参数（与industry_detail保持一致）
    hot_list_mode: str = Query("instant", description="热点榜模式: instant=总分TOP信号, frequent=最新热点TOP信号"),
    hot_list_top: int = Query(100, ge=50, le=500, description="热点榜阈值（TOP N）"),
    rank_jump_min: int = Query(1000, ge=100, le=5000, description="排名跳变最小阈值"),
    steady_rise_days: int = Query(3, ge=2, le=7, description="稳步上升天数"),
    price_surge_min: float = Query(5.0, ge=1.0, le=10.0, description="涨幅榜最小阈值 %"),
    volume_surge_min: float = Query(10.0, ge=5.0, le=20.0, description="成交量榜最小阈值 %"),
    volatility_surge_min: float = Query(10.0, ge=10.0, le=200.0, description="波动率上升阈值（百分比变化 %）")
):
    """
    查询个股历史排名数据
    
    Args:
        stock_code: 股票代码或名称
        date: 指定日期 (YYYYMMDD格式)，不传则使用最新日期
        hot_list_mode: 热点榜信号模式
        hot_list_top: 热点榜TOP阈值
        rank_jump_min: 排名跳变阈值
        steady_rise_days: 稳步上升天数
        price_surge_min: 涨幅榜阈值
        volume_surge_min: 成交量榜阈值
        volatility_surge_min: 波动率上升阈值
    """
    try:
        # 构建信号配置
        signal_thresholds = SignalThresholds(
            hot_list_mode=hot_list_mode,
            hot_list_top=hot_list_top,
            rank_jump_min=rank_jump_min,
            steady_rise_days_min=steady_rise_days,
            price_surge_min=price_surge_min,
            volume_surge_min=volume_surge_min,
            volatility_surge_min=volatility_surge_min
        )
        
        result = stock_service.search_stock(
            stock_code, 
            target_date=date,
            signal_thresholds=signal_thresholds
        )
        if not result:
            raise HTTPException(status_code=404, detail=f"未找到股票: {stock_code}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
