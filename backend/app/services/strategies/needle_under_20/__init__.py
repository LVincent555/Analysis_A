"""
单针下二十策略子模块
Needle Under 20 Strategy Submodule

核心逻辑：捕捉主力洗盘后的拉升机会
通过多周期位置指标识别"指标快速下杀但股价坚挺"的信号

v2.0 更新：
- 空中加油：红线>=60 + 白线从高位急跌 → 最高优先级
- 双底共振：红线30-60 + 白线下跌 → 中等优先级
- 低位洗盘：红线<30 + 白线下跌 → 低优先级（不排除）
- BBI破位排除
"""

from .strategy import NeedleUnder20Strategy
from .config import NEEDLE_UNDER_20_CONFIG
from .signal_scorer import SignalScorer
from .pattern_recognizer import PatternRecognizer
from .washout_detector_v2 import (
    WashoutDetectorV2, WashoutResult, WashoutPattern, get_washout_detector
)

__all__ = [
    'NeedleUnder20Strategy',
    'NEEDLE_UNDER_20_CONFIG',
    'SignalScorer',
    'PatternRecognizer',
    'WashoutDetectorV2',
    'WashoutResult',
    'WashoutPattern',
    'get_washout_detector'
]
