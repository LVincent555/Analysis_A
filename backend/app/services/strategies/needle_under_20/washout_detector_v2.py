"""
洗盘检测器 v4.0 - 简化版

只实现两个基本形态：

1. 空中加油：
   - 红线在高位或中高位(>=50)，跌幅慢
   - 白线下杀快（从高位急跌）
   - 判断条件：白线是否触及20、下杀天数(1/2/3天)
   
2. 底部放量：
   - 白线下杀快，红线基本没动
   - 红线在中部或底部(<50)
   
核心：股价跌幅越小 = 洗盘越明显
默认用最宽松标准，都能筛出来
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

from ..common.position_calculator import PositionCalculator


class WashoutPattern(Enum):
    """洗盘形态类型"""
    SKY_REFUEL = "sky_refuel"       # 空中加油：红线高位(>=50)
    BOTTOM_VOLUME = "bottom_volume" # 底部放量：红线低位(<50)
    INVALID = "invalid"             # 无效


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
    
    # 新增：下杀天数和触及20判断
    drop_days: int = 1              # 下杀完成天数(1/2/3)
    touched_20: bool = False        # 白线是否触及20以下
    
    # 红线变化
    long_drop: float = 0.0          # 红线下跌幅度
    
    # 股价数据
    price_change_pct: float = 0.0   # 股价涨跌幅(%)
    
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
            '红线下跌': round(self.long_drop, 1),
            '下杀天数': self.drop_days,
            '触及20': self.touched_20,
            '股价涨跌': f"{self.price_change_pct:+.2f}%",
            'BBI站上': not self.bbi_break,
            'exclude_reason': self.exclude_reason,
            'score_details': self.score_details
        }


class WashoutDetectorV2:
    """
    洗盘检测器 v4.0 - 简化版
    
    只实现两个基本形态，用最宽松标准
    """
    
    def __init__(self, short_period: int = 3, long_period: int = 10):
        """初始化，默认使用10天周期（数据有限时），可切换21天对齐同花顺"""
        self.calculator = PositionCalculator(
            short_period=short_period,
            long_period=long_period
        )
        self.long_period = long_period
    
    def detect(
        self,
        closes: List[float],
        highs: List[float],
        lows: List[float],
        bbis: List[float] = None
    ) -> Optional[WashoutResult]:
        """
        检测洗盘形态（简化版）
        
        Args:
            closes: 收盘价序列（升序，最新在最后）
            highs: 最高价序列
            lows: 最低价序列
            bbis: BBI序列（可选）
            
        Returns:
            WashoutResult
        """
        # 最小数据需求：long_period + 7天（计算7天位置变化）
        min_data = self.calculator.long_period + 7
        if len(closes) < min_data:
            return None
        
        # ========== 1. 计算最近7天的位置 ==========
        positions = []
        for i in range(len(closes) - 7, len(closes) + 1):
            if i < self.calculator.long_period:
                continue
            pos = self.calculator.calculate_all_positions(
                closes[:i], highs[:i], lows[:i]
            )
            positions.append({
                'short': pos.short_term,
                'long': pos.long_term,
                'close': closes[i-1]
            })
        
        if len(positions) < 3:
            return None
        
        # 当前数据
        curr_short = positions[-1]['short']
        curr_long = positions[-1]['long']
        curr_close = positions[-1]['close']
        prev_close = positions[-2]['close']
        curr_bbi = bbis[-1] if bbis and len(bbis) > 0 else 0
        
        # ========== 2. 白线下杀分析 ==========
        # 找前几天白线最高点
        recent_shorts = [p['short'] for p in positions[:-1]]
        prev_short_max = max(recent_shorts) if recent_shorts else positions[-2]['short']
        short_drop = prev_short_max - curr_short
        
        # 找下杀开始的位置，计算下杀天数
        drop_days = 1
        for i in range(len(positions) - 2, -1, -1):
            if positions[i]['short'] >= prev_short_max - 5:  # 接近最高点
                drop_days = len(positions) - 1 - i
                break
        drop_days = min(drop_days, 5)  # 最多5天
        
        # 白线是否触及20以下
        touched_20 = curr_short <= 20
        
        # ========== 3. 红线变化分析 ==========
        recent_longs = [p['long'] for p in positions[:-1]]
        prev_long_max = max(recent_longs) if recent_longs else positions[-2]['long']
        long_drop = prev_long_max - curr_long
        
        # ========== 4. 股价变化 ==========
        # 计算下杀期间的总股价变化
        if drop_days > 0 and len(positions) > drop_days:
            start_close = positions[-(drop_days+1)]['close']
            price_change_pct = ((curr_close - start_close) / start_close * 100) if start_close > 0 else 0
        else:
            price_change_pct = ((curr_close - prev_close) / prev_close * 100) if prev_close > 0 else 0
        
        # BBI破位检查
        bbi_break = curr_bbi > 0 and curr_close < curr_bbi
        
        # ========== 5. 核心判断：白线位置和下杀 ==========
        # 条件1：当前白线必须在低位（<=10）
        # 条件2：白线有明显下杀（>=50点）
        if curr_short > 10:
            return WashoutResult(
                is_valid=False,
                pattern=WashoutPattern.INVALID,
                pattern_name='白线不在20以下',
                score=0,
                current_short=curr_short,
                current_long=curr_long,
                prev_short_max=prev_short_max,
                short_drop=short_drop,
                drop_days=drop_days,
                touched_20=touched_20,
                long_drop=long_drop,
                price_change_pct=price_change_pct,
                bbi_break=bbi_break,
                exclude_reason=f'白线不在20以下({curr_short:.0f}>20)'
            )
        
        if short_drop < 40:
            return WashoutResult(
                is_valid=False,
                pattern=WashoutPattern.INVALID,
                pattern_name='下杀幅度不足',
                score=0,
                current_short=curr_short,
                current_long=curr_long,
                prev_short_max=prev_short_max,
                short_drop=short_drop,
                drop_days=drop_days,
                touched_20=touched_20,
                long_drop=long_drop,
                price_change_pct=price_change_pct,
                bbi_break=bbi_break,
                exclude_reason=f'白线下杀不足({short_drop:.0f}<30)'
            )
        
        # ========== 6. 形态判断 ==========
        # 空中加油：红线高位(>=55)
        # 底部放量：红线中低位(<55)
        
        if curr_long >= 55:
            pattern = WashoutPattern.SKY_REFUEL
            pattern_name = '空中加油'
            base_score = 70
        else:
            pattern = WashoutPattern.BOTTOM_VOLUME
            pattern_name = '底部放量'
            base_score = 50
        
        # ========== 7. 评分 ==========
        # 白线下杀越多，加分越高
        drop_bonus = min(20, int(short_drop / 3))
        
        # 红线越稳（变化小），说明洗盘越明显
        if long_drop < 5:
            stable_bonus = 15
        elif long_drop < 10:
            stable_bonus = 10
        elif long_drop < 15:
            stable_bonus = 5
        else:
            stable_bonus = 0
        
        # 股价跌幅越小越好
        if price_change_pct >= 0:
            price_bonus = 15  # 不跌反涨
        elif price_change_pct > -1:
            price_bonus = 12
        elif price_change_pct > -3:
            price_bonus = 8
        elif price_change_pct > -5:
            price_bonus = 4
        else:
            price_bonus = 0
        
        # 触及20加分
        touch_bonus = 5 if touched_20 else 0
        
        score = base_score + drop_bonus + stable_bonus + price_bonus + touch_bonus
        
        return WashoutResult(
            is_valid=True,
            pattern=pattern,
            pattern_name=pattern_name,
            score=min(100, score),
            current_short=curr_short,
            current_long=curr_long,
            prev_short_max=prev_short_max,
            short_drop=short_drop,
            drop_days=drop_days,
            touched_20=touched_20,
            long_drop=long_drop,
            price_change_pct=price_change_pct,
            bbi_break=bbi_break,
            score_details={
                '形态基础分': base_score,
                '白线下杀分': drop_bonus,
                '红线稳定分': stable_bonus,
                '股价稳健分': price_bonus,
                '触及20分': touch_bonus
            }
        )


# 单例（v4.0 每次重新创建以确保使用最新逻辑）
_detector_instance: Optional[WashoutDetectorV2] = None


def get_washout_detector(short_period: int = 3, long_period: int = 10) -> WashoutDetectorV2:
    """获取洗盘检测器"""
    # v4.0: 每次创建新实例，确保使用最新逻辑
    return WashoutDetectorV2(short_period, long_period)
