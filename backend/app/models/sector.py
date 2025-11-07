"""
板块数据模型
"""
from pydantic import BaseModel
from typing import List, Optional, Dict


class SectorInfo(BaseModel):
    """板块信息"""
    name: str
    rank: int
    total_score: Optional[float] = None
    price_change: Optional[float] = None
    turnover_rate: Optional[float] = None
    volume: Optional[int] = None
    volatility: Optional[float] = None


class SectorRankingResult(BaseModel):
    """板块排名结果"""
    date: str
    sectors: List[SectorInfo]
    total_count: int


class SectorDetail(BaseModel):
    """板块详细信息"""
    name: str
    history: List[Dict]
    days_count: int
