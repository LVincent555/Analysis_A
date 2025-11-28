"""
公共组件模块 - 可复用
Common Utils Module

包含：
- PositionCalculator: 位置指标计算（原神启动）
- IndicatorCalculator: 技术指标计算
- VolatilityEngine: 波动率分析
- HistoryAnalyzer: 历史行为分析器（核心！基于历史数据判断异常）
"""

from .position_calculator import PositionCalculator
from .indicator_calculator import IndicatorCalculator
from .volatility_engine import VolatilityEngine
from .history_analyzer import (
    HistoryAnalyzer, HistoryBaseline, PositionChangeAnalysis, 
    get_history_analyzer
)

__all__ = [
    'PositionCalculator',
    'IndicatorCalculator', 
    'VolatilityEngine',
    'HistoryAnalyzer',
    'HistoryBaseline',
    'PositionChangeAnalysis',
    'get_history_analyzer'
]
