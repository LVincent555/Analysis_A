"""
多榜单信号计算器
计算股票的多维度信号强度
"""
import logging
from typing import List, Dict, Optional, Set
from datetime import date, timedelta
from collections import defaultdict

from ..db_models import DailyStockData
from .memory_cache import memory_cache
from .hot_spots_cache import HotSpotsCache

logger = logging.getLogger(__name__)


class SignalThresholds:
    """信号阈值配置（可调节）"""
    def __init__(
        self,
        hot_list_mode: str = "instant",  # instant=即时龙头榜, frequent=高频热点榜
        hot_list_top: int = 100,
        hot_list_top2: int = 500,
        rank_jump_min: int = 1000,  # 排名跳变最小阈值
        rank_jump_large: int = 1500,  # 排名大幅跳变（1.5倍）
        steady_rise_days_min: int = 3,
        steady_rise_days_large: int = 5,
        price_surge_min: float = 5.0,
        volume_surge_min: float = 10.0,
        volatility_surge_min: float = 10.0,  # 波动率上升阈值（百分比变化：10%）
        volatility_surge_large: float = 100.0  # 波动率大幅上升（百分比变化：100%）
    ):
        self.hot_list_mode = hot_list_mode
        self.hot_list_top = hot_list_top
        self.hot_list_top2 = hot_list_top2
        self.rank_jump_min = rank_jump_min
        self.rank_jump_large = rank_jump_large
        self.steady_rise_days_min = steady_rise_days_min
        self.steady_rise_days_large = steady_rise_days_large
        self.price_surge_min = price_surge_min
        self.volume_surge_min = volume_surge_min
        self.volatility_surge_min = volatility_surge_min
        self.volatility_surge_large = volatility_surge_large


class SignalWeights:
    """信号权重配置（平衡型）"""
    HOT_LIST_WEIGHT = 0.25
    RANK_JUMP_WEIGHT = 0.20
    STEADY_RISE_WEIGHT = 0.20
    PRICE_SURGE_WEIGHT = 0.10
    VOLUME_SURGE_WEIGHT = 0.10
    VOLATILITY_SURGE_WEIGHT = 0.15  # 波动率上升权重


