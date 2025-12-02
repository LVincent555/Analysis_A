"""
股票查询相关API路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from ..services.stock_service_db import stock_service_db
from ..services.signal_calculator import SignalThresholds
from ..models import StockHistory, StockFullHistory

router = APIRouter(prefix="/api", tags=["stock"])

# 使用数据库服务
stock_service = stock_service_db


@router.get("/stocks/raw-data")
def get_stock_raw_data(  # ✅ 同步，使用numpy缓存
    date: str = Query(default=None, description="指定日期 (YYYYMMDD格式)"),
    limit: int = Query(default=5000, ge=10, le=10000, description="返回数量")
):
    """
    获取当日股票原始排名数据
    
    ✅ 使用numpy缓存，不查询数据库
    """
    try:
        from datetime import datetime
        from ..services.numpy_cache_middleware import numpy_cache
        
        # 获取日期
        if date:
            target_date = datetime.strptime(date, '%Y%m%d').date()
        else:
            target_date = numpy_cache.get_latest_date()
        
        if not target_date:
            raise HTTPException(404, "没有可用数据")
        
        # ✅ 使用numpy缓存获取TOP N数据（已按rank排序）
        raw_data = numpy_cache.get_top_n_by_rank(target_date, limit)
        
        data = []
        for row in raw_data:
            stock_info = numpy_cache.get_stock_info(row['stock_code'])
            item = {
                'code': row['stock_code'],
                'name': stock_info.stock_name if stock_info else '',
                'industry': stock_info.industry if stock_info else '未知',
                'rank': row['rank'],
                'total_score': row.get('total_score'),
                'price_change': row.get('price_change'),
                'close_price': row.get('close_price'),
                'turnover_rate': row.get('turnover_rate'),
                'volume_days': row.get('volume_days'),
                'avg_volume_ratio_50': row.get('avg_volume_ratio_50'),
                'volatility': row.get('volatility'),
                'market_cap': row.get('market_cap'),
            }
            data.append(item)
        
        return {
            'date': target_date.strftime('%Y%m%d'),
            'total_count': len(data),
            'data': data
        }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock/search", response_model=List[StockFullHistory])
def search_stock_full(  # ✅ 同步
    q: str = Query(..., min_length=1, description="股票代码或名称（模糊匹配）"),
    limit: int = Query(5, ge=1, le=20, description="返回的最大匹配数量")
):
    """
    搜索股票并返回全量历史数据
    
    - 返回包含所有83个技术指标的完整数据
    - 支持代码或名称模糊搜索
    - 默认返回匹配度最高的前5个
    """
    try:
        results = stock_service.search_stock_full(q, limit)
        # 如果没有结果，返回空列表而不是404，符合搜索API惯例
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stock/{stock_code}", response_model=StockHistory)
def query_stock(  # ✅ 同步
    stock_code: str, 
    date: str = None,
    # 信号阈值参数（与industry_detail保持一致）
    hot_list_mode: str = Query("frequent", description="热点榜模式: instant=总分TOP信号, frequent=最新热点TOP信号（默认）"),
    hot_list_version: str = Query("v2", description="热点榜版本: v1=原版, v2=新版（默认）"),
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
            hot_list_version=hot_list_version,
            hot_list_top=hot_list_top,
            hot_list_top2=500,  # 固定值
            hot_list_top3=2000,  # TOP2000固定值
            hot_list_top4=3000,  # 新增：TOP3000固定值
            rank_jump_min=rank_jump_min,
            rank_jump_large=3000,  # 固定值（与板块查询保持一致）
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
