"""
行业服务
负责行业统计和趋势分析相关业务逻辑
"""
from pathlib import Path
from collections import Counter
import logging

from ..models import IndustryStats, IndustryTrend, IndustryStat, IndustryDateData
from ..utils import get_sorted_files, cache_manager
from .data_loader import DataLoader

logger = logging.getLogger(__name__)


class IndustryService:
    """行业服务"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_loader = DataLoader()
    
    def get_top1000_industry_stats(self) -> IndustryStats:
        """
        获取前1000名的行业分布统计
        
        Returns:
            行业统计数据
        """
        cache_key = "top1000_industry_stats"
        cached = cache_manager.get(cache_key)
        if cached:
            logger.info(f"使用缓存: {cache_key}")
            return cached
        
        logger.info("计算前1000名行业统计")
        
        files_with_dates = get_sorted_files(self.data_dir)
        
        if not files_with_dates:
            raise ValueError("未找到数据文件")
        
        # 获取最新日期的数据
        latest_date, latest_file = files_with_dates[-1]
        
        # 加载前1000名股票
        top_1000 = self.data_loader.load_top_n_stocks(latest_file, top_n=1000)
        
        # 统计行业分布
        industry_counter = Counter()
        for stock in top_1000:
            industry_counter[stock['industry']] += 1
        
        # 按数量排序
        sorted_industries = sorted(industry_counter.items(), key=lambda x: x[1], reverse=True)
        
        # 计算百分比
        total = len(top_1000)
        stats = [
            IndustryStat(
                industry=industry,
                count=count,
                percentage=round((count / total) * 100, 1)
            )
            for industry, count in sorted_industries
        ]
        
        result = IndustryStats(
            date=latest_date,
            total_stocks=total,
            stats=stats
        )
        
        cache_manager.set(cache_key, result)
        return result
    
    def get_industry_trend(self) -> IndustryTrend:
        """
        获取行业趋势数据（前1000名）
        
        Returns:
            行业趋势数据
        """
        cache_key = "industry_trend"
        cached = cache_manager.get(cache_key)
        if cached:
            logger.info(f"使用缓存: {cache_key}")
            return cached
        
        logger.info("计算行业趋势")
        
        files_with_dates = get_sorted_files(self.data_dir)
        
        if not files_with_dates:
            raise ValueError("未找到数据文件")
        
        # 收集所有日期的行业数据
        all_industries = set()
        trend_data = []
        
        for date, file_path in files_with_dates:
            try:
                # 加载前1000名股票
                top_1000 = self.data_loader.load_top_n_stocks(file_path, top_n=1000)
                
                # 统计该日期的行业分布
                industry_counter = Counter()
                for stock in top_1000:
                    industry = stock['industry']
                    industry_counter[industry] += 1
                    all_industries.add(industry)
                
                trend_data.append(IndustryDateData(
                    date=date,
                    industry_counts=dict(industry_counter)
                ))
            except Exception as e:
                logger.error(f"处理文件失败 {file_path}: {e}")
                continue
        
        # 按行业总数量排序
        industry_totals = Counter()
        for data in trend_data:
            for industry, count in data.industry_counts.items():
                industry_totals[industry] += count
        
        sorted_industries = [industry for industry, _ in industry_totals.most_common()]
        
        result = IndustryTrend(
            industries=sorted_industries,
            data=trend_data
        )
        
        cache_manager.set(cache_key, result)
        return result
