"""
技术指标计算器
Technical Indicator Calculator

功能：
- 计算布林乖离率
- 计算下影线比例
- 计算排名变化
- 其他辅助指标
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass


@dataclass
class IndicatorResult:
    """指标计算结果"""
    boll_bias: float            # 布林乖离率 (%)
    shadow_ratio: float         # 下影线比例 (0-1)
    rank_change: int            # 排名变化（负数表示进步）
    turnover_ratio: float       # 换手率相对均值比例
    
    def to_dict(self) -> dict:
        return {
            'boll_bias': round(self.boll_bias, 2),
            'shadow_ratio': round(self.shadow_ratio, 4),
            'rank_change': self.rank_change,
            'turnover_ratio': round(self.turnover_ratio, 2),
        }


class IndicatorCalculator:
    """
    技术指标计算器
    
    提供各种辅助技术指标的计算功能
    """
    
    def __init__(
        self,
        boll_period: int = 20,      # 布林带周期
        boll_std_dev: float = 2.0,  # 布林带标准差倍数
        turnover_avg_period: int = 5  # 换手率均值周期
    ):
        self.boll_period = boll_period
        self.boll_std_dev = boll_std_dev
        self.turnover_avg_period = turnover_avg_period
    
    def calculate_boll_bias(
        self,
        closes: List[float],
        boll_mid: Optional[float] = None
    ) -> float:
        """
        计算布林乖离率
        
        公式：(收盘价 - 布林中轨) / 布林中轨 × 100%
        
        Args:
            closes: 收盘价序列
            boll_mid: 布林中轨值（可选，如果不提供则计算）
            
        Returns:
            乖离率 (%)
        """
        if len(closes) < self.boll_period:
            return 0.0
        
        current_close = closes[-1]
        
        if boll_mid is None:
            # 计算布林中轨（MA）
            boll_mid = np.mean(closes[-self.boll_period:])
        
        if boll_mid == 0:
            return 0.0
        
        bias = (current_close - boll_mid) / boll_mid * 100
        return bias
    
    def calculate_boll_bands(
        self,
        closes: List[float]
    ) -> Tuple[float, float, float]:
        """
        计算布林带上中下轨
        
        Args:
            closes: 收盘价序列
            
        Returns:
            (上轨, 中轨, 下轨)
        """
        if len(closes) < self.boll_period:
            current = closes[-1] if closes else 0
            return current, current, current
        
        recent = closes[-self.boll_period:]
        mid = np.mean(recent)
        std = np.std(recent)
        
        upper = mid + self.boll_std_dev * std
        lower = mid - self.boll_std_dev * std
        
        return upper, mid, lower
    
    def calculate_shadow_ratio(
        self,
        open_price: float,
        close: float,
        high: float,
        low: float
    ) -> float:
        """
        计算下影线比例
        
        公式：(min(开,收) - 最低) / (最高 - 最低)
        
        Args:
            open_price: 开盘价
            close: 收盘价
            high: 最高价
            low: 最低价
            
        Returns:
            下影线比例 (0-1)
        """
        if high == low:
            return 0.0
        
        body_low = min(open_price, close)
        lower_shadow = body_low - low
        total_range = high - low
        
        return lower_shadow / total_range
    
    def calculate_rank_change(
        self,
        current_rank: int,
        previous_rank: int
    ) -> int:
        """
        计算排名变化
        
        Args:
            current_rank: 当前排名
            previous_rank: 前一日排名
            
        Returns:
            排名变化（负数表示进步/排名上升）
        """
        return current_rank - previous_rank
    
    def calculate_turnover_ratio(
        self,
        turnovers: List[float]
    ) -> float:
        """
        计算换手率相对均值比例
        
        公式：当日换手率 / N日均换手率
        
        Args:
            turnovers: 换手率序列
            
        Returns:
            换手率比例
        """
        if len(turnovers) < 2:
            return 1.0
        
        current = turnovers[-1]
        
        if len(turnovers) < self.turnover_avg_period:
            avg = np.mean(turnovers[:-1])
        else:
            avg = np.mean(turnovers[-self.turnover_avg_period-1:-1])
        
        if avg == 0:
            return 1.0
        
        return current / avg
    
    def is_volume_shrink(
        self,
        turnovers: List[float],
        threshold: float = 5.0
    ) -> Dict:
        """
        判断是否极度缩量
        
        条件：换手率 < threshold 且 低于均值
        
        Args:
            turnovers: 换手率序列
            threshold: 换手率阈值（默认5%）
            
        Returns:
            缩量判断结果
        """
        if not turnovers:
            return {'is_shrink': False, 'score': 0, 'turnover': 0}
        
        current = turnovers[-1]
        ratio = self.calculate_turnover_ratio(turnovers)
        
        is_shrink = current < threshold and ratio < 1.0
        
        # 评分
        score = 0
        if current < 3.0 and ratio < 0.7:
            score = 10  # 极度缩量
        elif current < 5.0 and ratio < 0.85:
            score = 7   # 明显缩量
        elif current < 7.0 and ratio < 1.0:
            score = 4   # 轻微缩量
        
        return {
            'is_shrink': is_shrink,
            'score': score,
            'turnover': round(current, 2),
            'ratio': round(ratio, 2)
        }
    
    def analyze_boll_support(
        self,
        closes: List[float],
        low: float
    ) -> Dict:
        """
        分析布林带支撑情况
        
        条件：乖离率在 -8% ~ -3% 之间为有效支撑区
        
        Args:
            closes: 收盘价序列
            low: 当日最低价
            
        Returns:
            布林带支撑分析结果
        """
        upper, mid, lower = self.calculate_boll_bands(closes)
        bias = self.calculate_boll_bias(closes, mid)
        
        current_close = closes[-1] if closes else 0
        
        # 判断是否在支撑区
        is_support = -8.0 <= bias <= -3.0
        
        # 判断是否触及下轨
        touched_lower = low <= lower * 1.01  # 允许1%误差
        
        # 评分
        score = 0
        if is_support:
            score = 12  # 在支撑区
        elif touched_lower and current_close > lower:
            score = 10  # 触及下轨后收回
        elif bias < -3.0 and bias >= -10.0:
            score = 6   # 接近支撑区
        
        return {
            'is_support': is_support,
            'score': score,
            'bias': round(bias, 2),
            'boll_upper': round(upper, 2),
            'boll_mid': round(mid, 2),
            'boll_lower': round(lower, 2),
            'touched_lower': touched_lower
        }
    
    def analyze_shadow(
        self,
        open_price: float,
        close: float,
        high: float,
        low: float
    ) -> Dict:
        """
        分析下影线情况
        
        Args:
            open_price: 开盘价
            close: 收盘价
            high: 最高价
            low: 最低价
            
        Returns:
            下影线分析结果
        """
        ratio = self.calculate_shadow_ratio(open_price, close, high, low)
        
        # 评分：下影线越长越好
        score = 0
        if ratio >= 0.6:
            score = 6   # 长下影线
        elif ratio >= 0.4:
            score = 4   # 中等下影线
        elif ratio >= 0.2:
            score = 2   # 短下影线
        
        return {
            'shadow_ratio': round(ratio, 4),
            'score': score,
            'has_long_shadow': ratio >= 0.5
        }
    
    def analyze_rank_change(
        self,
        current_rank: int,
        previous_rank: int,
        price_change: float
    ) -> Dict:
        """
        分析排名逆势跃升
        
        条件：股价跌但排名进步>500名
        
        Args:
            current_rank: 当前排名
            previous_rank: 前一日排名
            price_change: 涨跌幅 (%)
            
        Returns:
            排名分析结果
        """
        rank_change = self.calculate_rank_change(current_rank, previous_rank)
        
        # 排名逆势跃升：股价跌但排名进步
        is_contrarian = price_change < 0 and rank_change < -500
        
        # 评分
        score = 0
        if is_contrarian:
            if rank_change < -1000:
                score = 15  # 大幅逆势跃升
            elif rank_change < -500:
                score = 10  # 明显逆势跃升
        elif rank_change < -300:
            score = 5   # 一般进步
        
        return {
            'rank_change': rank_change,
            'is_contrarian': is_contrarian,
            'score': score
        }
