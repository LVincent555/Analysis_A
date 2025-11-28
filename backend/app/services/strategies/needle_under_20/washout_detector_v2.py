"""
洗盘检测器 v2.1 - Washout Detector
基于红线(长期位置)、白线(短期位置)和股价跌幅分析洗盘形态

核心逻辑：
1. 形态基础分：空中加油(40) > 双底共振(25) > 低位洗盘(10)
2. 白线下杀加分：下杀越多加分越多（最多+30）
3. 股价跌幅扣分：跌幅越大扣分越多（洗盘效率低）
4. 洗盘效率 = 白线下杀 / 股价跌幅（效率高=真洗盘）

筛选选项：
- BBI破位：可选是否排除
- 股价跌幅阈值：5%/6%/8%/10%
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from ..common.position_calculator import PositionCalculator


class WashoutPattern(Enum):
    """洗盘形态类型"""
    SKY_REFUEL = "sky_refuel"       # 空中加油：红线高位
    DOUBLE_BOTTOM = "double_bottom" # 双底共振：红线中位
    LOW_WASHOUT = "low_washout"     # 低位洗盘：红线低位
    INVALID = "invalid"             # 无效（不符合条件）


@dataclass
class WashoutResult:
    """洗盘检测结果"""
    is_valid: bool                  # 是否有效洗盘形态
    pattern: WashoutPattern         # 形态类型
    pattern_name: str               # 形态名称
    score: int                      # 评分（0-100）
    
    # 位置数据
    current_short: float            # 当前白线位置
    current_long: float             # 当前红线位置
    prev_short_max: float           # 前几天白线最高
    short_drop: float               # 白线下杀幅度
    
    # 股价数据（新增）
    price_change_pct: float = 0.0   # 股价涨跌幅(%)
    washout_efficiency: float = 0.0 # 洗盘效率（白线下杀/股价跌幅）
    
    # BBI状态
    bbi_break: bool = False         # BBI是否破位
    
    # 排除原因（如果无效）
    exclude_reason: Optional[str] = None
    
    # 评分明细
    score_details: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'is_valid': self.is_valid,
            'pattern': self.pattern.value if self.pattern else None,
            'pattern_name': self.pattern_name,
            'score': self.score,
            '白线(短期)': round(self.current_short, 1),
            '红线(长期)': round(self.current_long, 1),
            '白线前高': round(self.prev_short_max, 1),
            '白线下杀': round(self.short_drop, 1),
            '股价涨跌': f"{self.price_change_pct:+.2f}%",
            '洗盘效率': round(self.washout_efficiency, 1),
            'BBI站上': not self.bbi_break,
            'exclude_reason': self.exclude_reason,
            'score_details': self.score_details
        }


class WashoutDetectorV2:
    """
    洗盘检测器 v2.0
    
    基于红线位置和白线下杀幅度判断洗盘形态
    """
    
    def __init__(self, short_period: int = 3, long_period: int = 10):
        self.calculator = PositionCalculator(
            short_period=short_period,
            long_period=long_period
        )
    
    def detect(
        self,
        closes: List[float],
        highs: List[float],
        lows: List[float],
        bbis: List[float] = None
    ) -> Optional[WashoutResult]:
        """
        检测洗盘形态
        
        Args:
            closes: 收盘价序列（升序，最新在最后）
            highs: 最高价序列
            lows: 最低价序列
            bbis: BBI序列（可选，用middle_band代替）
            
        Returns:
            WashoutResult（包含所有数据，由调用方决定是否筛选）
        """
        if len(closes) < self.calculator.long_period + 5:
            return None
        
        # 计算最近7天的位置
        positions = []
        for i in range(len(closes) - 7, len(closes) + 1):
            if i < self.calculator.long_period:
                continue
            pos = self.calculator.calculate_all_positions(
                closes[:i], highs[:i], lows[:i]
            )
            positions.append({
                'short': pos.short_term,
                'long': pos.long_term
            })
        
        if len(positions) < 3:
            return None
        
        # 当前位置
        curr_short = positions[-1]['short']
        curr_long = positions[-1]['long']
        curr_close = closes[-1]
        prev_close = closes[-2] if len(closes) >= 2 else curr_close
        curr_bbi = bbis[-1] if bbis and len(bbis) > 0 else 0
        
        # 股价涨跌幅计算
        price_change_pct = ((curr_close - prev_close) / prev_close * 100) if prev_close > 0 else 0
        
        # 白线下杀分析
        prev_short_max = max(p['short'] for p in positions[:-1])
        short_drop = prev_short_max - curr_short
        
        # 洗盘效率计算（白线下杀 / 股价跌幅）
        if price_change_pct < 0 and abs(price_change_pct) > 0.1:
            washout_efficiency = short_drop / abs(price_change_pct)
        else:
            washout_efficiency = short_drop  # 股价没跌或微涨，效率设为下杀幅度
        
        # BBI破位检查（只记录，不排除，由调用方决定）
        bbi_break = curr_bbi > 0 and curr_close < curr_bbi
        
        # 白线下杀评分
        if prev_short_max >= 80 and short_drop >= 30:
            drop_score = 30  # 从高位急跌
        elif prev_short_max >= 60 and short_drop >= 20:
            drop_score = 20  # 从中高位下跌
        elif short_drop >= 15:
            drop_score = 10  # 有一定下跌
        else:
            # 下杀不明显，但仍返回结果（由调用方决定是否排除）
            return WashoutResult(
                is_valid=False,
                pattern=WashoutPattern.INVALID,
                pattern_name='下杀不明显',
                score=0,
                current_short=curr_short,
                current_long=curr_long,
                prev_short_max=prev_short_max,
                short_drop=short_drop,
                price_change_pct=price_change_pct,
                washout_efficiency=washout_efficiency,
                bbi_break=bbi_break,
                exclude_reason='白线下杀不明显'
            )
        
        # 红线位置决定形态
        if curr_long >= 60:
            pattern = WashoutPattern.SKY_REFUEL
            pattern_name = '空中加油'
            base_score = 40
        elif curr_long >= 30:
            pattern = WashoutPattern.DOUBLE_BOTTOM
            pattern_name = '双底共振'
            base_score = 25
        else:
            pattern = WashoutPattern.LOW_WASHOUT
            pattern_name = '低位洗盘'
            base_score = 10
        
        # 计算总分
        score = base_score + drop_score
        
        return WashoutResult(
            is_valid=True,
            pattern=pattern,
            pattern_name=pattern_name,
            score=score,
            current_short=curr_short,
            current_long=curr_long,
            prev_short_max=prev_short_max,
            short_drop=short_drop,
            price_change_pct=price_change_pct,
            washout_efficiency=washout_efficiency,
            bbi_break=bbi_break,
            score_details={
                '形态基础分': base_score,
                '白线下杀分': drop_score
            }
        )


# 单例
_detector_instance: Optional[WashoutDetectorV2] = None


def get_washout_detector(short_period: int = 3, long_period: int = 10) -> WashoutDetectorV2:
    """获取洗盘检测器单例"""
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = WashoutDetectorV2(short_period, long_period)
    return _detector_instance
