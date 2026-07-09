"""Industry detail analysis routes."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ....models.industry_detail import (
    IndustryCompareRequest,
    IndustryCompareResponse,
    IndustryDetailResponse,
    IndustryStocksResponse,
    IndustryTrendResponse,
)
from ..application.industry_detail_queries import (
    CompareIndustriesUseCase,
    GetIndustryDetailTrendUseCase,
    GetIndustryDetailUseCase,
    GetIndustryStocksUseCase,
)
from ..application.queries import (
    CompareIndustriesQuery,
    GetIndustryDetailQuery,
    GetIndustryDetailTrendQuery,
    GetIndustryStocksQuery,
    IndustryDetailSignalThresholdSettings,
)
from ..infrastructure.industry_detail_queries import LegacyIndustryDetailAnalysisAdapter

router = APIRouter(prefix="/api/industry", tags=["industry-detail"])


def _industry_detail_adapter() -> LegacyIndustryDetailAnalysisAdapter:
    return LegacyIndustryDetailAnalysisAdapter()


def _signal_thresholds(
    *,
    calculate_signals: bool,
    hot_list_mode: str,
    hot_list_version: str,
    hot_list_top: int,
    rank_jump_min: int,
    steady_rise_days: int,
    price_surge_min: float,
    volume_surge_min: float,
    volatility_surge_min: float,
) -> IndustryDetailSignalThresholdSettings | None:
    if not calculate_signals:
        return None

    return IndustryDetailSignalThresholdSettings(
        hot_list_mode=hot_list_mode,
        hot_list_version=hot_list_version,
        hot_list_top=hot_list_top,
        hot_list_top2=500,
        hot_list_top3=2000,
        hot_list_top4=3000,
        rank_jump_min=rank_jump_min,
        rank_jump_large=3000,
        steady_rise_days_min=steady_rise_days,
        steady_rise_days_large=5,
        price_surge_min=price_surge_min,
        volume_surge_min=volume_surge_min,
        volatility_surge_min=volatility_surge_min,
        volatility_surge_large=100.0,
    )


@router.get("/{industry_name}/stocks", response_model=IndustryStocksResponse)
def get_industry_stocks(
    industry_name: str,
    date: Optional[str] = Query(None, description="日期 YYYYMMDD，默认最新"),
    sort_mode: str = Query("rank", description="排序模式: rank|score|price_change|volume|signal|signal_count"),
    calculate_signals: bool = Query(True, description="是否计算信号"),
    hot_list_mode: str = Query("frequent", description="热点榜模式: instant=总分TOP信号, frequent=最新热点TOP信号（默认）"),
    hot_list_version: str = Query("v2", description="热点榜版本: v1=原版（2.0倍数）, v2=新版（1.5倍数，默认）"),
    hot_list_top: int = Query(100, ge=50, le=500, description="热点榜阈值（TOP N）"),
    rank_jump_min: int = Query(2000, ge=1000, le=5000, description="跳变榜最小阈值"),
    steady_rise_days: int = Query(3, ge=2, le=10, description="稳步上升最小天数"),
    price_surge_min: float = Query(5.0, ge=1.0, le=10.0, description="涨幅榜最小阈值 %"),
    volume_surge_min: float = Query(10.0, ge=5.0, le=20.0, description="成交量榜最小阈值 %"),
    volatility_surge_min: float = Query(10.0, ge=10.0, le=200.0, description="波动率上升阈值（百分比变化 %）"),
):
    try:
        query = GetIndustryStocksQuery(
            industry_name=industry_name,
            target_date=date,
            sort_mode=sort_mode,
            calculate_signals=calculate_signals,
            signal_thresholds=_signal_thresholds(
                calculate_signals=calculate_signals,
                hot_list_mode=hot_list_mode,
                hot_list_version=hot_list_version,
                hot_list_top=hot_list_top,
                rank_jump_min=rank_jump_min,
                steady_rise_days=steady_rise_days,
                price_surge_min=price_surge_min,
                volume_surge_min=volume_surge_min,
                volatility_surge_min=volatility_surge_min,
            ),
        )
        result = GetIndustryStocksUseCase(_industry_detail_adapter()).execute(query)
        if not result:
            raise HTTPException(status_code=404, detail=f"未找到板块 '{industry_name}' 或该板块无成分股数据")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(exc)}") from exc


@router.get("/{industry_name}/detail", response_model=IndustryDetailResponse)
def get_industry_detail(
    industry_name: str,
    date: Optional[str] = Query(None, description="日期 YYYYMMDD，默认最新"),
    k: float = Query(0.618, ge=0.1, le=0.99, description="K值（权重衰减参数）"),
):
    try:
        result = GetIndustryDetailUseCase(_industry_detail_adapter()).execute(
            GetIndustryDetailQuery(industry_name=industry_name, target_date=date, k=k)
        )
        if not result:
            raise HTTPException(status_code=404, detail=f"未找到板块 '{industry_name}' 或该板块无成分股数据")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(exc)}") from exc


@router.get("/{industry_name}/trend", response_model=IndustryTrendResponse)
def get_industry_trend(
    industry_name: str,
    period: int = Query(7, ge=3, le=30, description="追踪天数"),
    k: float = Query(0.618, ge=0.1, le=0.99, description="K值参数"),
):
    try:
        result = GetIndustryDetailTrendUseCase(_industry_detail_adapter()).execute(
            GetIndustryDetailTrendQuery(industry_name=industry_name, period=period, k=k)
        )
        if not result:
            raise HTTPException(status_code=404, detail=f"未找到板块 '{industry_name}' 的历史数据")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"查询失败: {str(exc)}") from exc


@router.post("/compare", response_model=IndustryCompareResponse)
def compare_industries(request: IndustryCompareRequest):
    try:
        if len(request.industries) < 2:
            raise HTTPException(status_code=400, detail="至少需要2个板块进行对比")
        if len(request.industries) > 5:
            raise HTTPException(status_code=400, detail="最多支持对比5个板块")

        return CompareIndustriesUseCase(_industry_detail_adapter()).execute(
            CompareIndustriesQuery(
                industry_names=request.industries,
                target_date=request.date,
                k=request.k,
            )
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"对比失败: {str(exc)}") from exc
