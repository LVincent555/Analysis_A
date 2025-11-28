"""
洗盘检测器 - Washout Detector
基于历史行为分析，识别"假跌"（洗盘机会）vs "真跌"

核心逻辑（v2.1修正 - 计算密集型！）：
1. 获取股票最近2/3/5天的每日位置数据
2. 计算短期位置变化 vs 长期位置变化
3. 短期跌得快 + 长期跌得慢 = 洗盘信号！

这不是简单的阈值判断(if 短期<20)
而是真正的计算：
- 短期2天跌了50，长期只跌了20 → 比率2.5 → 洗盘
- 短期2天跌了50，长期也跌了40 → 比率1.25 → 真跌
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ..common.history_analyzer import (
    HistoryAnalyzer, HistoryBaseline, PositionChangeAnalysis, 
    get_history_analyzer
)
from ..common.position_calculator import PositionCalculator


class DropType(Enum):
    """下跌类型"""
    REAL_DROP = "real_drop"      # 真跌：要剔除
    FAKE_DROP = "fake_drop"      # 假跌：洗盘机会
    UNCERTAIN = "uncertain"      # 不确定
    NO_DROP = "no_drop"          # 没有下跌


@dataclass
class WashoutResult:
    """洗盘检测结果"""
    drop_type: DropType
    confidence: float           # 置信度 0-100
    washout_score: float        # 洗盘得分 0-100
    
    # 位置变化分析（核心！）
    short_change_2d: float = 0.0   # 短期2天变化
    short_change_3d: float = 0.0   # 短期3天变化
    long_change_2d: float = 0.0    # 长期2天变化
    long_change_3d: float = 0.0    # 长期3天变化
    change_ratio_2d: float = 0.0   # 2天变化比率
    change_ratio_3d: float = 0.0   # 3天变化比率
    
    # 当前位置
    current_short_pos: float = 0.0
    current_long_pos: float = 0.0
    
    # 各维度得分（用于前端展示）
    efficiency_score: float = 0.0     # 洗盘效率得分
    volatility_score: float = 0.0     # 波动率收敛得分
    volume_score: float = 0.0         # 缩量得分
    support_score: float = 0.0        # 支撑强度得分
    
    # 原始数据
    price_change: float = 0.0         # 股价涨跌幅
    position_change: float = 0.0      # 位置变化
    washout_zscore: float = 0.0       # 洗盘效率Z分数
    
    # 判断理由
    reasons: List[str] = None
    
    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []
    
    def to_dict(self) -> Dict:
        return {
            'drop_type': self.drop_type.value,
            'confidence': round(self.confidence, 1),
            'washout_score': round(self.washout_score, 1),
            # 位置变化（核心数据！）
            'short_change_2d': round(self.short_change_2d, 1),
            'short_change_3d': round(self.short_change_3d, 1),
            'long_change_2d': round(self.long_change_2d, 1),
            'long_change_3d': round(self.long_change_3d, 1),
            'change_ratio_2d': round(self.change_ratio_2d, 2),
            'change_ratio_3d': round(self.change_ratio_3d, 2),
            'current_short_pos': round(self.current_short_pos, 1),
            'current_long_pos': round(self.current_long_pos, 1),
            # 其他得分
            'efficiency_score': round(self.efficiency_score, 1),
            'volume_score': round(self.volume_score, 1),
            'price_change': round(self.price_change, 2),
            'reasons': self.reasons
        }


class WashoutDetector:
    """
    洗盘检测器（计算密集型！）
    
    核心职责：
    1. 计算每日的短期位置和长期位置
    2. 计算2/3/5天的位置变化
    3. 计算变化速度比率
    4. 判断：短期跌得快 + 长期跌得慢 = 洗盘
    """
    
    def __init__(
        self,
        short_period: int = 3,    # 短期位置周期
        long_period: int = 21,    # 长期位置周期
        max_real_drop_pct: float = -5.0,
    ):
        self.short_period = short_period
        self.long_period = long_period
        self.max_real_drop_pct = max_real_drop_pct
        self.history_analyzer = get_history_analyzer()
        self.position_calculator = PositionCalculator()
    
    def detect(
        self,
        stock_code: str,
        closes: List[float],
        highs: List[float],
        lows: List[float],
        volumes: List[float],
        turnovers: Optional[List[float]] = None,
        bbi_values: Optional[List[float]] = None,
    ) -> WashoutResult:
        """
        核心方法！基于历史数据计算洗盘信号
        
        计算过程：
        1. 计算每一天的短期位置、长期位置
        2. 计算2/3/5天的位置变化
        3. 计算变化速度比率
        4. 判断是否为洗盘
        """
        # 数据验证
        min_len = min(len(closes), len(highs), len(lows), len(volumes))
        if min_len < 6:
            return self._create_uncertain_result("数据不足（需要至少6天数据）")
        
        # ========== 核心计算：每日位置序列 ==========
        short_positions = []  # 每日短期位置
        long_positions = []   # 每日长期位置
        
        # 从第long_period天开始计算（确保有足够数据）
        start_idx = max(self.long_period, 6)
        
        for i in range(start_idx, min_len + 1):
            # 计算到第i天为止的短期位置
            short_pos = self.position_calculator.calculate_position(
                closes[:i], highs[:i], lows[:i], self.short_period
            )
            # 计算到第i天为止的长期位置
            long_pos = self.position_calculator.calculate_position(
                closes[:i], highs[:i], lows[:i], self.long_period
            )
            short_positions.append(short_pos)
            long_positions.append(long_pos)
        
        if len(short_positions) < 3:
            return self._create_uncertain_result("位置数据不足")
        
        # ========== 核心计算：位置变化分析 ==========
        pos_analysis = self.history_analyzer.analyze_position_changes(
            short_positions=short_positions,
            long_positions=long_positions,
            volumes=volumes[-len(short_positions):],
            closes=closes[-len(short_positions):],
            bbi_values=bbi_values[-len(short_positions):] if bbi_values else None
        )
        
        # 当前位置
        current_short = short_positions[-1]
        current_long = long_positions[-1]
        
        # 股价变化
        price_change = (closes[-1] - closes[-2]) / closes[-2] * 100 if closes[-2] != 0 else 0
        
        # ========== 判断下跌类型 ==========
        if pos_analysis.is_washout:
            drop_type = DropType.FAKE_DROP
        elif price_change < self.max_real_drop_pct:
            drop_type = DropType.REAL_DROP
        elif pos_analysis.washout_score > 0:
            drop_type = DropType.UNCERTAIN
        else:
            drop_type = DropType.NO_DROP
        
        # 计算置信度
        confidence = min(100.0, pos_analysis.washout_score + 20) if pos_analysis.is_washout else 30.0
        
        return WashoutResult(
            drop_type=drop_type,
            confidence=confidence,
            washout_score=pos_analysis.washout_score,
            # 位置变化（核心数据！）
            short_change_2d=pos_analysis.short_change_2d,
            short_change_3d=pos_analysis.short_change_3d,
            long_change_2d=pos_analysis.long_change_2d,
            long_change_3d=pos_analysis.long_change_3d,
            change_ratio_2d=pos_analysis.change_ratio_2d,
            change_ratio_3d=pos_analysis.change_ratio_3d,
            current_short_pos=current_short,
            current_long_pos=current_long,
            # 其他
            efficiency_score=pos_analysis.washout_score * 0.3,
            volume_score=15.0 if "量能萎缩" in str(pos_analysis.reasons) else 0.0,
            price_change=price_change,
            reasons=pos_analysis.reasons
        )
    
    def _create_uncertain_result(self, reason: str) -> WashoutResult:
        """创建不确定结果"""
        return WashoutResult(
            drop_type=DropType.UNCERTAIN,
            confidence=0.0,
            washout_score=0.0,
            reasons=[reason]
        )


# 全局单例
_washout_detector_instance: Optional[WashoutDetector] = None

def get_washout_detector() -> WashoutDetector:
    """获取洗盘检测器单例"""
    global _washout_detector_instance
    if _washout_detector_instance is None:
        _washout_detector_instance = WashoutDetector()
    return _washout_detector_instance
