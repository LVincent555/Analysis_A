"""
板块成分股详细分析 - 数据模型
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date


class StockSignalInfo(BaseModel):
    """股票信号信息"""
    stock_code: str
    stock_name: str
    rank: int = Field(..., description="全市场排名")
    total_score: float = Field(..., description="总分")
    
    # 基础数据
    price_change: Optional[float] = Field(None, description="涨跌幅 %")
    turnover_rate_percent: Optional[float] = Field(None, description="换手率 %")
    volume_days: Optional[float] = Field(None, description="放量天数")
    market_cap_billions: Optional[float] = Field(None, description="总市值(亿)")
    volatility: Optional[float] = Field(None, description="波动率 %")
    
    # 多榜单信号
    signals: List[str] = Field(default_factory=list, description="信号标签列表")
    signal_count: int = Field(0, description="信号数量")
    signal_strength: float = Field(0.0, description="信号强度 0-1")
    
    # 详细信号标记
    in_hot_list: bool = Field(False, description="是否在热点榜")
    in_rank_jump: bool = Field(False, description="是否在排名跳变榜")
    rank_improvement: Optional[int] = Field(None, description="排名提升幅度")
    in_steady_rise: bool = Field(False, description="是否在稳步上升榜")
    rise_days: Optional[int] = Field(None, description="连续上升天数")
    in_price_surge: bool = Field(False, description="是否在涨幅榜")
    in_volume_surge: bool = Field(False, description="是否在成交量榜")
    
    # 历史信号（7天）
    signal_history: Optional[dict] = Field(None, description="历史信号数据")


class IndustryStocksResponse(BaseModel):
    """板块成分股列表响应"""
    industry: str = Field(..., description="板块名称")
    date: str = Field(..., description="日期 YYYYMMDD")
    stock_count: int = Field(..., description="成分股数量")
    
    # 不同排序模式的结果
    stocks: List[StockSignalInfo] = Field(..., description="成分股列表")
    
    # 统计信息
    statistics: dict = Field(default_factory=dict, description="统计数据")


class IndustryDetailResponse(BaseModel):
    """板块详细分析响应"""
    industry: str
    date: str
    stock_count: int
    
    # 板块4维指标
    B1: float = Field(..., description="B1指标")
    B2: float = Field(..., description="B2指标")
    C1: float = Field(..., description="C1指标")
    C2: float = Field(..., description="C2指标")
    
    # 统计数据
    avg_rank: float = Field(..., description="平均排名")
    top_100_count: int = Field(..., description="TOP 100数量")
    top_500_count: int = Field(..., description="TOP 500数量")
    top_1000_count: int = Field(..., description="TOP 1000数量")
    
    # 信号统计
    hot_list_count: int = Field(0, description="热点榜数量")
    rank_jump_count: int = Field(0, description="跳变榜数量")
    steady_rise_count: int = Field(0, description="稳步上升数量")
    multi_signal_count: int = Field(0, description="多信号股票数量")
    avg_signal_strength: float = Field(0.0, description="平均信号强度")


class IndustryTrendResponse(BaseModel):
    """板块历史趋势响应"""
    industry: str
    period: int
    dates: List[str]
    
    # 指标历史数据
    metrics_history: dict = Field(..., description="指标历史数据")
    
    # TOP股票变化
    top_stocks_changes: Optional[List[dict]] = Field(None, description="TOP股票排名变化")


class IndustryCompareRequest(BaseModel):
    """板块对比请求"""
    industries: List[str] = Field(..., min_items=2, max_items=5, description="板块列表 2-5个")
    date: Optional[str] = Field(None, description="日期 YYYYMMDD")
    k: float = Field(0.618, description="K值")


class IndustryCompareResponse(BaseModel):
    """板块对比响应"""
    date: str
    k_value: float
    industries: List[IndustryDetailResponse]
