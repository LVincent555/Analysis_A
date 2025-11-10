"""
股票相关数据模型
"""
from typing import List, Optional
from pydantic import BaseModel, Field, model_serializer


class DateRankInfo(BaseModel):
    """日期和排名信息"""
    date: str
    rank: int
    # 技术指标
    price_change: Optional[float] = None  # 涨跌幅
    turnover_rate: Optional[float] = None  # 换手率
    volume_days: Optional[float] = None  # 放量天数
    avg_volume_ratio_50: Optional[float] = None  # 平均量比_50天
    volatility: Optional[float] = None  # 波动率


class StockInfo(BaseModel):
    """股票基本信息"""
    code: str
    name: Optional[str] = None
    industry: Optional[str] = None
    rank: Optional[int] = None
    count: Optional[int] = None  # 重复出现次数
    date_rank_info: Optional[List[DateRankInfo]] = None  # 出现日期和排名信息
    
    @model_serializer
    def ser_model(self) -> dict:
        """序列化时添加旧字段别名以向后兼容"""
        result = {
            "code": self.code,
            "name": self.name,
            "industry": self.industry,
            "rank": self.rank,
            "count": self.count,
            # 向后兼容旧前端的字段
            "stock_code": self.code,
            "stock_name": self.name,
            "latest_rank": self.rank,
            "appearances": self.count
        }
        
        # 添加date_rank_info（如果存在）
        if self.date_rank_info is not None:
            result["date_rank_info"] = [
                {"date": info.date, "rank": info.rank} 
                for info in self.date_rank_info
            ]
            
            # 添加最新一天的涨跌幅（从最后一个date_rank_info中获取）
            if len(self.date_rank_info) > 0:
                latest_info = self.date_rank_info[-1]
                result["price_change"] = latest_info.price_change
        else:
            result["price_change"] = None
        
        return result


class StockHistory(BaseModel):
    """股票历史数据"""
    code: str
    name: str
    industry: str
    date_rank_info: List[DateRankInfo]
    appears_count: int  # 出现次数
    dates: List[str]  # 出现的日期列表
    signals: Optional[List[str]] = []  # 信号列表（如：["TOP100·5次", "排名跳变↑1500"]）


class RankJumpStock(BaseModel):
    """排名跳变股票"""
    code: str
    name: str
    industry: str
    latest_rank: int  # 最新排名
    previous_rank: int  # 前一天排名
    rank_change: int  # 排名变化（正数表示向前跳）
    latest_date: str  # 最新日期
    previous_date: str  # 前一天日期
    # 技术指标
    price_change: Optional[float] = None  # 涨跌幅
    turnover_rate: Optional[float] = None  # 换手率
    volume_days: Optional[float] = None  # 放量天数
    avg_volume_ratio_50: Optional[float] = None  # 平均量比_50天
    volatility: Optional[float] = None  # 波动率


class RankJumpResult(BaseModel):
    """排名跳变分析结果"""
    stocks: List[RankJumpStock]
    total_count: int
    jump_threshold: int
    latest_date: str
    previous_date: str
    # 统计信息
    mean_rank_change: Optional[float] = None  # 平均跳变幅度
    std_rank_change: Optional[float] = None  # 跳变幅度标准差
    sigma_range: Optional[List[float]] = None  # ±1σ范围 [下限, 上限]
    sigma_stocks: Optional[List[RankJumpStock]] = None  # ±1σ范围内的股票


class SteadyRiseStock(BaseModel):
    """稳步上升股票"""
    code: str
    name: str
    industry: str
    start_rank: int  # 起始排名
    end_rank: int  # 结束排名
    total_improvement: int  # 总排名提升
    avg_daily_improvement: float  # 平均每天提升
    rank_history: List[int]  # 排名历史
    dates: List[str]  # 日期列表
    # 技术指标（最新一天的）
    price_change: Optional[float] = None
    turnover_rate: Optional[float] = None
    volume_days: Optional[float] = None
    avg_volume_ratio_50: Optional[float] = None
    volatility: Optional[float] = None


class SteadyRiseResult(BaseModel):
    """稳步上升分析结果"""
    stocks: List[SteadyRiseStock]
    total_count: int
    period: int
    dates: List[str]
    min_rank_improvement: int
    # 统计信息
    mean_improvement: Optional[float] = None  # 平均提升幅度
    std_improvement: Optional[float] = None  # 提升幅度标准差
    sigma_range: Optional[List[float]] = None  # ±1σ范围 [下限, 上限]
    sigma_stocks: Optional[List[SteadyRiseStock]] = None  # ±1σ范围内的股票
