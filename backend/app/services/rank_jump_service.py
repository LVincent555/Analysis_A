"""
排名跳变分析服务
"""
from typing import List, Dict, Optional
from pathlib import Path
from app.models.stock import RankJumpStock, RankJumpResult
from app.services.data_loader import DataLoader
from app.utils import get_sorted_files
from app.config import DATA_DIR
import logging
import statistics

logger = logging.getLogger(__name__)


class RankJumpService:
    """排名跳变分析服务"""
    
    def __init__(self):
        self.data_loader = DataLoader()
        self.data_dir = Path(DATA_DIR)
        self.cache = {}
    
    def analyze_rank_jump(
        self, 
        jump_threshold: int = 2500,
        filter_stocks: bool = True,
        sigma_multiplier: float = 1.0
    ) -> RankJumpResult:
        """
        分析排名跳变的股票
        
        Args:
            jump_threshold: 跳变阈值，默认2500（向前跳变超过此值的股票）
            filter_stocks: 是否过滤双创板股票
            sigma_multiplier: σ倍数，用于计算筛选范围
        
        Returns:
            排名跳变分析结果
        """
        cache_key = f"rank_jump_{jump_threshold}_{filter_stocks}_{sigma_multiplier}"
        if cache_key in self.cache:
            logger.info(f"使用缓存: {cache_key}")
            return self.cache[cache_key]
        
        logger.info(f"计算新数据: {cache_key}")
        
        # 获取所有数据文件
        files_with_dates = get_sorted_files(self.data_dir)
        
        if len(files_with_dates) < 2:
            return RankJumpResult(
                stocks=[],
                total_count=0,
                jump_threshold=jump_threshold,
                latest_date="",
                previous_date=""
            )
        
        # 获取最近两天的数据（已按时间排序，最后一个是最新的）
        previous_date, previous_file = files_with_dates[-2]
        latest_date, latest_file = files_with_dates[-1]
        
        # 加载两天的数据（包含所有股票）
        latest_stocks = self.data_loader.load_stock_data(
            latest_file,
            filter_stocks=filter_stocks,
            include_details=True,
            max_count=None
        )
        
        previous_stocks = self.data_loader.load_stock_data(
            previous_file,
            filter_stocks=filter_stocks,
            include_details=False,
            max_count=None
        )
        
        # 建立前一天的排名字典
        previous_ranks = {}
        for stock in previous_stocks:
            code_normalized = stock['code'].lstrip('0')
            previous_ranks[code_normalized] = stock['rank']
        
        # 分析排名跳变
        jump_stocks = []
        for stock in latest_stocks:
            code_normalized = stock['code'].lstrip('0')
            current_rank = stock['rank']
            
            # 检查前一天是否存在
            if code_normalized in previous_ranks:
                previous_rank = previous_ranks[code_normalized]
                # 计算跳变（正数表示向前跳，负数表示向后跳）
                rank_change = previous_rank - current_rank
                
                # 只关注向前跳变超过阈值的
                if rank_change >= jump_threshold:
                    jump_stocks.append(RankJumpStock(
                        code=stock['code'],
                        name=stock['name'],
                        industry=stock['industry'],
                        latest_rank=current_rank,
                        previous_rank=previous_rank,
                        rank_change=rank_change,
                        latest_date=latest_date,
                        previous_date=previous_date,
                        price_change=stock.get('price_change'),
                        turnover_rate=stock.get('turnover_rate'),
                        volume_days=stock.get('volume_days'),
                        avg_volume_ratio_50=stock.get('avg_volume_ratio_50'),
                        volatility=stock.get('volatility')
                    ))
        
        # 按跳变幅度倒序排列
        jump_stocks.sort(key=lambda x: x.rank_change, reverse=True)
        
        # 计算统计信息
        mean_rank_change = None
        std_rank_change = None
        sigma_range = None
        sigma_stocks = []
        
        if len(jump_stocks) >= 2:
            rank_changes = [stock.rank_change for stock in jump_stocks]
            mean_rank_change = statistics.mean(rank_changes)
            std_rank_change = statistics.stdev(rank_changes)
            
            # 计算±σ范围（使用sigma_multiplier）
            lower_bound = mean_rank_change - std_rank_change * sigma_multiplier
            upper_bound = mean_rank_change + std_rank_change * sigma_multiplier
            sigma_range = [lower_bound, upper_bound]
            
            # 筛选±σ范围内的股票
            sigma_stocks = [
                stock for stock in jump_stocks
                if lower_bound <= stock.rank_change <= upper_bound
            ]
            logger.info(f"±{sigma_multiplier}σ范围: [{lower_bound:.1f}, {upper_bound:.1f}], 包含 {len(sigma_stocks)} 只股票")
        
        result = RankJumpResult(
            stocks=jump_stocks,
            total_count=len(jump_stocks),
            jump_threshold=jump_threshold,
            latest_date=latest_date,
            previous_date=previous_date,
            mean_rank_change=mean_rank_change,
            std_rank_change=std_rank_change,
            sigma_range=sigma_range,
            sigma_stocks=sigma_stocks
        )
        
        self.cache[cache_key] = result
        logger.info(f"找到 {len(jump_stocks)} 只排名跳变超过 {jump_threshold} 的股票")
        
        return result


# 全局实例
rank_jump_service = RankJumpService()
