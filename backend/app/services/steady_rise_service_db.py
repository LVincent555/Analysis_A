"""
稳步上升服务 - Numpy缓存版

v0.5.0: 使用统一缓存系统
"""
from typing import List, Optional
import statistics
import logging
from datetime import datetime

from .numpy_cache_middleware import numpy_cache
from ..core.caching import cache  # v0.5.0: 统一缓存
from ..models.stock import SteadyRiseResult, SteadyRiseStock
from ..utils.board_filter import should_filter_stock

logger = logging.getLogger(__name__)

# v0.5.0: 缓存TTL改为25小时
STEADY_RISE_CACHE_TTL = 90000


class SteadyRiseServiceDB:
    """稳步上升服务（Numpy缓存版）"""
    
    def analyze_steady_rise(
        self,
        period: int = 3,
        board_type: str = 'main',
        min_rank_improvement: int = 100,
        sigma_multiplier: float = 1.0,
        target_date: Optional[str] = None
    ) -> SteadyRiseResult:
        """
        稳步上升分析
        
        ✅ 使用numpy缓存 + api_cache二级缓存
        
        Args:
            period: 分析周期
            board_type: 板块类型 ('all': 全部, 'main': 主板, 'bjs': 北交所)
            min_rank_improvement: 最小排名提升
            sigma_multiplier: σ倍数
            target_date: 指定日期 (YYYYMMDD格式)，不传则使用最新日期
        
        Returns:
            稳步上升结果
        """
        # 获取目标日期
        if target_date:
            target_date_obj = datetime.strptime(target_date, '%Y%m%d').date()
        else:
            target_date_obj = numpy_cache.get_latest_date()
        
        if not target_date_obj:
            return self._empty_result(period)
        
        date_str = target_date_obj.strftime('%Y%m%d')
        
        # v0.5.0: 使用统一缓存系统 (直接缓存对象，避免反序列化开销)
        cache_key = f"steady_rise_{period}_{board_type}_{min_rank_improvement}_{sigma_multiplier}_{date_str}"
        cached = cache.get_api_cache("steady_rise", cache_key)
        if cached:
            logger.info(f"✨ 缓存命中: {cache_key}")
            return cached  # 直接返回对象
        
        # ========== 使用numpy缓存计算 ==========
        # 1. 获取最近N天的日期
        all_dates = numpy_cache.get_dates_range(period + 5)  # 多取几天以防万一
        target_dates = [d for d in all_dates if d <= target_date_obj][:period]
        
        if len(target_dates) < period:
            return self._empty_result(period)
        
        target_dates.reverse()  # 从旧到新排序
        date_strs = [d.strftime('%Y%m%d') for d in target_dates]
        
        # 2. 从numpy缓存获取数据并按股票分组
        stock_data = {}  # {stock_code: {name, industry, ranks, latest_indicators}}
        
        for check_date in target_dates:
            # 获取当天所有股票数据
            all_daily = numpy_cache.get_all_by_date(check_date)
            for daily in all_daily:
                stock_code = daily.get('stock_code')
                if not stock_code:
                    continue
                
                if stock_code not in stock_data:
                    stock_info = numpy_cache.get_stock_info(stock_code)
                    stock_data[stock_code] = {
                        'name': stock_info.stock_name if stock_info else '',
                        'industry': stock_info.industry if stock_info else '未知',
                        'ranks': [],
                        'latest_indicators': {}
                    }
                
                stock_data[stock_code]['ranks'].append((check_date, daily.get('rank', 9999)))
                # 保存最新一天的技术指标
                stock_data[stock_code]['latest_indicators'] = {
                    'price_change': daily.get('price_change'),
                    'turnover_rate': daily.get('turnover_rate'),
                    'volatility': daily.get('volatility')
                }
        
        # 3. 后端计算：找出稳步上升的股票
        steady_stocks = []
        for code, info in stock_data.items():
            ranks = info['ranks']
            
            # 必须有完整的N天数据
            if len(ranks) != period:
                continue
            
            # 后端板块筛选逻辑
            if should_filter_stock(code, board_type):
                continue
            
            # 按日期排序
            ranks.sort(key=lambda x: x[0])
            
            # 检查是否连续上升（rank变小=上升）
            is_rising = True
            for i in range(len(ranks) - 1):
                if ranks[i][1] <= ranks[i+1][1]:  # 排名没有提升
                    is_rising = False
                    break
            
            if is_rising:
                total_improvement = ranks[0][1] - ranks[-1][1]  # 总提升
                
                if total_improvement >= min_rank_improvement:
                    # 构建排名历史和日期列表
                    rank_history = [r[1] for r in ranks]
                    date_list = [r[0].strftime('%Y%m%d') for r in ranks]
                    avg_improvement = total_improvement / (period - 1) if period > 1 else total_improvement
                    
                    indicators = info.get('latest_indicators', {})
                    steady_stocks.append(SteadyRiseStock(
                        code=code,
                        name=info['name'],
                        industry=info['industry'],
                        start_rank=ranks[0][1],
                        end_rank=ranks[-1][1],
                        total_improvement=total_improvement,
                        avg_daily_improvement=round(avg_improvement, 2),
                        rank_history=rank_history,
                        dates=date_list,
                        price_change=indicators.get('price_change'),
                        turnover_rate=indicators.get('turnover_rate'),
                        volatility=indicators.get('volatility')
                    ))
        
        if not steady_stocks:
            return self._empty_result(period)
        
        # 4. 后端计算：统计
        improvements = [s.total_improvement for s in steady_stocks]
        mean_improvement = statistics.mean(improvements)
        std_improvement = statistics.stdev(improvements) if len(improvements) > 1 else 0
        
        # 5. 后端计算：±σ筛选
        lower_bound = mean_improvement - std_improvement * sigma_multiplier
        upper_bound = mean_improvement + std_improvement * sigma_multiplier
        
        sigma_stocks = [
            stock for stock in steady_stocks
            if lower_bound <= stock.total_improvement <= upper_bound
        ]
        
        # 构建结果
        result = SteadyRiseResult(
            period=period,
            dates=date_strs,
            min_rank_improvement=min_rank_improvement,
            total_count=len(steady_stocks),
            stocks=steady_stocks,
            mean_improvement=mean_improvement,
            std_improvement=std_improvement,
            sigma_range=[lower_bound, upper_bound],
            sigma_stocks=sigma_stocks
        )
        
        # v0.5.0: 直接缓存对象，避免反序列化开销
        cache.set_api_cache("steady_rise", cache_key, result, ttl=STEADY_RISE_CACHE_TTL)
        logger.info(f"✓ 稳步上升分析完成并缓存: {len(steady_stocks)}只股票")
        
        return result
    
    def _empty_result(self, period: int) -> SteadyRiseResult:
        """空结果"""
        return SteadyRiseResult(
            period=period,
            dates=[],
            min_rank_improvement=0,
            total_count=0,
            stocks=[],
            mean_improvement=0,
            std_improvement=0,
            sigma_range=[0, 0],
            sigma_stocks=[]
        )


# 全局实例
steady_rise_service_db = SteadyRiseServiceDB()
