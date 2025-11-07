"""
股票查询相关API路由
"""
from fastapi import APIRouter, HTTPException
from ..services.stock_service_db import stock_service_db
from ..models import StockHistory

router = APIRouter(prefix="/api", tags=["stock"])

# 使用数据库服务
stock_service = stock_service_db


@router.get("/stock/{stock_code}", response_model=StockHistory)
async def query_stock(stock_code: str, date: str = None):
    """
    查询个股历史排名数据
    
    Args:
        stock_code: 股票代码或名称
        date: 指定日期 (YYYYMMDD格式)，不传则使用最新日期
    """
    try:
        result = stock_service.search_stock(stock_code, target_date=date)
        if not result:
            raise HTTPException(status_code=404, detail=f"未找到股票: {stock_code}")
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
