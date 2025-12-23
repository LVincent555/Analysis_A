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
                {
                    "date": info.date, 
                    "rank": info.rank,
                    "price_change": info.price_change,
                    "turnover_rate": info.turnover_rate,
                    "volatility": info.volatility
                } 
                for info in self.date_rank_info
            ]
            
            # 添加最新一天的涨跌幅和波动率（从最后一个date_rank_info中获取）
            if len(self.date_rank_info) > 0:
                latest_info = self.date_rank_info[-1]
                result["price_change"] = latest_info.price_change
                result["volatility"] = latest_info.volatility
        else:
            result["price_change"] = None
            result["volatility"] = None
        
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
    signals: Optional[List[str]] = None
    signal_count: Optional[int] = None
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
    signals: Optional[List[str]] = None
    signal_count: Optional[int] = None
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


class StockDailyFull(BaseModel):
    """每日全量数据（包含所有83个指标）"""
    date: str
    rank: int
    
    # 基础价格数据
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    close_price: Optional[float] = None
    price_change: Optional[float] = None
    total_score: Optional[float] = None
    
    # 成交量相关
    volume: Optional[int] = None
    turnover_rate_percent: Optional[float] = None
    volume_days: Optional[float] = None
    avg_volume_ratio_50: Optional[float] = None
    volume_days_volume: Optional[float] = None
    avg_volume_ratio_50_volume: Optional[float] = None
    obv: Optional[int] = None
    obv_consec: Optional[int] = None
    obv_2: Optional[int] = None
    
    # 波动率相关
    volatility: Optional[float] = None
    volatile_consec: Optional[int] = None
    beta: Optional[float] = None
    beta_consec: Optional[int] = None
    correlation: Optional[float] = None
    
    # 市场数据
    market_cap_billions: Optional[float] = None
    jump: Optional[float] = None
    
    # 趋势指标
    long_term: Optional[float] = None
    short_term: Optional[int] = None
    overbought: Optional[int] = None
    oversold: Optional[int] = None
    
    # MACD系列
    macd_signal: Optional[float] = None
    dif_dem: Optional[float] = None
    macd_consec: Optional[int] = None
    dif_0: Optional[float] = None
    macdcons_consec: Optional[int] = None
    dem_0: Optional[float] = None
    demcons_consec: Optional[int] = None
    histgram: Optional[float] = None
    dif: Optional[float] = None
    dem: Optional[float] = None
    
    # LON系列
    lon_lonma: Optional[float] = None
    lon_consec: Optional[int] = None
    lon_0: Optional[float] = None
    loncons_consec: Optional[int] = None
    lonma_0: Optional[float] = None
    lonmacons_consec: Optional[int] = None
    lon_lonma_diff: Optional[float] = None
    lon: Optional[float] = None
    lonma: Optional[float] = None
    
    # KDJ系列
    slowkdj_signal: Optional[float] = None
    k_kdj: Optional[float] = None
    slowkdj_consec: Optional[int] = None
    slowk: Optional[float] = None
    
    # DMA
    dma: Optional[float] = None
    dma_consec: Optional[int] = None
    
    # DMI
    pdi_adx: Optional[float] = None
    dmiadx_consec: Optional[int] = None
    pdi_ndi: Optional[float] = None
    dmi_consec: Optional[int] = None
    adx: Optional[float] = None
    plus_di: Optional[float] = None
    
    # RSI
    rsi: Optional[float] = None
    rsi_consec: Optional[int] = None
    rsi_2: Optional[float] = None
    
    # CCI
    cci_neg_90: Optional[float] = None
    cci_lower_consec: Optional[int] = None
    cci_pos_90: Optional[float] = None
    cci_upper_consec: Optional[int] = None
    cci_neg_90_2: Optional[float] = None
    cci_pos_90_2: Optional[float] = None
    
    # BOLL
    bands_lower: Optional[float] = None
    bands_lower_consec: Optional[int] = None
    bands_middle: Optional[float] = None
    bands_middle_consec: Optional[int] = None
    bands_upper: Optional[float] = None
    bands_upper_consec: Optional[int] = None
    lower_band: Optional[float] = None
    middle_band: Optional[float] = None
    upper_band: Optional[float] = None
    
    # 其他
    lst_close: Optional[float] = None
    code2: Optional[str] = None
    name2: Optional[str] = None
    zhangdiefu2: Optional[float] = None
    volume_consec2: Optional[float] = None
    volume_50_consec2: Optional[float] = None


class StockFullHistory(BaseModel):
    """股票全量历史数据"""
    code: str
    name: str
    industry: str
    total_count: int
    daily_data: List[StockDailyFull]

