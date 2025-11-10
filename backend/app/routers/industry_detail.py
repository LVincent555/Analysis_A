"""
板块成分股详细分析API路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional

from ..services.industry_detail_service import industry_detail_service
from ..services.signal_calculator import SignalThresholds
from ..models.industry_detail import (
    IndustryStocksResponse, IndustryDetailResponse,
    IndustryTrendResponse, IndustryCompareRequest, IndustryCompareResponse
)

router = APIRouter(prefix="/api/industry", tags=["industry-detail"])


@router.get("/{industry_name}/stocks", response_model=IndustryStocksResponse)
async def get_industry_stocks(
    industry_name: str,
    date: Optional[str] = Query(None, description="日期 YYYYMMDD，默认最新"),
    sort_mode: str = Query("rank", description="排序模式: rank|score|price_change|volume|signal"),
    calculate_signals: bool = Query(True, description="是否计算信号"),
    # 信号阈值参数（可调节）
    hot_list_mode: str = Query("instant", description="热点榜模式: instant=总分TOP信号, frequent=最新热点TOP信号"),
    hot_list_top: int = Query(100, ge=50, le=500, description="热点榜阈值（TOP N）"),
    rank_jump_min: int = Query(2000, ge=1000, le=5000, description="跳变榜最小阈值"),
    steady_rise_days: int = Query(3, ge=2, le=10, description="稳步上升最小天数"),
    price_surge_min: float = Query(5.0, ge=1.0, le=10.0, description="涨幅榜最小阈值 %"),
    volume_surge_min: float = Query(10.0, ge=5.0, le=20.0, description="成交量榜最小阈值 %"),
    volatility_surge_min: float = Query(10.0, ge=10.0, le=200.0, description="波动率上升阈值（百分比变化 %）")
):
    """
    获取板块成分股列表（完整版，支持信号计算）
    
    Args:
        industry_name: 板块名称（如：食品、建材）
        date: 查询日期 YYYYMMDD
        sort_mode: 排序模式
            - rank: 按全市场排名升序（默认）
            - score: 按总分降序
            - price_change: 按涨跌幅降序
            - volume: 按换手率降序
            - signal: 按信号强度降序 ⭐
        calculate_signals: 是否计算多榜单信号（默认True）
        hot_list_top: 热点榜阈值，默认100
        rank_jump_min: 跳变榜阈值，默认2000
        steady_rise_days: 稳步上升天数，默认3天
        price_surge_min: 涨幅榜阈值，默认5%
        volume_surge_min: 成交量榜阈值，默认10%
        volatility_surge_min: 波动率上升阈值（百分比变化），默认10%
    
    Returns:
        板块成分股列表及统计信息
    
    Examples:
        # 基础查询
        GET /api/industry/食品/stocks
        
        # 按信号强度排序
        GET /api/industry/食品/stocks?sort_mode=signal
        
        # 自定义信号阈值
        GET /api/industry/食品/stocks?sort_mode=signal&hot_list_top=200&rank_jump_min=150
        
        # 不计算信号（仅基础数据）
        GET /api/industry/食品/stocks?calculate_signals=false
    """
    try:
        # 构建信号阈值配置
        signal_thresholds = None
        if calculate_signals:
            signal_thresholds = SignalThresholds(
                hot_list_mode=hot_list_mode,
                hot_list_top=hot_list_top,
                hot_list_top2=500,  # 固定值
                rank_jump_min=rank_jump_min,
                rank_jump_large=3000,  # 固定值（更新为3000）
                steady_rise_days_min=steady_rise_days,
                steady_rise_days_large=5,  # 固定值
                price_surge_min=price_surge_min,
                volume_surge_min=volume_surge_min,
                volatility_surge_min=volatility_surge_min,
                volatility_surge_large=100.0  # 固定值
            )
        
        result = industry_detail_service.get_industry_stocks(
            industry_name=industry_name,
            target_date=date,
            sort_mode=sort_mode,
            calculate_signals=calculate_signals,
            signal_thresholds=signal_thresholds
        )
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"未找到板块 '{industry_name}' 或该板块无成分股数据"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/{industry_name}/detail", response_model=IndustryDetailResponse)
async def get_industry_detail(
    industry_name: str,
    date: Optional[str] = Query(None, description="日期 YYYYMMDD，默认最新"),
    k: float = Query(0.618, ge=0.1, le=0.99, description="K值（权重衰减参数）")
):
    """
    获取板块详细分析（包含4维指标）
    
    Args:
        industry_name: 板块名称（如：食品、建材）
        date: 查询日期 YYYYMMDD
        k: K值参数，用于加权计算，默认0.618
    
    Returns:
        板块详细分析，包括：
        - 4维指标：B1/B2/C1/C2
        - 成分股统计
        - 信号统计
    
    Examples:
        GET /api/industry/食品/detail
        GET /api/industry/食品/detail?k=0.8
        GET /api/industry/建材/detail?date=20251107
    """
    try:
        result = industry_detail_service.get_industry_detail(
            industry_name=industry_name,
            target_date=date,
            k_value=k
        )
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"未找到板块 '{industry_name}' 或该板块无成分股数据"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.get("/{industry_name}/trend", response_model=IndustryTrendResponse)
async def get_industry_trend(
    industry_name: str,
    period: int = Query(7, ge=3, le=30, description="追踪天数"),
    k: float = Query(0.618, ge=0.1, le=0.99, description="K值参数")
):
    """
    获取板块历史趋势
    
    Args:
        industry_name: 板块名称
        period: 追踪天数，默认7天
        k: K值参数
    
    Returns:
        板块历史趋势数据，包括：
        - 4维指标的历史变化
        - 平均排名的历史变化
        - TOP100数量的历史变化
        - 信号强度的历史变化
    
    Examples:
        GET /api/industry/食品/trend
        GET /api/industry/食品/trend?period=14
        GET /api/industry/建材/trend?period=7&k=0.5
    """
    try:
        result = industry_detail_service.get_industry_trend(
            industry_name=industry_name,
            period=period,
            k_value=k
        )
        
        if not result:
            raise HTTPException(
                status_code=404,
                detail=f"未找到板块 '{industry_name}' 的历史数据"
            )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(e)}")


@router.post("/compare", response_model=IndustryCompareResponse)
async def compare_industries(request: IndustryCompareRequest):
    """
    多板块对比（2-5个）
    
    Request Body:
        {
            "industries": ["食品", "建材", "化学"],
            "date": "20251107",  // 可选
            "k": 0.618  // 可选
        }
    
    Returns:
        多个板块的详细数据对比
    
    Examples:
        POST /api/industry/compare
        Body: {"industries": ["食品", "建材"]}
        
        POST /api/industry/compare
        Body: {"industries": ["食品", "建材", "化学"], "k": 0.8}
    """
    try:
        # 验证板块数量
        if len(request.industries) < 2:
            raise HTTPException(
                status_code=400,
                detail="至少需要2个板块进行对比"
            )
        if len(request.industries) > 5:
            raise HTTPException(
                status_code=400,
                detail="最多支持对比5个板块"
            )
        
        result = industry_detail_service.compare_industries(
            industry_names=request.industries,
            target_date=request.date,
            k_value=request.k
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"对比失败: {str(e)}")
