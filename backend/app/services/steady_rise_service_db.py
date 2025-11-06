"""
稳步上升服务 - 数据库版
简单SQL查询 + 后端计算
"""
from typing import List
import statistics
import logging

from ..database import SessionLocal
from ..db_models import Stock, DailyStockData
from ..models.stock import SteadyRiseResult, SteadyRiseStock
from sqlalchemy import desc

logger = logging.getLogger(__name__)


class SteadyRiseServiceDB:
    """稳步上升服务（数据库版）"""
    
    def __init__(self):
        """初始化"""
        self.cache = {}
    
    def get_db(self):
        """获取数据库会话"""
        return SessionLocal()
    
    def analyze_steady_rise(
        self,
        period: int = 3,
        filter_stocks: bool = True,
        min_rank_improvement: int = 100,
        sigma_multiplier: float = 1.0
    ) -> SteadyRiseResult:
        """
        稳步上升分析
        
        逻辑：
        1. 简单SQL：获取最近N天的数据
        2. 后端计算：按股票分组
        3. 后端计算：检查连续上升
        4. 后端计算：统计和筛选
        
        Args:
            period: 分析周期
            filter_stocks: 是否过滤双创板
            min_rank_improvement: 最小排名提升
            sigma_multiplier: σ倍数
        
        Returns:
            稳步上升结果
        """
        cache_key = f"steady_rise_{period}_{filter_stocks}_{min_rank_improvement}_{sigma_multiplier}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        db = self.get_db()
        try:
            # 1. 简单SQL：获取最近N天的日期
            recent_dates = db.query(DailyStockData.date)\
                .distinct()\
                .order_by(desc(DailyStockData.date))\
                .limit(period)\
                .all()
            
            if len(recent_dates) < period:
                return self._empty_result(period)
            
            target_dates = [d[0] for d in recent_dates]
            target_dates.reverse()  # 从旧到新排序
            date_strs = [d.strftime('%Y%m%d') for d in target_dates]
            
            # 2. 简单SQL：查询这些日期的所有数据
            query = db.query(
                DailyStockData.stock_code,
                DailyStockData.date,
                DailyStockData.rank,
                Stock.stock_name,
                Stock.industry
            ).join(Stock, DailyStockData.stock_code == Stock.stock_code)\
             .filter(DailyStockData.date.in_(target_dates))\
             .order_by(DailyStockData.stock_code, DailyStockData.date)
            
            # 3. 后端计算：按股票分组
            stock_data = {}  # {stock_code: [(date, rank), ...]}
            for code, date, rank, name, industry in query.all():
                if code not in stock_data:
                    stock_data[code] = {
                        'name': name,
                        'industry': industry or '未知',
                        'ranks': []
                    }
                stock_data[code]['ranks'].append((date, rank))
            
            # 4. 后端计算：找出稳步上升的股票
            steady_stocks = []
            for code, info in stock_data.items():
                ranks = info['ranks']
                
                # 必须有完整的N天数据
                if len(ranks) != period:
                    continue
                
                # 后端过滤逻辑
                if filter_stocks and (code.startswith('3') or code.startswith('68')):
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
                        
                        steady_stocks.append(SteadyRiseStock(
                            code=code,
                            name=info['name'],
                            industry=info['industry'],
                            start_rank=ranks[0][1],
                            end_rank=ranks[-1][1],
                            total_improvement=total_improvement,
                            avg_daily_improvement=round(avg_improvement, 2),
                            rank_history=rank_history,
                            dates=date_list
                        ))
            
            if not steady_stocks:
                return self._empty_result(period)
            
            # 5. 后端计算：统计
            improvements = [s.total_improvement for s in steady_stocks]
            mean_improvement = statistics.mean(improvements)
            std_improvement = statistics.stdev(improvements) if len(improvements) > 1 else 0
            
            # 6. 后端计算：±σ筛选
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
            
            self.cache[cache_key] = result
            logger.info(f"稳步上升分析完成: {len(steady_stocks)}只股票")
            
            return result
            
        finally:
            db.close()
    
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
