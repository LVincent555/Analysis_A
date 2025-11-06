"""
行业相关数据模型
"""
from typing import List, Dict
from pydantic import BaseModel


class IndustryStat(BaseModel):
    """单个行业统计"""
    industry: str
    count: int
    percentage: float


class IndustryStats(BaseModel):
    """行业统计数据"""
    date: str
    total_stocks: int
    stats: List[IndustryStat]


class IndustryDateData(BaseModel):
    """某个日期的行业数据"""
    date: str
    industry_counts: Dict[str, int]


class IndustryTrend(BaseModel):
    """行业趋势数据"""
    industries: List[str]  # 所有行业列表
    data: List[IndustryDateData]  # 各日期的数据
