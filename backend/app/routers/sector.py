"""
板块数据API路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List
from ..services.sector_service_db import sector_service_db
from ..models import SectorRankingResult, SectorDetail

router = APIRouter(prefix="/api", tags=["sector"])

# 使用数据库服务
sector_service = sector_service_db


@router.get("/sectors/dates", response_model=List[str])
async def get_available_dates():
    """
    获取所有可用的数据日期
    
    Returns:
        日期列表（降序）
    """
    try:
        return sector_service.get_available_dates()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectors/ranking", response_model=SectorRankingResult)
@router.get("/sector-ranking", response_model=SectorRankingResult)  # 兼容连字符格式
async def get_sector_ranking(
    date: str = Query(default=None, description="指定日期 (YYYYMMDD格式)"),
    limit: int = Query(default=100, ge=10, le=500, description="返回的板块数量")
):
    """
    获取板块排名
    
    Args:
        date: 指定日期 (YYYYMMDD格式)，不传则使用最新日期
        limit: 返回的板块数量，默认100
    
    Returns:
        板块排名结果
    """
    try:
        return sector_service.get_sector_ranking(
            target_date=date,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectors/{sector_name}", response_model=SectorDetail)
@router.get("/sector/{sector_name}", response_model=SectorDetail)  # 兼容单数形式
async def get_sector_detail(
    sector_name: str,
    days: int = Query(default=30, ge=7, le=365, description="返回的历史天数"),
    date: str = Query(default=None, description="指定日期 (YYYYMMDD格式)")
):
    """
    获取板块详细信息和历史数据
    
    Args:
        sector_name: 板块名称
        days: 返回的历史天数，默认30天
        date: 指定日期 (YYYYMMDD格式)，不传则使用最新日期
    
    Returns:
        板块详细信息
    """
    try:
        result = sector_service.get_sector_detail(
            sector_name=sector_name,
            days=days,
            target_date=date
        )
        
        if not result:
            raise HTTPException(status_code=404, detail=f"板块不存在: {sector_name}")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sectors/search/{keyword}", response_model=List[str])
async def search_sectors(keyword: str):
    """
    搜索板块
    
    Args:
        keyword: 搜索关键词
    
    Returns:
        匹配的板块名称列表
    """
    try:
        return sector_service.search_sectors(keyword)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
