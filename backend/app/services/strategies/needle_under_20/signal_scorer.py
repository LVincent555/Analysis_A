"""
九维信号评分引擎
Signal Scorer - 9-Dimension Scoring Engine

核心理念：基于历史数据判断“真跌”vs“假跌”，而不是简单阈值筛选

评分维度：
1. 洗盘检测 (+30) - 核心！基于历史数据的异常检测
2. 排名逆势跃升 (+15)
3. 布林中轨支撑 (+12)
4. 极度缩量 (+10)
5. KDJ共振超卖 (+10)
6. 独立妖股 (+8)
7. ADX趋势有效 (+8)
8. 下影线支撑 (+6)
9. MACD金叉预备 (+5)
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from .config import NEEDLE_UNDER_20_CONFIG, SCORING_WEIGHTS, PATTERN_BONUS, PATTERN_NAMES
from .washout_detector import WashoutDetector, WashoutResult, DropType, get_washout_detector


@dataclass
class ScoreResult:
    """评分结果"""
    total_score: int                    # 总分
    pattern: str                        # 形态类型
    pattern_name: str                   # 形态中文名
    score_details: Dict[str, int]       # 各维度得分详情
    labels: List[str]                   # 特征标签
    signal_level: str                   # 信号强度：strong/normal/weak/ignore
    washout_result: Optional[Dict] = None  # 洗盘检测结果
    
    def to_dict(self) -> dict:
        result = {
            'total_score': self.total_score,
            'pattern': self.pattern,
            'pattern_name': self.pattern_name,
            'score_details': self.score_details,
            'labels': self.labels,
            'signal_level': self.signal_level,
        }
        if self.washout_result:
            result['washout_analysis'] = self.washout_result
        return result


class SignalScorer:
    """
    九维信号评分引擎
    
    核心：基于历史数据判断是否为洗盘（假跌）
    而不是简单的阈值筛选
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or NEEDLE_UNDER_20_CONFIG
        self.washout_detector = get_washout_detector()
    
    def calculate_score(
        self,
        pattern: str,
        indicators: Dict[str, Any]
    ) -> ScoreResult:
        """
        计算综合评分
        
        Args:
            pattern: 形态类型
            indicators: 指标数据字典，包含：
                - rank_change: 排名变化
                - price_change: 涨跌幅
                - boll_bias: 布林乖离率
                - turnover: 换手率
                - turnover_ratio: 换手率相对比
                - kdj_k: KDJ的K值
                - correlation: 与大盘相关性
                - adx: ADX值
                - obv_divergence: OBV是否底背离
                - shadow_ratio: 下影线比例
                - macd_ready: MACD是否金叉预备
                - is_single_day: 是否单日急跌
                - next_day_up: 次日是否高开
                
        Returns:
            ScoreResult 评分结果
        """
        score_details = {}
        labels = []
        total_score = 0
        
        # 1. 排名逆势跃升 (+15)
        rank_score = self._score_rank_contrarian(indicators)
        if rank_score > 0:
            score_details['排名逆势跃升'] = rank_score
            total_score += rank_score
            if rank_score >= 10:
                labels.append('排名逆袭')
        
        # 2. 布林中轨支撑 (+12)
        boll_score = self._score_boll_support(indicators)
        if boll_score > 0:
            score_details['布林中轨支撑'] = boll_score
            total_score += boll_score
            if boll_score >= 10:
                labels.append('布林支撑')
        
        # 3. 极度缩量 (+10)
        volume_score = self._score_volume_shrink(indicators)
        if volume_score > 0:
            score_details['极度缩量'] = volume_score
            total_score += volume_score
            if volume_score >= 7:
                labels.append('极度缩量')
        
        # 3.5 洗盘效率 (+12) - 股价跌幅小但指标跌幅大
        washout_score = self._score_washout_efficiency(indicators)
        if washout_score > 0:
            score_details['洗盘效率'] = washout_score
            total_score += washout_score
            if washout_score >= 8:
                labels.append('高效洗盘')
        
        # 4. KDJ共振超卖 (+10)
        kdj_score = self._score_kdj_resonance(indicators)
        if kdj_score > 0:
            score_details['KDJ共振超卖'] = kdj_score
            total_score += kdj_score
            if kdj_score >= 7:
                labels.append('KDJ共振')
        
        # 5. 独立妖股 (+8)
        independent_score = self._score_independent_stock(indicators)
        if independent_score > 0:
            score_details['独立妖股'] = independent_score
            total_score += independent_score
            if independent_score >= 6:
                labels.append('独立妖股')
        
        # 6. ADX趋势有效 (+8)
        adx_score = self._score_adx_trend(indicators)
        if adx_score > 0:
            score_details['ADX趋势有效'] = adx_score
            total_score += adx_score
            if adx_score >= 6:
                labels.append('趋势有效')
        
        # 7. OBV底背离 (+8)
        obv_score = self._score_obv_divergence(indicators)
        if obv_score > 0:
            score_details['OBV底背离'] = obv_score
            total_score += obv_score
            if obv_score >= 6:
                labels.append('OBV背离')
        
        # 8. 下影线支撑 (+6)
        shadow_score = self._score_shadow_support(indicators)
        if shadow_score > 0:
            score_details['下影线支撑'] = shadow_score
            total_score += shadow_score
            if shadow_score >= 4:
                labels.append('下影线')
        
        # 9. MACD金叉预备 (+5)
        macd_score = self._score_macd_ready(indicators)
        if macd_score > 0:
            score_details['MACD金叉预备'] = macd_score
            total_score += macd_score
            if macd_score >= 4:
                labels.append('MACD预备')
        
        # 形态加分
        pattern_score = self._score_pattern_bonus(pattern, indicators)
        if pattern_score > 0:
            score_details['形态加分'] = pattern_score
            total_score += pattern_score
        
        # 添加形态标签
        pattern_name = PATTERN_NAMES.get(pattern, '未知形态')
        if pattern in ['sky_refuel', 'double_bottom']:
            labels.insert(0, pattern_name)  # 形态标签放在最前面
        
        # 判断信号强度
        signal_level = self._determine_signal_level(total_score)
        
        return ScoreResult(
            total_score=total_score,
            pattern=pattern,
            pattern_name=pattern_name,
            score_details=score_details,
            labels=labels,
            signal_level=signal_level
        )
    
    def _score_rank_contrarian(self, indicators: Dict) -> int:
        """评分：排名逆势跃升"""
        rank_change = indicators.get('rank_change', 0)
        price_change = indicators.get('price_change', 0)
        
        # 股价跌但排名进步
        if price_change < 0 and rank_change < self.config['RANK_DELTA_THRESHOLD']:
            if rank_change < -1000:
                return 15
            elif rank_change < -500:
                return 10
        elif rank_change < -300:
            return 5
        
        return 0
    
    def _score_boll_support(self, indicators: Dict) -> int:
        """评分：布林中轨支撑"""
        boll_bias = indicators.get('boll_bias', 0)
        
        bias_min = self.config['BOLL_BIAS_MIN']
        bias_max = self.config['BOLL_BIAS_MAX']
        
        if bias_min <= boll_bias <= bias_max:
            return 12  # 在支撑区
        elif boll_bias < bias_max and boll_bias >= -10:
            return 6   # 接近支撑区
        
        return 0
    
    def _score_volume_shrink(self, indicators: Dict) -> int:
        """评分：极度缩量"""
        turnover = indicators.get('turnover', 100)
        turnover_ratio = indicators.get('turnover_ratio', 1.0)
        
        limit = self.config['TURNOVER_LIMIT']
        
        if turnover < 3.0 and turnover_ratio < 0.7:
            return 10  # 极度缩量
        elif turnover < limit and turnover_ratio < 0.85:
            return 7   # 明显缩量
        elif turnover < 7.0 and turnover_ratio < 1.0:
            return 4   # 轻微缩量
        
        return 0
    
    def _score_washout_efficiency(self, indicators: Dict) -> int:
        """
        评分：洗盘效率（基于简单阈值，作为备用）
        
        注意：这是简化版，主要评分应使用 score_with_history_analysis
        """
        price_change = indicators.get('price_change', 0)
        position_change = indicators.get('position_change', 0)
        
        # 真跌过滤：股价跌幅超过5%
        if price_change < -5.0:
            return 0
        
        # 简单的效率计算
        if abs(price_change) > 0.1:
            efficiency = abs(position_change) / abs(price_change)
        else:
            efficiency = abs(position_change) if position_change else 0
        
        # 效率越高越可能是洗盘
        if efficiency >= 20:
            return 12
        elif efficiency >= 15:
            return 8
        elif efficiency >= 10:
            return 5
        elif efficiency >= 5:
            return 3
        
        return 0
    
    def score_with_history_analysis(
        self,
        stock_code: str,
        pattern: str,
        indicators: Dict[str, Any],
        closes: List[float],
        highs: List[float],
        lows: List[float],
        volumes: List[float]
    ) -> ScoreResult:
        """
        基于历史数据的综合评分（核心方法！）
        
        与 calculate_score 的区别：
        - 这个方法使用 WashoutDetector 进行基于历史数据的异常检测
        - 不是简单的阈值判断，而是判断当前行为是否偏离历史规律
        
        Args:
            stock_code: 股票代码
            pattern: 形态类型
            indicators: 指标数据
            closes: 收盘价历史数据
            highs: 最高价历史数据
            lows: 最低价历史数据
            volumes: 成交量历史数据
        """
        score_details = {}
        labels = []
        total_score = 0
        washout_dict = None
        
        # ========== 核心：洗盘检测（基于历史数据）==========
        washout_result = self.washout_detector.detect(
            stock_code, closes, highs, lows, volumes
        )
        washout_dict = washout_result.to_dict()
        
        # 根据洗盘检测结果评分
        if washout_result.drop_type == DropType.REAL_DROP:
            # 真跌：直接返回低分
            return ScoreResult(
                total_score=0,
                pattern=pattern,
                pattern_name=PATTERN_NAMES.get(pattern, '真跌'),
                score_details={'判定': '真跌，剔除'},
                labels=['真跌'],
                signal_level='ignore',
                washout_result=washout_dict
            )
        
        if washout_result.drop_type == DropType.FAKE_DROP:
            # 假跌（洗盘）：核心加分
            washout_score = int(washout_result.washout_score * 0.3)  # 最高30分
            score_details['洗盘检测'] = washout_score
            total_score += washout_score
            labels.append('假跌洗盘')
            
            # 添加细分得分
            if washout_result.efficiency_score > 15:
                labels.append(f'Z={washout_result.washout_zscore:.1f}')
        
        elif washout_result.drop_type == DropType.UNCERTAIN:
            # 不确定：给予基础分
            score_details['洗盘检测'] = 5
            total_score += 5
        
        # ========== 其他维度评分（与原来相同）==========
        
        # 排名逆势跃升
        rank_score = self._score_rank_contrarian(indicators)
        if rank_score > 0:
            score_details['排名逆势跃升'] = rank_score
            total_score += rank_score
            if rank_score >= 10:
                labels.append('排名逆袭')
        
        # 布林中轨支撑
        boll_score = self._score_boll_support(indicators)
        if boll_score > 0:
            score_details['布林中轨支撑'] = boll_score
            total_score += boll_score
            if boll_score >= 10:
                labels.append('布林支撑')
        
        # 极度缩量（使用洗盘检测结果中的缩量得分）
        volume_score = int(washout_result.volume_score * 0.4)  # 最高10分
        if volume_score > 0:
            score_details['缩量程度'] = volume_score
            total_score += volume_score
            if volume_score >= 7:
                labels.append('极度缩量')
        
        # KDJ共振超卖
        kdj_score = self._score_kdj_resonance(indicators)
        if kdj_score > 0:
            score_details['KDJ共振超卖'] = kdj_score
            total_score += kdj_score
            if kdj_score >= 7:
                labels.append('KDJ共振')
        
        # 独立妖股
        independent_score = self._score_independent_stock(indicators)
        if independent_score > 0:
            score_details['独立妖股'] = independent_score
            total_score += independent_score
            if independent_score >= 6:
                labels.append('独立妖股')
        
        # ADX趋势有效
        adx_score = self._score_adx_trend(indicators)
        if adx_score > 0:
            score_details['ADX趋势有效'] = adx_score
            total_score += adx_score
        
        # 下影线支撑
        shadow_score = self._score_shadow_support(indicators)
        if shadow_score > 0:
            score_details['下影线支撑'] = shadow_score
            total_score += shadow_score
            if shadow_score >= 4:
                labels.append('下影线')
        
        # MACD金叉预备
        macd_score = self._score_macd_ready(indicators)
        if macd_score > 0:
            score_details['MACD金叉预备'] = macd_score
            total_score += macd_score
        
        # 形态加分
        pattern_score = self._score_pattern_bonus(pattern, indicators)
        if pattern_score > 0:
            score_details['形态加分'] = pattern_score
            total_score += pattern_score
        
        # 添加形态标签
        pattern_name = PATTERN_NAMES.get(pattern, '未知形态')
        if pattern in ['sky_refuel', 'double_bottom']:
            labels.insert(0, pattern_name)
        
        # 判断信号强度
        signal_level = self._determine_signal_level(total_score)
        
        return ScoreResult(
            total_score=total_score,
            pattern=pattern,
            pattern_name=pattern_name,
            score_details=score_details,
            labels=labels,
            signal_level=signal_level,
            washout_result=washout_dict
        )
    
    def _score_kdj_resonance(self, indicators: Dict) -> int:
        """评分：KDJ共振超卖"""
        kdj_k = indicators.get('kdj_k', 50)
        
        if kdj_k <= self.config['KDJ_LIMIT']:
            if kdj_k <= 10:
                return 10  # 极度超卖
            else:
                return 7
        elif kdj_k <= 30:
            return 4
        
        return 0
    
    def _score_independent_stock(self, indicators: Dict) -> int:
        """评分：独立妖股"""
        correlation = indicators.get('correlation', 1.0)
        
        if correlation <= self.config['CORRELATION_LIMIT']:
            if correlation <= 0.1:
                return 8  # 高度独立
            else:
                return 5
        
        return 0
    
    def _score_adx_trend(self, indicators: Dict) -> int:
        """评分：ADX趋势有效"""
        adx = indicators.get('adx', 0)
        
        if adx >= self.config['ADX_TREND_MIN']:
            if adx >= 35:
                return 8  # 强趋势
            else:
                return 5
        
        return 0
    
    def _score_obv_divergence(self, indicators: Dict) -> int:
        """评分：OBV底背离"""
        obv_divergence = indicators.get('obv_divergence', False)
        
        if obv_divergence:
            return 8
        
        return 0
    
    def _score_shadow_support(self, indicators: Dict) -> int:
        """评分：下影线支撑"""
        shadow_ratio = indicators.get('shadow_ratio', 0)
        
        if shadow_ratio >= 0.6:
            return 6  # 长下影线
        elif shadow_ratio >= 0.4:
            return 4
        elif shadow_ratio >= 0.2:
            return 2
        
        return 0
    
    def _score_macd_ready(self, indicators: Dict) -> int:
        """评分：MACD金叉预备"""
        macd_ready = indicators.get('macd_ready', False)
        
        if macd_ready:
            return 5
        
        return 0
    
    def _score_pattern_bonus(self, pattern: str, indicators: Dict) -> int:
        """形态加分"""
        bonus = 0
        
        # 形态加分
        if pattern == 'sky_refuel':
            bonus += PATTERN_BONUS['sky_refuel'][0]
        elif pattern == 'double_bottom':
            bonus += PATTERN_BONUS['double_bottom'][0]
        
        # 单日急跌加分
        if indicators.get('is_single_day', False):
            bonus += PATTERN_BONUS['single_day_drop'][0]
        
        # 次日高开加分
        if indicators.get('next_day_up', False):
            bonus += PATTERN_BONUS['next_day_confirm'][0]
        
        return bonus
    
    def _determine_signal_level(self, total_score: int) -> str:
        """判断信号强度"""
        if total_score >= self.config['SCORE_STRONG']:
            return 'strong'     # 强烈信号
        elif total_score >= self.config['SCORE_NORMAL']:
            return 'normal'     # 普通信号
        elif total_score >= self.config['SCORE_WEAK']:
            return 'weak'       # 弱信号
        else:
            return 'ignore'     # 忽略
