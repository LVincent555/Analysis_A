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


class IndustryStatWeighted(BaseModel):
    """单个行业统计（加权版本）"""
    industry: str
    count: int                    # 股票数量
    percentage: float             # 百分比
    
    # B方案（基于排名的加权）
    total_heat_rank: float        # B1: 总热度 = Σ(1/rank^k)
    avg_heat_rank: float          # B2: 平均热度 = B1/count
    
    # C方案（基于总分的加权）
    total_score: float            # C1: 总分数 = Σ(total_score)
    avg_score: float              # C2: 平均分数 = C1/count


class IndustryStatsWeighted(BaseModel):
    """行业统计数据（加权版本）"""
    date: str
    total_stocks: int             # 总股票数
    k_value: float                # 使用的k值
    metric_type: str              # 排序指标：'B1'/'B2'/'C1'/'C2'
    stats: List[IndustryStatWeighted]
