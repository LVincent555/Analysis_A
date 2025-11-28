"""
形态识别器
Pattern Recognizer

识别四种典型形态：
- 形态A：空中加油（红高白低）
- 形态B：双底共振（红白双低）
- 形态C：低位金叉
- 形态D：缓慢下杀
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from .config import NEEDLE_UNDER_20_CONFIG, PATTERN_NAMES
from ..common.position_calculator import PositionCalculator, PositionResult


@dataclass
class PatternResult:
    """形态识别结果"""
    is_triggered: bool          # 是否触发信号
    pattern: Optional[str]      # 形态类型
    pattern_name: str           # 形态中文名
    positions: PositionResult   # 位置指标
    drop_days: int              # 下杀天数
    is_single_day: bool         # 是否单日急跌
    
    def to_dict(self) -> dict:
        return {
            'is_triggered': self.is_triggered,
            'pattern': self.pattern,
            'pattern_name': self.pattern_name,
            'positions': self.positions.to_dict(),
            'drop_days': self.drop_days,
            'is_single_day': self.is_single_day,
        }


class PatternRecognizer:
    """
    形态识别器
    
    识别单针下二十的各种形态
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or NEEDLE_UNDER_20_CONFIG
        self.position_calculator = PositionCalculator(
            short_period=self.config['N1_SHORT'],
            long_period=self.config['N2_LONG']
        )
    
    def recognize(
        self,
        closes: List[float],
        highs: List[float],
        lows: List[float],
        positions_history: Optional[List[PositionResult]] = None
    ) -> PatternResult:
        """
        识别形态
        
        Args:
            closes: 收盘价序列
            highs: 最高价序列
            lows: 最低价序列
            positions_history: 历史位置指标（用于判断下杀天数）
            
        Returns:
            PatternResult 形态识别结果
        """
        # 计算当前位置指标
        current_positions = self.position_calculator.calculate_all_positions(
            closes, highs, lows
        )
        
        # 检查是否触发基本条件：白线 < 20
        threshold = self.config['NEEDLE_THRESHOLD']
        is_triggered = current_positions.short_term <= threshold
        
        if not is_triggered:
            return PatternResult(
                is_triggered=False,
                pattern=None,
                pattern_name='未触发',
                positions=current_positions,
                drop_days=0,
                is_single_day=False
            )
        
        # 计算下杀天数
        drop_days, is_single_day = self._calculate_drop_days(
            closes, highs, lows, positions_history
        )
        
        # 识别形态
        pattern = self._detect_pattern(current_positions)
        pattern_name = PATTERN_NAMES.get(pattern, '未知形态')
        
        return PatternResult(
            is_triggered=True,
            pattern=pattern,
            pattern_name=pattern_name,
            positions=current_positions,
            drop_days=drop_days,
            is_single_day=is_single_day
        )
    
    def _detect_pattern(self, positions: PositionResult) -> str:
        """
        检测形态类型
        
        Args:
            positions: 位置指标结果
            
        Returns:
            形态类型字符串
        """
        short = positions.short_term
        long = positions.long_term
        
        # 形态A：空中加油（红高白低）
        if long >= self.config['SKY_REFUEL_LONG_MIN']:
            return 'sky_refuel'
        
        # 形态B：双底共振（红白双低）
        if (long <= self.config['DOUBLE_BOTTOM_LONG_MAX'] and
            abs(long - short) <= self.config['DOUBLE_BOTTOM_DIFF']):
            return 'double_bottom'
        
        # 其他情况
        return 'general_needle'
    
    def _calculate_drop_days(
        self,
        closes: List[float],
        highs: List[float],
        lows: List[float],
        positions_history: Optional[List[PositionResult]] = None
    ) -> Tuple[int, bool]:
        """
        计算下杀天数
        
        Args:
            closes: 收盘价序列
            highs: 最高价序列
            lows: 最低价序列
            positions_history: 历史位置指标
            
        Returns:
            (下杀天数, 是否单日急跌)
        """
        threshold = self.config['NEEDLE_THRESHOLD']
        max_days = self.config['DROP_WINDOW_DAYS']
        
        # 如果有历史位置数据，使用它来判断
        if positions_history and len(positions_history) >= 2:
            drop_days = 1
            for i in range(len(positions_history) - 2, -1, -1):
                if positions_history[i].short_term > 40:  # 从高位下来
                    break
                if positions_history[i].short_term <= threshold:
                    drop_days += 1
                    if drop_days >= max_days:
                        break
            
            is_single_day = drop_days == 1
            return drop_days, is_single_day
        
        # 否则，通过价格变化判断
        if len(closes) < 3:
            return 1, True
        
        # 简单判断：看最近几天是否连续下跌
        drop_days = 1
        for i in range(len(closes) - 2, max(0, len(closes) - max_days - 1), -1):
            if closes[i] > closes[i + 1]:  # 下跌
                drop_days += 1
            else:
                break
        
        is_single_day = drop_days == 1
        return min(drop_days, max_days), is_single_day
    
    def check_context(
        self,
        closes: List[float],
        highs: List[float],
        lows: List[float],
        lookback_days: int = 5
    ) -> Dict:
        """
        检查历史语境（前向判据）
        
        Args:
            closes: 收盘价序列
            highs: 最高价序列
            lows: 最低价序列
            lookback_days: 回溯天数
            
        Returns:
            语境检查结果
        """
        result = {
            'no_crash': True,       # 无连续暴跌
            'support_valid': False, # 支撑有效
            'trend_intact': False,  # 趋势未破坏
            'is_valid': True,       # 总体是否有效
        }
        
        if len(closes) < lookback_days + 1:
            return result
        
        # 检查是否有连续暴跌（>5%的大阴线）
        max_drop_pct = self.config['MAX_DROP_PCT']
        for i in range(len(closes) - lookback_days, len(closes) - 1):
            if i > 0:
                daily_change = (closes[i] - closes[i-1]) / closes[i-1] * 100
                if daily_change < max_drop_pct:
                    result['no_crash'] = False
                    break
        
        # 检查支撑有效性（简化：最低点没有大幅破位）
        recent_lows = lows[-lookback_days:]
        if len(recent_lows) >= 2:
            lowest = min(recent_lows[:-1])
            current_low = recent_lows[-1]
            # 如果当前最低价没有比前几天最低价低很多，支撑有效
            if current_low >= lowest * 0.97:  # 3%容忍度
                result['support_valid'] = True
        
        # 检查趋势是否完整（简化：价格整体向上）
        if len(closes) >= lookback_days:
            start_price = closes[-lookback_days]
            end_price = closes[-1]
            if end_price >= start_price * 0.95:  # 5%容忍度
                result['trend_intact'] = True
        
        # 总体判断
        result['is_valid'] = result['no_crash']
        
        return result
    
    def check_confirmation(
        self,
        current_close: float,
        next_open: Optional[float] = None,
        next_close: Optional[float] = None,
        next_volume_ratio: Optional[float] = None
    ) -> Dict:
        """
        检查次日确认（后向判据）
        
        Args:
            current_close: 当日收盘价
            next_open: 次日开盘价
            next_close: 次日收盘价
            next_volume_ratio: 次日成交量/当日成交量
            
        Returns:
            确认检查结果
        """
        result = {
            'next_day_gap_up': False,   # 次日高开
            'next_day_close_up': False, # 次日收阳
            'next_day_volume_up': False,# 次日放量
            'confirmation_score': 0,    # 确认得分
        }
        
        if next_open is not None:
            result['next_day_gap_up'] = next_open > current_close
            if result['next_day_gap_up']:
                result['confirmation_score'] += 5
        
        if next_close is not None:
            result['next_day_close_up'] = next_close > current_close
            if result['next_day_close_up']:
                result['confirmation_score'] += 5
        
        if next_volume_ratio is not None:
            amplify_ratio = self.config['VOLUME_AMPLIFY_RATIO']
            result['next_day_volume_up'] = next_volume_ratio >= amplify_ratio
            if result['next_day_volume_up']:
                result['confirmation_score'] += 5
        
        return result
