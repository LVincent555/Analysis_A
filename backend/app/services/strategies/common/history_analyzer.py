"""
历史行为分析器 - History Analyzer
基于历史数据建立股票的"正常行为模式"，用于检测异常

核心理念（v2.1修正）：
- 不是"位置<阈值"的死逻辑
- 而是比较**短期位置变化**和**长期位置变化**的速度差异
- 短期跌得快 + 长期跌得慢 = 洗盘信号！

关键公式：
- 短期变化 = short_position[today] - short_position[N days ago]
- 长期变化 = long_position[today] - long_position[N days ago]
- 变化比率 = |短期变化| / |长期变化|
- 比率 > 2 表示短期下杀快但长期稳定 = 洗盘
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np
from functools import lru_cache


@dataclass
class PositionChangeAnalysis:
    """位置变化分析结果（核心！）"""
    # N天内的位置变化
    short_change_2d: float = 0.0   # 短期位置2天变化
    short_change_3d: float = 0.0   # 短期位置3天变化
    short_change_5d: float = 0.0   # 短期位置5天变化
    
    long_change_2d: float = 0.0    # 长期位置2天变化
    long_change_3d: float = 0.0    # 长期位置3天变化
    long_change_5d: float = 0.0    # 长期位置5天变化
    
    # 变化速度比率（核心指标！）
    change_ratio_2d: float = 0.0   # 2天变化比率 = |短期变化| / |长期变化|
    change_ratio_3d: float = 0.0   # 3天变化比率
    change_ratio_5d: float = 0.0   # 5天变化比率
    
    # 是否为洗盘信号
    is_washout: bool = False
    washout_score: float = 0.0
    reasons: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'short_change_2d': round(self.short_change_2d, 2),
            'short_change_3d': round(self.short_change_3d, 2),
            'short_change_5d': round(self.short_change_5d, 2),
            'long_change_2d': round(self.long_change_2d, 2),
            'long_change_3d': round(self.long_change_3d, 2),
            'long_change_5d': round(self.long_change_5d, 2),
            'change_ratio_2d': round(self.change_ratio_2d, 2),
            'change_ratio_3d': round(self.change_ratio_3d, 2),
            'change_ratio_5d': round(self.change_ratio_5d, 2),
            'is_washout': self.is_washout,
            'washout_score': round(self.washout_score, 1),
            'reasons': self.reasons
        }


@dataclass
class HistoryBaseline:
    """历史基准数据"""
    # 洗盘效率基准（指标变化/股价变化的比值）
    washout_efficiency_mean: float = 0.0
    washout_efficiency_std: float = 1.0
    
    # 波动率基准
    volatility_mean: float = 0.0
    volatility_std: float = 1.0
    
    # 成交量基准
    volume_mean: float = 0.0
    volume_std: float = 1.0
    
    # 价格区间基准
    price_high: float = 0.0
    price_low: float = 0.0
    price_mean: float = 0.0
    
    # 指标联动基准（指标变化与股价变化的相关性）
    correlation: float = 0.0
    
    # 有效数据天数
    valid_days: int = 0


@dataclass 
class DailyBehavior:
    """每日行为数据"""
    date_idx: int  # 日期索引
    price_change: float  # 股价涨跌幅(%)
    position_change: float  # 短期位置变化
    volatility: float  # 当日波动率
    volume_ratio: float  # 成交量相对均值的比率
    washout_efficiency: float  # 洗盘效率 = |位置变化| / |股价变化|


class HistoryAnalyzer:
    """
    历史行为分析器
    
    职责：
    1. 计算历史基准（均值、标准差）
    2. 计算当日Z-Score（偏离程度）
    3. 缓存计算结果，优化性能
    """
    
    def __init__(self, lookback_days: int = 20):
        """
        Args:
            lookback_days: 回溯天数，用于计算历史基准
        """
        self.lookback_days = lookback_days
        # 缓存：stock_code -> HistoryBaseline
        self._baseline_cache: Dict[str, HistoryBaseline] = {}
        # 缓存：stock_code -> List[DailyBehavior]
        self._behavior_cache: Dict[str, List[DailyBehavior]] = {}
    
    def analyze_history(
        self,
        stock_code: str,
        closes: List[float],
        highs: List[float],
        lows: List[float],
        volumes: List[float],
        positions: List[float],  # 每日的短期位置指标
        force_recalc: bool = False
    ) -> HistoryBaseline:
        """
        分析历史数据，建立基准
        
        Args:
            stock_code: 股票代码
            closes: 收盘价序列
            highs: 最高价序列
            lows: 最低价序列
            volumes: 成交量序列
            positions: 短期位置指标序列
            force_recalc: 强制重新计算
            
        Returns:
            HistoryBaseline: 历史基准数据
        """
        # 检查缓存
        if not force_recalc and stock_code in self._baseline_cache:
            return self._baseline_cache[stock_code]
        
        # 数据长度检查
        min_len = min(len(closes), len(highs), len(lows), len(volumes), len(positions))
        if min_len < 5:  # 至少需要5天数据
            return HistoryBaseline(valid_days=0)
        
        # 计算每日行为数据
        behaviors = self._calculate_daily_behaviors(
            closes[:min_len], highs[:min_len], lows[:min_len], 
            volumes[:min_len], positions[:min_len]
        )
        
        if len(behaviors) < 3:
            return HistoryBaseline(valid_days=len(behaviors))
        
        # 缓存行为数据
        self._behavior_cache[stock_code] = behaviors
        
        # 计算基准
        baseline = self._calculate_baseline(behaviors, closes, highs, lows)
        
        # 缓存基准
        self._baseline_cache[stock_code] = baseline
        
        return baseline
    
    def _calculate_daily_behaviors(
        self,
        closes: List[float],
        highs: List[float],
        lows: List[float],
        volumes: List[float],
        positions: List[float]
    ) -> List[DailyBehavior]:
        """计算每日行为数据"""
        behaviors = []
        
        # 计算成交量均值（用于后续比较）
        vol_mean = np.mean(volumes) if volumes else 1.0
        
        for i in range(1, len(closes)):
            # 股价涨跌幅
            price_change = (closes[i] - closes[i-1]) / closes[i-1] * 100 if closes[i-1] != 0 else 0
            
            # 位置变化
            position_change = positions[i] - positions[i-1] if i < len(positions) else 0
            
            # 当日波动率 = (高-低) / 收盘价
            volatility = (highs[i] - lows[i]) / closes[i] * 100 if closes[i] != 0 else 0
            
            # 成交量相对比率
            volume_ratio = volumes[i] / vol_mean if vol_mean != 0 else 1.0
            
            # 洗盘效率 = |位置变化| / |股价变化|
            # 关键：当股价变化很小但位置变化大时，效率高（可能是洗盘）
            if abs(price_change) > 0.1:  # 股价变化至少0.1%才有意义
                washout_efficiency = abs(position_change) / abs(price_change)
            else:
                # 股价几乎没变但位置变了，效率无穷大，取一个大值
                washout_efficiency = abs(position_change) * 10 if abs(position_change) > 1 else 0
            
            behaviors.append(DailyBehavior(
                date_idx=i,
                price_change=price_change,
                position_change=position_change,
                volatility=volatility,
                volume_ratio=volume_ratio,
                washout_efficiency=washout_efficiency
            ))
        
        return behaviors
    
    def _calculate_baseline(
        self,
        behaviors: List[DailyBehavior],
        closes: List[float],
        highs: List[float],
        lows: List[float]
    ) -> HistoryBaseline:
        """根据行为数据计算历史基准"""
        
        # 取最近N天的数据
        recent = behaviors[-self.lookback_days:] if len(behaviors) > self.lookback_days else behaviors
        
        # 洗盘效率基准（过滤极端值）
        efficiencies = [b.washout_efficiency for b in recent if b.washout_efficiency < 100]
        if efficiencies:
            eff_mean = np.mean(efficiencies)
            eff_std = np.std(efficiencies) if len(efficiencies) > 1 else eff_mean * 0.5
        else:
            eff_mean, eff_std = 10.0, 5.0
        
        # 波动率基准
        volatilities = [b.volatility for b in recent]
        vol_mean = np.mean(volatilities) if volatilities else 3.0
        vol_std = np.std(volatilities) if len(volatilities) > 1 else vol_mean * 0.3
        
        # 成交量基准
        volume_ratios = [b.volume_ratio for b in recent]
        volume_mean = np.mean(volume_ratios) if volume_ratios else 1.0
        volume_std = np.std(volume_ratios) if len(volume_ratios) > 1 else 0.3
        
        # 价格区间
        recent_closes = closes[-self.lookback_days:] if len(closes) > self.lookback_days else closes
        price_high = max(recent_closes) if recent_closes else 0
        price_low = min(recent_closes) if recent_closes else 0
        price_mean = np.mean(recent_closes) if recent_closes else 0
        
        # 指标与股价的相关性
        price_changes = [b.price_change for b in recent]
        position_changes = [b.position_change for b in recent]
        if len(price_changes) > 2:
            correlation = np.corrcoef(price_changes, position_changes)[0, 1]
            if np.isnan(correlation):
                correlation = 0.5
        else:
            correlation = 0.5
        
        return HistoryBaseline(
            washout_efficiency_mean=eff_mean,
            washout_efficiency_std=max(eff_std, 1.0),  # 防止标准差为0
            volatility_mean=vol_mean,
            volatility_std=max(vol_std, 0.5),
            volume_mean=volume_mean,
            volume_std=max(volume_std, 0.1),
            price_high=price_high,
            price_low=price_low,
            price_mean=price_mean,
            correlation=correlation,
            valid_days=len(recent)
        )
    
    def calculate_zscore(
        self,
        current_value: float,
        mean: float,
        std: float
    ) -> float:
        """
        计算Z-Score（标准分数）
        
        Z-Score = (当前值 - 均值) / 标准差
        
        含义：
        - Z > 2: 当前值显著高于历史平均（2个标准差以上）
        - Z > 1: 当前值略高于历史平均
        - Z ≈ 0: 当前值接近历史平均
        - Z < -1: 当前值低于历史平均
        """
        if std <= 0:
            return 0.0
        return (current_value - mean) / std
    
    def analyze_current_day(
        self,
        stock_code: str,
        baseline: HistoryBaseline,
        current_price_change: float,
        current_position_change: float,
        current_volatility: float,
        current_volume_ratio: float
    ) -> Dict[str, float]:
        """
        分析当日行为，返回各维度的Z-Score
        
        Returns:
            Dict包含：
            - washout_zscore: 洗盘效率Z分数（正值表示指标跌但股价稳）
            - volatility_zscore: 波动率Z分数（负值表示收敛）
            - volume_zscore: 成交量Z分数（负值表示缩量）
            - is_fake_drop: 是否判定为假跌（洗盘）
            - confidence: 判断置信度
        """
        # 计算当日洗盘效率
        if abs(current_price_change) > 0.1:
            current_efficiency = abs(current_position_change) / abs(current_price_change)
        else:
            current_efficiency = abs(current_position_change) * 10 if abs(current_position_change) > 1 else 0
        
        # 计算各维度Z-Score
        washout_zscore = self.calculate_zscore(
            current_efficiency,
            baseline.washout_efficiency_mean,
            baseline.washout_efficiency_std
        )
        
        volatility_zscore = self.calculate_zscore(
            current_volatility,
            baseline.volatility_mean,
            baseline.volatility_std
        )
        
        volume_zscore = self.calculate_zscore(
            current_volume_ratio,
            baseline.volume_mean,
            baseline.volume_std
        )
        
        # 综合判断是否为假跌（洗盘）
        # 条件：洗盘效率高 + 波动率收敛 + 缩量
        is_fake_drop = False
        confidence = 0.0
        
        # 真跌过滤：股价跌幅超过5%直接判定为真跌
        if current_price_change < -5.0:
            is_fake_drop = False
            confidence = 0.0
        else:
            # 计算洗盘置信度
            # 洗盘效率Z > 1 且 波动率收敛（Z < 0）且 缩量（Z < 0）
            washout_score = max(0, washout_zscore)  # 效率越高越好
            vol_compress_score = max(0, -volatility_zscore)  # 波动率越低越好
            volume_shrink_score = max(0, -volume_zscore)  # 成交量越低越好
            
            # 综合得分
            confidence = (
                washout_score * 0.40 +
                vol_compress_score * 0.30 +
                volume_shrink_score * 0.30
            )
            
            # 判定阈值
            is_fake_drop = confidence > 0.8 or (washout_zscore > 1.5 and current_price_change > -3.0)
        
        return {
            'washout_efficiency': current_efficiency,
            'washout_zscore': washout_zscore,
            'volatility_zscore': volatility_zscore,
            'volume_zscore': volume_zscore,
            'is_fake_drop': is_fake_drop,
            'confidence': confidence,
            'price_change': current_price_change,
            'position_change': current_position_change
        }
    
    def clear_cache(self, stock_code: Optional[str] = None):
        """清除缓存"""
        if stock_code:
            self._baseline_cache.pop(stock_code, None)
            self._behavior_cache.pop(stock_code, None)
        else:
            self._baseline_cache.clear()
            self._behavior_cache.clear()
    
    def get_cached_baseline(self, stock_code: str) -> Optional[HistoryBaseline]:
        """获取缓存的基准数据"""
        return self._baseline_cache.get(stock_code)
    
    def analyze_position_changes(
        self,
        short_positions: List[float],  # 每日短期位置列表（最新的在最后）
        long_positions: List[float],   # 每日长期位置列表
        volumes: List[float],          # 每日成交量列表
        closes: List[float],           # 每日收盘价列表
        bbi_values: Optional[List[float]] = None  # BBI指标值（可选）
    ) -> PositionChangeAnalysis:
        """
        核心方法！分析位置变化（计算密集型）
        
        这不是简单的阈值判断，而是真正的计算：
        1. 计算2/3/5天的短期位置变化
        2. 计算2/3/5天的长期位置变化
        3. 计算变化速度比率
        4. 计算量能变化
        5. 检查BBI支撑
        
        Args:
            short_positions: 短期位置序列（至少需要6个数据点）
            long_positions: 长期位置序列
            volumes: 成交量序列
            closes: 收盘价序列
            bbi_values: BBI指标值序列（可选）
        """
        result = PositionChangeAnalysis()
        reasons = []
        
        # 数据长度检查
        min_len = min(len(short_positions), len(long_positions), len(volumes), len(closes))
        if min_len < 3:
            result.reasons = ["数据不足，无法计算"]
            return result
        
        # ========== 1. 计算位置变化 ==========
        # 2天变化
        if min_len >= 2:
            result.short_change_2d = short_positions[-1] - short_positions[-2]
            result.long_change_2d = long_positions[-1] - long_positions[-2]
        
        # 3天变化
        if min_len >= 3:
            result.short_change_3d = short_positions[-1] - short_positions[-3]
            result.long_change_3d = long_positions[-1] - long_positions[-3]
        
        # 5天变化
        if min_len >= 5:
            result.short_change_5d = short_positions[-1] - short_positions[-5]
            result.long_change_5d = long_positions[-1] - long_positions[-5]
        
        # ========== 2. 计算变化速度比率（核心！）==========
        # 比率 = |短期变化| / |长期变化|
        # 比率 > 2 表示短期下杀快但长期稳定 = 洗盘信号
        
        def calc_ratio(short_chg: float, long_chg: float) -> float:
            """计算变化比率"""
            if abs(long_chg) > 1.0:  # 长期有变化
                return abs(short_chg) / abs(long_chg)
            elif abs(short_chg) > 5.0:  # 长期几乎没变，短期变了很多
                return abs(short_chg)  # 返回短期变化量本身
            else:
                return 1.0  # 都没怎么变
        
        result.change_ratio_2d = calc_ratio(result.short_change_2d, result.long_change_2d)
        result.change_ratio_3d = calc_ratio(result.short_change_3d, result.long_change_3d)
        result.change_ratio_5d = calc_ratio(result.short_change_5d, result.long_change_5d)
        
        # ========== 3. 计算量能变化 ==========
        vol_avg_5d = np.mean(volumes[-5:]) if min_len >= 5 else np.mean(volumes)
        vol_today = volumes[-1]
        vol_ratio = vol_today / vol_avg_5d if vol_avg_5d > 0 else 1.0
        is_volume_shrink = vol_ratio < 0.8  # 缩量
        
        # ========== 4. 检查BBI支撑（可选）==========
        bbi_support = True  # 默认有支撑
        if bbi_values and len(bbi_values) >= 1:
            current_close = closes[-1]
            current_bbi = bbi_values[-1]
            bbi_support = current_close >= current_bbi * 0.98  # 允许2%的误差
        
        # ========== 5. 综合判断洗盘信号 ==========
        washout_score = 0.0
        
        # 核心条件：短期下杀快，长期稳定
        # 用2天、3天、5天的变化比率来判断
        
        # 2天变化分析
        if result.short_change_2d < -20:  # 短期2天跌了20以上
            if result.change_ratio_2d >= 2.5:
                washout_score += 35
                reasons.append(f"2天短期跌{result.short_change_2d:.0f}，长期仅跌{result.long_change_2d:.0f}，比率{result.change_ratio_2d:.1f}")
            elif result.change_ratio_2d >= 1.5:
                washout_score += 20
                reasons.append(f"2天变化比率{result.change_ratio_2d:.1f}")
        
        # 3天变化分析
        if result.short_change_3d < -30:  # 短期3天跌了30以上
            if result.change_ratio_3d >= 2.0:
                washout_score += 25
                reasons.append(f"3天短期跌{result.short_change_3d:.0f}，长期仅跌{result.long_change_3d:.0f}")
            elif result.change_ratio_3d >= 1.5:
                washout_score += 15
        
        # 5天变化分析（可能数据失真，权重较低）
        if min_len >= 5 and result.short_change_5d < -40:
            if result.change_ratio_5d >= 2.0:
                washout_score += 15
                reasons.append(f"5天短期跌{result.short_change_5d:.0f}，长期仅跌{result.long_change_5d:.0f}")
        
        # 量能配合加分
        if is_volume_shrink and washout_score > 0:
            washout_score += 15
            reasons.append(f"量能萎缩至{vol_ratio*100:.0f}%")
        
        # BBI支撑加分
        if bbi_support and washout_score > 0:
            washout_score += 10
            reasons.append("BBI支撑有效")
        
        # ========== 6. 最终判定 ==========
        result.washout_score = min(100.0, washout_score)
        result.is_washout = washout_score >= 30
        result.reasons = reasons if reasons else ["未检测到明显洗盘信号"]
        
        return result


# 全局单例，避免重复创建
_history_analyzer_instance: Optional[HistoryAnalyzer] = None

def get_history_analyzer(lookback_days: int = 20) -> HistoryAnalyzer:
    """获取历史分析器单例"""
    global _history_analyzer_instance
    if _history_analyzer_instance is None:
        _history_analyzer_instance = HistoryAnalyzer(lookback_days)
    return _history_analyzer_instance
