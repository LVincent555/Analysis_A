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
    hot_list_mode: str = Query("instant", description="热点榜模式: instant=总分TOP信号, frequent=最新热点TOP信号")
):
    """
    查询个股历史排名数据
    
    Args:
        stock_code: 股票代码或名称
        date: 指定日期 (YYYYMMDD格式)，不传则使用最新日期
        hot_list_mode: 热点榜信号模式
    """
    try:
        # 构建信号配置
        signal_thresholds = SignalThresholds(hot_list_mode=hot_list_mode)
        
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
