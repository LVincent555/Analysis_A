"""
稳步上升分析服务
筛选连续N天排名持续上升的股票
"""
from typing import List, Dict, Optional
from pathlib import Path
from app.models.stock import SteadyRiseStock, SteadyRiseResult
from app.services.data_loader import DataLoader
from app.utils import get_sorted_files
from app.config import DATA_DIR
import logging
import statistics

logger = logging.getLogger(__name__)


class SteadyRiseService:
    """稳步上升分析服务"""
    
    def __init__(self):
        self.data_loader = DataLoader()
        self.data_dir = Path(DATA_DIR)
        self.cache = {}
    
    def analyze_steady_rise(
        self, 
        period: int = 3,
        filter_stocks: bool = True,
        min_rank_improvement: int = 100,  # 最小排名提升幅度
        sigma_multiplier: float = 1.0
    ) -> SteadyRiseResult:
        """
        分析稳步上升的股票
        
        Args:
            period: 分析周期（天数）
            filter_stocks: 是否过滤双创板股票
            min_rank_improvement: 最小排名提升幅度（总排名提升需超过此值）
            sigma_multiplier: σ倍数，用于计算筛选范围
        
        Returns:
            稳步上升分析结果
        """
        cache_key = f"steady_rise_{period}_{filter_stocks}_{min_rank_improvement}_{sigma_multiplier}"
        if cache_key in self.cache:
            logger.info(f"使用缓存: {cache_key}")
            return self.cache[cache_key]
        
        logger.info(f"计算新数据: {cache_key}")
        
        # 获取所有数据文件
        files_with_dates = get_sorted_files(self.data_dir)
        
        if len(files_with_dates) < period:
            return SteadyRiseResult(
                stocks=[],
                total_count=0,
                period=period,
                dates=[],
                min_rank_improvement=min_rank_improvement
            )
        
        # 获取最近period天的数据
        recent_files = files_with_dates[-period:]
        dates = [date for date, _ in recent_files]
        
        # 加载所有天的数据
        all_stocks_by_date = {}
        for date, file_path in recent_files:
            stocks = self.data_loader.load_stock_data(
                file_path,
                filter_stocks=filter_stocks,
                include_details=True,
                max_count=None
            )
            # 建立代码到股票数据的映射
            stocks_dict = {}
            for stock in stocks:
                code_normalized = stock['code'].lstrip('0')
                stocks_dict[code_normalized] = stock
            all_stocks_by_date[date] = stocks_dict
        
        # 分析稳步上升的股票
        steady_rise_stocks = []
        
        # 获取最新一天的股票列表
        latest_date = dates[-1]
        latest_stocks_dict = all_stocks_by_date[latest_date]
        
        for code_normalized, latest_stock in latest_stocks_dict.items():
            # 检查这只股票在所有天数都出现
            appears_all_days = True
            rank_history = []
            
            for date in dates:
                if code_normalized in all_stocks_by_date[date]:
                    rank_history.append(all_stocks_by_date[date][code_normalized]['rank'])
                else:
                    appears_all_days = False
                    break
            
            if not appears_all_days:
                continue
            
            # 检查是否稳步上升（每一天的排名都比前一天小，即越来越靠前）
            is_steady_rise = True
            for i in range(1, len(rank_history)):
                if rank_history[i] >= rank_history[i-1]:  # 如果当前排名>=前一天排名，说明没有上升
                    is_steady_rise = False
                    break
            
            if not is_steady_rise:
                continue
            
            # 检查总排名提升幅度
            total_improvement = rank_history[0] - rank_history[-1]
            if total_improvement < min_rank_improvement:
                continue
            
            # 计算平均每天提升
            avg_daily_improvement = total_improvement / (period - 1) if period > 1 else total_improvement
            
            # 添加到结果列表
            steady_rise_stocks.append(SteadyRiseStock(
                code=latest_stock['code'],
                name=latest_stock['name'],
                industry=latest_stock['industry'],
                start_rank=rank_history[0],
                end_rank=rank_history[-1],
                total_improvement=total_improvement,
                avg_daily_improvement=avg_daily_improvement,
                rank_history=rank_history,
                dates=dates,
                price_change=latest_stock.get('price_change'),
                turnover_rate=latest_stock.get('turnover_rate'),
                volume_days=latest_stock.get('volume_days'),
                avg_volume_ratio_50=latest_stock.get('avg_volume_ratio_50'),
                volatility=latest_stock.get('volatility')
            ))
        
        # 按总排名提升幅度倒序排列
        steady_rise_stocks.sort(key=lambda x: x.total_improvement, reverse=True)
        
        # 计算统计信息
        mean_improvement = None
        std_improvement = None
        sigma_range = None
        sigma_stocks = []
        
        if len(steady_rise_stocks) >= 2:
            improvements = [stock.total_improvement for stock in steady_rise_stocks]
            mean_improvement = statistics.mean(improvements)
            std_improvement = statistics.stdev(improvements)
            
            # 计算±σ范围（使用sigma_multiplier）
            lower_bound = mean_improvement - std_improvement * sigma_multiplier
            upper_bound = mean_improvement + std_improvement * sigma_multiplier
            sigma_range = [lower_bound, upper_bound]
            
            # 筛选±σ范围内的股票
            sigma_stocks = [
                stock for stock in steady_rise_stocks
                if lower_bound <= stock.total_improvement <= upper_bound
            ]
            logger.info(f"±{sigma_multiplier}σ范围: [{lower_bound:.1f}, {upper_bound:.1f}], 包含 {len(sigma_stocks)} 只股票")
        
        result = SteadyRiseResult(
            stocks=steady_rise_stocks,
            total_count=len(steady_rise_stocks),
            period=period,
            dates=dates,
            min_rank_improvement=min_rank_improvement,
            mean_improvement=mean_improvement,
            std_improvement=std_improvement,
            sigma_range=sigma_range,
            sigma_stocks=sigma_stocks
        )
        
        self.cache[cache_key] = result
        logger.info(f"找到 {len(steady_rise_stocks)} 只连续{period}天稳步上升的股票")
        
        return result


# 全局实例
steady_rise_service = SteadyRiseService()