class SignalCalculator:
    """信号计算器"""
    
    def __init__(self, thresholds: Optional[SignalThresholds] = None):
        """
        初始化信号计算器
        
        Args:
            thresholds: 信号阈值配置，默认使用标准阈值
        """
        self.thresholds = thresholds or SignalThresholds()
    
    def calculate_signals(
        self,
        stock_code: str,
        current_date: date,
        current_data: DailyStockData,
        history_days: int = 7
    ) -> Dict:
        """
        计算股票的多榜单信号
        
        Args:
            stock_code: 股票代码
            current_date: 当前日期
            current_data: 当前日期的股票数据
            history_days: 历史追踪天数
        
        Returns:
            信号数据字典
        """
        signals = []
        signal_score = 0.0
        
        # 1. 热点榜信号（根据模式选择）
        if self.thresholds.hot_list_mode == "frequent":
            # 高频热点榜：基于14天聚合数据
            hot_signal = self.calculate_hot_spot_signal(stock_code, current_date.strftime('%Y%m%d'))
        else:
            # 即时龙头榜：基于当日排名
            hot_signal = self._check_hot_list(current_data.rank)
        
        if hot_signal:
            signals.append(hot_signal['label'])
            signal_score += hot_signal['score']
        
        # 2. 排名跳变榜信号
        jump_signal = self._check_rank_jump(stock_code, current_date, current_data.rank)
        if jump_signal:
            signals.append(jump_signal['label'])
            signal_score += jump_signal['score']
        
        # 3. 稳步上升榜信号
        rise_signal = self._check_steady_rise(stock_code, current_date)
        if rise_signal:
            signals.append(rise_signal['label'])
            signal_score += rise_signal['score']
        
        # 4. 涨幅榜信号
        price_signal = self._check_price_surge(current_data.price_change)
        if price_signal:
            signals.append(price_signal['label'])
            signal_score += price_signal['score']
        
        # 5. 成交量榜信号
        volume_signal = self._check_volume_surge(current_data.turnover_rate_percent)
        if volume_signal:
            signals.append(volume_signal['label'])
            signal_score += volume_signal['score']
        
        # 6. 波动率上升信号
        volatility_signal = self._check_volatility_surge(stock_code, current_date, current_data.volatility)
        if volatility_signal:
            signals.append(volatility_signal['label'])
            signal_score += volatility_signal['score']
        
        # 7. 历史信号追踪（过去7天）
        signal_history = self._get_signal_history(
            stock_code, current_date, history_days
        )
        
        return {
            'signals': signals,
            'signal_count': len(signals),
            'signal_strength': min(signal_score, 1.0),  # 最高1.0
            'in_hot_list': hot_signal is not None,
            'in_rank_jump': jump_signal is not None,
            'rank_improvement': jump_signal['improvement'] if jump_signal else None,
            'in_steady_rise': rise_signal is not None,
            'rise_days': rise_signal['days'] if rise_signal else None,
            'in_price_surge': price_signal is not None,
            'in_volume_surge': volume_signal is not None,
            'in_volatility_surge': volatility_signal is not None,
            'signal_history': signal_history
        }
    
    def _check_hot_list(self, rank: int) -> Optional[Dict]:
        """检查热点榜信号（旧方法，已废弃）
        
        注意：此方法基于各模块自身排名判断，不推荐使用
        请使用 calculate_hot_spot_signal 方法替代
        """
        if rank <= self.thresholds.hot_list_top:
            return {
                'label': f'热点榜TOP{self.thresholds.hot_list_top}',
                'score': SignalWeights.HOT_LIST_WEIGHT
            }
        elif rank <= self.thresholds.hot_list_top2:
            return {
                'label': f'热点榜TOP{self.thresholds.hot_list_top2}',
                'score': SignalWeights.HOT_LIST_WEIGHT * 0.5  # 减半
            }
        return None
    
    def calculate_hot_spot_signal(
        self,
        stock_code: str,
        date_str: str
    ) -> Optional[Dict]:
        """基于热点榜缓存计算信号（新方法）
        
        从14天聚合热点榜中查询股票排名和出现次数，返回相应信号
        
        Args:
            stock_code: 股票代码
            date_str: 日期 (YYYYMMDD)
            
        Returns:
            {
                'label': 'TOP100·12次',   # 信号标签（带次数）
                'score': 1.0,             # 信号分数
                'rank': 15,               # 实际排名
                'hit_count': 12           # 出现次数
            }
            或 None（不在热点榜TOP1000中）
        """
        try:
            # 从缓存查询排名和次数
            result = HotSpotsCache.get_rank(stock_code, date_str)
            
            if not result:
                return None
            
            rank, hit_count = result
            
            # 根据排名确定标签和分数
            label = None
            score = 0.0
            
            if rank <= 100:
                label = f"TOP100·{hit_count}次"
                score = SignalWeights.HOT_LIST_WEIGHT * 2.0  # 最高权重
            elif rank <= 200:
                label = f"TOP200·{hit_count}次"
                score = SignalWeights.HOT_LIST_WEIGHT * 1.5
            elif rank <= 400:
                label = f"TOP400·{hit_count}次"
                score = SignalWeights.HOT_LIST_WEIGHT * 1.2
            elif rank <= 600:
                label = f"TOP600·{hit_count}次"
                score = SignalWeights.HOT_LIST_WEIGHT * 1.0
            elif rank <= 800:
                label = f"TOP800·{hit_count}次"
                score = SignalWeights.HOT_LIST_WEIGHT * 0.8
            elif rank <= 1000:
                label = f"TOP1000·{hit_count}次"
                score = SignalWeights.HOT_LIST_WEIGHT * 0.5
            
            # 根据出现次数微调分数（次数越多，热度越高）
            # 14天内出现12次以上视为持续热点，额外加权
            if hit_count >= 12:
                score *= 1.2
            elif hit_count >= 10:
                score *= 1.1
            elif hit_count >= 8:
                score *= 1.05
            
            if label:
                return {
                    'label': label,
                    'score': score,
                    'rank': rank,
                    'hit_count': hit_count
                }
            
            return None
            
        except Exception as e:
            logger.error(f"计算热点榜信号失败 {stock_code} {date_str}: {e}")
            return None
    
    def _check_rank_jump(
        self,
        stock_code: str,
        current_date: date,
        current_rank: int
    ) -> Optional[Dict]:
        """检查排名跳变信号"""
        # 获取前一天的数据
        dates = memory_cache.get_dates_range(10)  # 获取最近10天
        prev_date = None
        for d in dates:
            if d < current_date:
                prev_date = d
                break
        
        if not prev_date:
            return None
        
        prev_data = memory_cache.get_daily_data_by_stock(stock_code, prev_date)
        if not prev_data:
            return None
        
        # 计算排名提升（排名变小 = 提升）
        improvement = prev_data.rank - current_rank
        
        if improvement >= self.thresholds.rank_jump_large:
            return {
                'label': f'大幅跳变↑{improvement}',
                'score': SignalWeights.RANK_JUMP_WEIGHT,
                'improvement': improvement
            }
        elif improvement >= self.thresholds.rank_jump_min:
            return {
                'label': f'跳变↑{improvement}',
                'score': SignalWeights.RANK_JUMP_WEIGHT * 0.6,
                'improvement': improvement
            }
        
        return None
    
    def _check_steady_rise(
        self,
        stock_code: str,
        current_date: date
    ) -> Optional[Dict]:
        """检查稳步上升信号（连续N天排名上升）"""
        dates = memory_cache.get_dates_range(10)  # 最近10天
        dates = [d for d in dates if d <= current_date][:8]  # 取当前日期及之前的7天
        
        if len(dates) < 2:
            return None
        
        # 获取历史排名
        ranks = []
        for d in dates:
            data = memory_cache.get_daily_data_by_stock(stock_code, d)
            if data:
                ranks.append(data.rank)
        
        if len(ranks) < 2:
            return None
        
        # 检查连续上升天数（排名变小 = 上升）
        rise_days = 0
        for i in range(len(ranks) - 1):
            if ranks[i+1] < ranks[i]:  # 后一天排名更小（更好）
                rise_days += 1
            else:
                break
        
        if rise_days >= self.thresholds.steady_rise_days_large:
            return {
                'label': f'持续上升{rise_days}天',
                'score': SignalWeights.STEADY_RISE_WEIGHT,
                'days': rise_days
            }
        elif rise_days >= self.thresholds.steady_rise_days_min:
            return {
                'label': f'上升{rise_days}天',
                'score': SignalWeights.STEADY_RISE_WEIGHT * 0.6,
                'days': rise_days
            }
        
        return None
    
    def _check_price_surge(self, price_change: Optional[float]) -> Optional[Dict]:
        """检查涨幅信号"""
        if price_change is None:
            return None
        
        if price_change >= self.thresholds.price_surge_min:
            return {
                'label': f'涨幅{price_change:.1f}%',
                'score': SignalWeights.PRICE_SURGE_WEIGHT
            }
        
        return None
    
    def _check_volume_surge(
        self,
        turnover_rate: Optional[float]
    ) -> Optional[Dict]:
        """检查成交量信号"""
        if turnover_rate is None:
            return None
        
        if turnover_rate >= self.thresholds.volume_surge_min:
            return {
                'label': f'换手率{turnover_rate:.1f}%',
                'score': SignalWeights.VOLUME_SURGE_WEIGHT
            }
        
        return None
    
    def _check_volatility_surge(
        self,
        stock_code: str,
        current_date: date,
        current_volatility: Optional[float]
    ) -> Optional[Dict]:
        """检查波动率上升信号（相比前一天波动率百分比变化）"""
        if current_volatility is None or current_volatility == 0:
            return None
        
        # 获取前一天的数据
        dates = memory_cache.get_dates_range(10)
        prev_date = None
        for d in dates:
            if d < current_date:
                prev_date = d
                break
        
        if not prev_date:
            return None
        
        prev_data = memory_cache.get_daily_data_by_stock(stock_code, prev_date)
        if not prev_data or prev_data.volatility is None or prev_data.volatility == 0:
            return None
        
        # 计算波动率百分比变化: (current - prev) / prev * 100
        volatility_change_percent = ((current_volatility - prev_data.volatility) / prev_data.volatility) * 100
        
        if volatility_change_percent >= self.thresholds.volatility_surge_large:
            return {
                'label': f'波动率↑{volatility_change_percent:.1f}%',
                'score': SignalWeights.VOLATILITY_SURGE_WEIGHT
            }
        elif volatility_change_percent >= self.thresholds.volatility_surge_min:
            return {
                'label': f'波动率小幅↑{volatility_change_percent:.1f}%',
                'score': SignalWeights.VOLATILITY_SURGE_WEIGHT * 0.6
            }
        
        return None
    
    def _get_signal_history(
        self,
        stock_code: str,
        current_date: date,
        history_days: int
    ) -> Dict:
        """
        获取历史信号追踪（过去N天）
        
        Returns:
            历史信号字典，格式：
            {
                'hot_list': [True, True, False, True, ...],
                'rank_jump': [False, True, False, False, ...],
                'steady_rise': [True, True, True, False, ...],
                'dates': ['20251107', '20251106', ...]
            }
        """
        dates = memory_cache.get_dates_range(history_days + 5)
        dates = [d for d in dates if d <= current_date][:history_days]
        
        hot_list_history = []
        rank_jump_history = []
        steady_rise_history = []
        date_strs = []
        
        for i, d in enumerate(dates):
            data = memory_cache.get_daily_data_by_stock(stock_code, d)
            if not data:
                continue
            
            date_strs.append(d.strftime('%Y%m%d'))
            
            # 热点榜
            hot = data.rank <= self.thresholds.hot_list_top
            hot_list_history.append(hot)
            
            # 跳变榜（需要前一天数据）
            if i < len(dates) - 1:
                prev_data = memory_cache.get_daily_data_by_stock(stock_code, dates[i+1])
                if prev_data:
                    improvement = prev_data.rank - data.rank
                    rank_jump_history.append(improvement >= self.thresholds.rank_jump_min)
                else:
                    rank_jump_history.append(False)
            else:
                rank_jump_history.append(False)
            
            # 稳步上升（简化：只看是否比前一天排名更好）
            if i < len(dates) - 1:
                prev_data = memory_cache.get_daily_data_by_stock(stock_code, dates[i+1])
                if prev_data:
                    steady_rise_history.append(data.rank < prev_data.rank)
                else:
                    steady_rise_history.append(False)
            else:
                steady_rise_history.append(False)
        
        return {
            'hot_list': hot_list_history,
            'rank_jump': rank_jump_history,
            'steady_rise': steady_rise_history,
            'dates': date_strs
        }
