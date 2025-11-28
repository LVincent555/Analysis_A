"""
位置指标计算器 - 原神启动指标
Position Calculator - Multi-period Position Indicator

公式：位置指标(N) = 100 × (C - LLV(L,N)) / (HHV(C,N) - LLV(L,N))
- C: 当前收盘价
- LLV(L,N): N日内最低价的最低值
- HHV(C,N): N日内收盘价的最高值（注意：是收盘价不是最高价！）

四条线：
- 短期（白线）：N1 = 3天（默认）
- 中期（黄线）：固定10天
- 中长期（紫线）：固定20天
- 长期（红线）：N2 = 21天
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PositionResult:
    """位置指标计算结果"""
    short_term: float       # 短期位置（白线）
    medium_term: float      # 中期位置（黄线）
    medium_long_term: float # 中长期位置（紫线）
    long_term: float        # 长期位置（红线）
    
    def to_dict(self) -> dict:
        return {
            'short_term': round(self.short_term, 2),
            'medium_term': round(self.medium_term, 2),
            'medium_long_term': round(self.medium_long_term, 2),
            'long_term': round(self.long_term, 2),
        }


class PositionCalculator:
    """
    位置指标计算器
    
    用于计算股票在不同周期内的相对位置，
    判断当前价格处于近期高低点的什么位置。
    """
    
    def __init__(
        self,
        short_period: int = 3,      # 短期周期（白线）N1默认=3
        medium_period: int = 10,    # 中期周期（黄线）
        medium_long_period: int = 20,  # 中长期周期（紫线）
        long_period: int = 21       # 长期周期（红线）N2默认=21
    ):
        self.short_period = short_period
        self.medium_period = medium_period
        self.medium_long_period = medium_long_period
        self.long_period = long_period
    
    def calculate_position(
        self,
        closes: List[float],
        highs: List[float],
        lows: List[float],
        period: int
    ) -> float:
        """
        计算单个周期的位置指标
        
        公式：100 × (C - LLV(L,N)) / (HHV(C,N) - LLV(L,N))
        - HHV(C,N): N日内收盘价的最高值
        - LLV(L,N): N日内最低价的最低值
        
        Args:
            closes: 收盘价序列（最新的在最后）
            highs: 最高价序列（未使用，保留接口兼容）
            lows: 最低价序列
            period: 计算周期
            
        Returns:
            位置指标值 (0-100)
        """
        if len(closes) < period or len(lows) < period:
            return 50.0  # 数据不足时返回中间值
        
        # 取最近 period 天的数据
        recent_closes = closes[-period:]
        recent_lows = lows[-period:]
        
        current_close = recent_closes[-1]
        period_high_close = max(recent_closes)  # HHV(C,N) - 收盘价最高值
        period_low = min(recent_lows)           # LLV(L,N) - 最低价最低值
        
        # 避免除零
        if period_high_close == period_low:
            return 50.0
        
        position = 100 * (current_close - period_low) / (period_high_close - period_low)
        
        # 限制在 0-100 范围内
        return max(0.0, min(100.0, position))
    
    def calculate_all_positions(
        self,
        closes: List[float],
        highs: List[float],
        lows: List[float]
    ) -> PositionResult:
        """
        计算所有周期的位置指标（四条线）
        
        Args:
            closes: 收盘价序列（最新的在最后）
            highs: 最高价序列
            lows: 最低价序列
            
        Returns:
            PositionResult 包含四条线的位置值
        """
        short = self.calculate_position(closes, highs, lows, self.short_period)
        medium = self.calculate_position(closes, highs, lows, self.medium_period)
        medium_long = self.calculate_position(closes, highs, lows, self.medium_long_period)
        long = self.calculate_position(closes, highs, lows, self.long_period)
        
        return PositionResult(
            short_term=short,
            medium_term=medium,
            medium_long_term=medium_long,
            long_term=long
        )
    
    def calculate_positions_series(
        self,
        closes: List[float],
        highs: List[float],
        lows: List[float]
    ) -> List[PositionResult]:
        """
        计算整个序列的位置指标（用于历史分析）
        
        Args:
            closes: 收盘价序列
            highs: 最高价序列
            lows: 最低价序列
            
        Returns:
            每天的 PositionResult 列表
        """
        results = []
        min_length = max(self.short_period, self.medium_period, 
                        self.medium_long_period, self.long_period)
        
        for i in range(min_length, len(closes) + 1):
            result = self.calculate_all_positions(
                closes[:i],
                highs[:i],
                lows[:i]
            )
            results.append(result)
        
        return results
    
    def is_needle_under_20(
        self,
        closes: List[float],
        highs: List[float],
        lows: List[float],
        threshold: float = 20.0
    ) -> Tuple[bool, PositionResult]:
        """
        判断是否触发"单针下二十"信号
        
        条件：短期位置（白线）<= threshold
        
        Args:
            closes: 收盘价序列
            highs: 最高价序列
            lows: 最低价序列
            threshold: 触发阈值，默认20
            
        Returns:
            (是否触发, 位置指标结果)
        """
        positions = self.calculate_all_positions(closes, highs, lows)
        is_triggered = positions.short_term <= threshold
        
        return is_triggered, positions
    
    def detect_pattern(
        self,
        positions: PositionResult,
        config: Optional[Dict] = None
    ) -> Optional[str]:
        """
        检测形态类型
        
        形态A：空中加油（红线>60，白线<20）
        形态B：双底共振（红线<30，白线<20，差值<15）
        形态C：低位金叉（白线上穿红线，交叉点<30）
        形态D：缓慢下杀（2-3天缓慢下探）
        
        Args:
            positions: 位置指标结果
            config: 配置参数
            
        Returns:
            形态类型字符串或None
        """
        if config is None:
            config = {
                'sky_refuel_long_min': 60,      # 空中加油红线最小值
                'double_bottom_long_max': 30,   # 双底共振红线最大值
                'double_bottom_diff': 15,       # 双底共振红白线最大差值
                'needle_threshold': 20,         # 白线阈值
            }
        
        short = positions.short_term
        long = positions.long_term
        
        # 首先检查是否满足基本条件：白线 < 20
        if short > config.get('needle_threshold', 20):
            return None
        
        # 形态A：空中加油（红高白低）
        if long >= config.get('sky_refuel_long_min', 60):
            return 'sky_refuel'  # 空中加油
        
        # 形态B：双底共振（红白双低）
        if (long <= config.get('double_bottom_long_max', 30) and
            abs(long - short) <= config.get('double_bottom_diff', 15)):
            return 'double_bottom'  # 双底共振
        
        # 其他情况：一般单针
        return 'general_needle'
    
    @staticmethod
    def get_pattern_name(pattern: str) -> str:
        """获取形态的中文名称"""
        pattern_names = {
            'sky_refuel': '空中加油',
            'double_bottom': '双底共振',
            'low_golden_cross': '低位金叉',
            'slow_drop': '缓慢下杀',
            'general_needle': '一般单针',
        }
        return pattern_names.get(pattern, '未知形态')
