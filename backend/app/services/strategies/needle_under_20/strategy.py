"""
单针下二十策略主入口
Needle Under 20 Strategy Main Entry

整合所有组件，提供统一的分析接口
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import date

from .config import NEEDLE_UNDER_20_CONFIG
from .pattern_recognizer import PatternRecognizer, PatternResult
from .signal_scorer import SignalScorer, ScoreResult
from ..common.position_calculator import PositionCalculator
from ..common.volatility_engine import VolatilityEngine
from ..common.indicator_calculator import IndicatorCalculator


@dataclass
class AnalysisResult:
    """分析结果"""
    stock_code: str
    stock_name: str
    signal_date: str
    is_triggered: bool              # 是否触发信号
    total_score: int                # 总分
    signal_level: str               # 信号强度
    pattern: str                    # 形态类型
    pattern_name: str               # 形态中文名
    labels: List[str]               # 特征标签
    positions: Dict                 # 位置指标
    score_details: Dict[str, int]   # 评分详情
    context_valid: bool             # 语境是否有效
    washout_analysis: Optional[Dict] = None  # 洗盘分析结果（基于历史数据）
    
    def to_dict(self) -> dict:
        result = {
            'stock_code': self.stock_code,
            'stock_name': self.stock_name,
            'signal_date': self.signal_date,
            'is_triggered': self.is_triggered,
            'total_score': self.total_score,
            'signal_level': self.signal_level,
            'pattern': self.pattern,
            'pattern_name': self.pattern_name,
            'labels': self.labels,
            'positions': self.positions,
            'score_details': self.score_details,
            'context_valid': self.context_valid,
        }
        if self.washout_analysis:
            result['washout_analysis'] = self.washout_analysis
        return result


class NeedleUnder20Strategy:
    """
    单针下二十策略
    
    主要入口类，整合所有组件进行综合分析
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or NEEDLE_UNDER_20_CONFIG
        
        # 初始化各组件
        self.pattern_recognizer = PatternRecognizer(self.config)
        self.signal_scorer = SignalScorer(self.config)
        self.volatility_engine = VolatilityEngine(
            avg_period=self.config['VOL_WINDOW']
        )
        self.indicator_calculator = IndicatorCalculator()
    
    def analyze(
        self,
        stock_code: str,
        stock_name: str,
        signal_date: str,
        closes: List[float],
        highs: List[float],
        lows: List[float],
        opens: List[float],
        volumes: List[float],
        turnovers: List[float],
        ranks: Optional[List[int]] = None,
        extra_indicators: Optional[Dict] = None
    ) -> AnalysisResult:
        """
        分析单只股票
        
        Args:
            stock_code: 股票代码
            stock_name: 股票名称
            signal_date: 信号日期
            closes: 收盘价序列
            highs: 最高价序列
            lows: 最低价序列
            opens: 开盘价序列
            volumes: 成交量序列
            turnovers: 换手率序列
            ranks: 排名序列（可选）
            extra_indicators: 额外指标（KDJ、ADX、相关性等）
            
        Returns:
            AnalysisResult 分析结果
        """
        # 1. 形态识别（获取当前位置）
        pattern_result = self.pattern_recognizer.recognize(
            closes, highs, lows
        )
        
        # ========== 核心改进！计算密集型洗盘检测 ==========
        # 不再简单判断"当前位置<阈值"
        # 而是计算2/3/5天的位置变化，检测洗盘信号
        from .washout_detector import get_washout_detector
        washout_detector = get_washout_detector()
        
        washout_result = washout_detector.detect(
            stock_code=stock_code,
            closes=closes,
            highs=highs,
            lows=lows,
            volumes=volumes
        )
        
        # 触发条件：
        # 1. 传统条件：当前位置<阈值
        # 2. 新条件：检测到洗盘信号（短期跌快+长期跌慢）
        is_washout_signal = washout_result.is_washout if hasattr(washout_result, 'is_washout') else (
            washout_result.washout_score >= 30 or washout_result.change_ratio_2d >= 2.0
        )
        
        if not pattern_result.is_triggered and not is_washout_signal:
            return AnalysisResult(
                stock_code=stock_code,
                stock_name=stock_name,
                signal_date=signal_date,
                is_triggered=False,
                total_score=0,
                signal_level='ignore',
                pattern=None,
                pattern_name='未触发',
                labels=[],
                positions=pattern_result.positions.to_dict(),
                score_details={
                    '位置变化分析': {
                        '短期2天变化': washout_result.short_change_2d,
                        '长期2天变化': washout_result.long_change_2d,
                        '变化比率': washout_result.change_ratio_2d
                    }
                },
                context_valid=True,
                washout_analysis=washout_result.to_dict()
            )
        
        # 2. 语境检查
        context = self.pattern_recognizer.check_context(closes, highs, lows)
        
        # 3. 收集指标数据
        indicators = self._collect_indicators(
            closes, highs, lows, opens, volumes, turnovers, ranks, extra_indicators
        )
        
        # 添加形态相关信息
        indicators['is_single_day'] = pattern_result.is_single_day
        
        # 4. 基于历史数据的评分（核心改进！）
        # 使用新的 score_with_history_analysis 方法，基于历史数据判断真跌/假跌
        score_result = self.signal_scorer.score_with_history_analysis(
            stock_code=stock_code,
            pattern=pattern_result.pattern,
            indicators=indicators,
            closes=closes,
            highs=highs,
            lows=lows,
            volumes=volumes
        )
        
        # 如果被判定为真跌，直接返回不触发
        if score_result.signal_level == 'ignore' and '真跌' in score_result.labels:
            return AnalysisResult(
                stock_code=stock_code,
                stock_name=stock_name,
                signal_date=signal_date,
                is_triggered=False,
                total_score=0,
                signal_level='ignore',
                pattern=None,
                pattern_name='真跌剔除',
                labels=['真跌'],
                positions=pattern_result.positions.to_dict(),
                score_details=score_result.score_details,
                context_valid=False,
                washout_analysis=score_result.washout_result
            )
        
        return AnalysisResult(
            stock_code=stock_code,
            stock_name=stock_name,
            signal_date=signal_date,
            is_triggered=True,
            total_score=score_result.total_score,
            signal_level=score_result.signal_level,
            pattern=score_result.pattern,
            pattern_name=score_result.pattern_name,
            labels=score_result.labels,
            positions=pattern_result.positions.to_dict(),
            score_details=score_result.score_details,
            context_valid=context['is_valid'],
            washout_analysis=score_result.washout_result
        )
    
    def _collect_indicators(
        self,
        closes: List[float],
        highs: List[float],
        lows: List[float],
        opens: List[float],
        volumes: List[float],
        turnovers: List[float],
        ranks: Optional[List[int]] = None,
        extra_indicators: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        收集各项指标
        
        Args:
            各种价格和量数据
            
        Returns:
            指标数据字典
        """
        indicators = {}
        
        # 价格变化（百分比）
        if len(closes) >= 2:
            indicators['price_change'] = (closes[-1] - closes[-2]) / closes[-2] * 100
        else:
            indicators['price_change'] = 0
        
        # 位置指标变化（短期位置的变化）
        # 用于判断"缩量洗盘"：股价跌幅小但指标跌幅大
        if len(closes) >= 4 and len(lows) >= 4:  # 需要至少4天数据计算两天的短期位置
            # 今天的短期位置
            today_pos = self.pattern_recognizer.position_calculator.calculate_position(
                closes, highs, lows, self.config['N1_SHORT']
            )
            # 昨天的短期位置（用前N-1天数据）
            yesterday_pos = self.pattern_recognizer.position_calculator.calculate_position(
                closes[:-1], highs[:-1], lows[:-1], self.config['N1_SHORT']
            )
            indicators['position_change'] = today_pos - yesterday_pos  # 负值表示下跌
            indicators['current_position'] = today_pos
        else:
            indicators['position_change'] = 0
            indicators['current_position'] = 50
        
        # 排名变化
        if ranks and len(ranks) >= 2:
            indicators['rank_change'] = ranks[-1] - ranks[-2]
        else:
            indicators['rank_change'] = 0
        
        # 布林乖离率
        boll_result = self.indicator_calculator.analyze_boll_support(closes, lows[-1] if lows else 0)
        indicators['boll_bias'] = boll_result['bias']
        
        # 换手率
        if turnovers:
            indicators['turnover'] = turnovers[-1]
            indicators['turnover_ratio'] = self.indicator_calculator.calculate_turnover_ratio(turnovers)
        else:
            indicators['turnover'] = 0
            indicators['turnover_ratio'] = 1.0
        
        # 下影线
        if opens and closes and highs and lows:
            shadow_result = self.indicator_calculator.analyze_shadow(
                opens[-1], closes[-1], highs[-1], lows[-1]
            )
            indicators['shadow_ratio'] = shadow_result['shadow_ratio']
        else:
            indicators['shadow_ratio'] = 0
        
        # 波动率
        vol_result = self.volatility_engine.analyze(highs, lows, closes)
        indicators['volatility_compression'] = vol_result.compression_ratio
        
        # 额外指标（KDJ、ADX、相关性等）
        if extra_indicators:
            indicators.update(extra_indicators)
        else:
            # 默认值
            indicators.setdefault('kdj_k', 50)
            indicators.setdefault('correlation', 0.5)
            indicators.setdefault('adx', 20)
            indicators.setdefault('obv_divergence', False)
            indicators.setdefault('macd_ready', False)
        
        return indicators
    
    def batch_analyze(
        self,
        stocks_data: List[Dict]
    ) -> List[AnalysisResult]:
        """
        批量分析多只股票
        
        Args:
            stocks_data: 股票数据列表，每个元素包含单只股票的所有数据
            
        Returns:
            分析结果列表（按评分降序排列）
        """
        results = []
        
        for data in stocks_data:
            result = self.analyze(
                stock_code=data['stock_code'],
                stock_name=data.get('stock_name', ''),
                signal_date=data.get('signal_date', ''),
                closes=data['closes'],
                highs=data['highs'],
                lows=data['lows'],
                opens=data.get('opens', []),
                volumes=data.get('volumes', []),
                turnovers=data.get('turnovers', []),
                ranks=data.get('ranks'),
                extra_indicators=data.get('extra_indicators')
            )
            
            # 只保留触发的信号
            if result.is_triggered and result.signal_level != 'ignore':
                results.append(result)
        
        # 按评分降序排列
        results.sort(key=lambda x: x.total_score, reverse=True)
        
        return results
    
    def get_signal_for_main_system(
        self,
        result: AnalysisResult
    ) -> Optional[Dict]:
        """
        获取用于主信号系统的信号数据
        
        Args:
            result: 分析结果
            
        Returns:
            主信号系统格式的数据，或None（不满足条件）
        """
        if not result.is_triggered or result.signal_level == 'ignore':
            return None
        
        # 只有达到普通信号以上才输出到主系统
        if result.total_score < self.config['SCORE_NORMAL']:
            return None
        
        return {
            'signal_type': '单针下二十',
            'score': result.total_score,
            'pattern': result.pattern_name,
            'labels': result.labels,
            'signal_level': result.signal_level,
        }
