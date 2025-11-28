"""
波动率分析引擎
Volatility Analysis Engine

功能：
- 计算历史波动率
- 计算波动率压缩比（当前/均值）
- 识别波动率收敛/发散
"""

import numpy as np
from typing import List, Optional, Dict
from dataclasses import dataclass


@dataclass
class VolatilityResult:
    """波动率分析结果"""
    current_volatility: float       # 当前波动率
    avg_volatility: float           # 平均波动率（N日）
    compression_ratio: float        # 压缩比（当前/平均）
    is_compressed: bool             # 是否处于压缩状态
    trend: str                      # 趋势：expanding/compressing/stable
    
    def to_dict(self) -> dict:
        return {
            'current_volatility': round(self.current_volatility, 4),
            'avg_volatility': round(self.avg_volatility, 4),
            'compression_ratio': round(self.compression_ratio, 4),
            'is_compressed': self.is_compressed,
            'trend': self.trend,
        }


class VolatilityEngine:
    """
    波动率分析引擎
    
    用于分析股票的波动率状态，识别洗盘时的波动率压缩特征
    """
    
    def __init__(
        self,
        avg_period: int = 20,           # 均值计算周期
        compression_threshold: float = 1.0,  # 压缩判定阈值
        short_period: int = 5           # 短期周期（用于趋势判断）
    ):
        self.avg_period = avg_period
        self.compression_threshold = compression_threshold
        self.short_period = short_period
    
    def calculate_volatility(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float]
    ) -> float:
        """
        计算单日真实波动率（ATR方式）
        
        True Range = max(High-Low, |High-PrevClose|, |Low-PrevClose|)
        
        Args:
            highs: 最高价序列
            lows: 最低价序列
            closes: 收盘价序列
            
        Returns:
            当日波动率
        """
        if len(closes) < 2:
            if len(highs) > 0 and len(lows) > 0:
                return (highs[-1] - lows[-1]) / closes[-1] if closes[-1] > 0 else 0
            return 0
        
        high = highs[-1]
        low = lows[-1]
        prev_close = closes[-2]
        current_close = closes[-1]
        
        # 计算真实波幅
        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close)
        )
        
        # 归一化（相对于收盘价的百分比）
        if current_close > 0:
            return tr / current_close
        return 0
    
    def calculate_volatility_series(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float]
    ) -> List[float]:
        """
        计算波动率序列
        
        Args:
            highs: 最高价序列
            lows: 最低价序列
            closes: 收盘价序列
            
        Returns:
            波动率序列
        """
        volatilities = []
        
        for i in range(len(closes)):
            if i == 0:
                vol = (highs[i] - lows[i]) / closes[i] if closes[i] > 0 else 0
            else:
                high = highs[i]
                low = lows[i]
                prev_close = closes[i-1]
                current_close = closes[i]
                
                tr = max(
                    high - low,
                    abs(high - prev_close),
                    abs(low - prev_close)
                )
                vol = tr / current_close if current_close > 0 else 0
            
            volatilities.append(vol)
        
        return volatilities
    
    def analyze(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volatilities: Optional[List[float]] = None
    ) -> VolatilityResult:
        """
        分析波动率状态
        
        Args:
            highs: 最高价序列
            lows: 最低价序列
            closes: 收盘价序列
            volatilities: 预计算的波动率序列（可选）
            
        Returns:
            VolatilityResult 分析结果
        """
        # 计算波动率序列
        if volatilities is None:
            volatilities = self.calculate_volatility_series(highs, lows, closes)
        
        if len(volatilities) < self.avg_period:
            # 数据不足，返回默认值
            current_vol = volatilities[-1] if volatilities else 0
            return VolatilityResult(
                current_volatility=current_vol,
                avg_volatility=current_vol,
                compression_ratio=1.0,
                is_compressed=False,
                trend='stable'
            )
        
        # 当前波动率
        current_vol = volatilities[-1]
        
        # 平均波动率（最近N日）
        avg_vol = np.mean(volatilities[-self.avg_period:])
        
        # 压缩比
        compression_ratio = current_vol / avg_vol if avg_vol > 0 else 1.0
        
        # 是否处于压缩状态
        is_compressed = compression_ratio <= self.compression_threshold
        
        # 判断趋势
        trend = self._determine_trend(volatilities)
        
        return VolatilityResult(
            current_volatility=current_vol,
            avg_volatility=avg_vol,
            compression_ratio=compression_ratio,
            is_compressed=is_compressed,
            trend=trend
        )
    
    def _determine_trend(self, volatilities: List[float]) -> str:
        """
        判断波动率趋势
        
        Args:
            volatilities: 波动率序列
            
        Returns:
            趋势：expanding(扩张)/compressing(收缩)/stable(稳定)
        """
        if len(volatilities) < self.short_period + 1:
            return 'stable'
        
        recent = volatilities[-self.short_period:]
        prev = volatilities[-(self.short_period + 5):-self.short_period] if len(volatilities) >= self.short_period + 5 else volatilities[:-self.short_period]
        
        if not prev:
            return 'stable'
        
        recent_avg = np.mean(recent)
        prev_avg = np.mean(prev)
        
        if prev_avg == 0:
            return 'stable'
        
        change_ratio = (recent_avg - prev_avg) / prev_avg
        
        if change_ratio > 0.1:  # 增长超过10%
            return 'expanding'
        elif change_ratio < -0.1:  # 下降超过10%
            return 'compressing'
        else:
            return 'stable'
    
    def is_wash_trading_signal(
        self,
        highs: List[float],
        lows: List[float],
        closes: List[float],
        volatilities: Optional[List[float]] = None
    ) -> Dict:
        """
        判断是否有洗盘特征（波动率压缩）
        
        洗盘特征：
        - 波动率压缩比 <= 1.0
        - 波动率趋势为收缩或稳定
        
        Args:
            highs: 最高价序列
            lows: 最低价序列
            closes: 收盘价序列
            volatilities: 预计算的波动率序列（可选）
            
        Returns:
            洗盘信号分析结果
        """
        result = self.analyze(highs, lows, closes, volatilities)
        
        is_wash_signal = (
            result.is_compressed and 
            result.trend in ['compressing', 'stable']
        )
        
        # 评分：波动率压缩越明显，分数越高
        score = 0
        if result.compression_ratio <= 0.7:
            score = 10  # 极度压缩
        elif result.compression_ratio <= 0.85:
            score = 7   # 明显压缩
        elif result.compression_ratio <= 1.0:
            score = 4   # 轻微压缩
        
        return {
            'is_wash_signal': is_wash_signal,
            'score': score,
            'details': result.to_dict()
        }
