"""
行业趋势服务 - 内存缓存版
使用memory_cache替代数据库查询，大幅提升性能
"""
from typing import List
from collections import defaultdict
from datetime import datetime
import logging

from ..database import SessionLocal
from ..db_models import Stock, DailyStockData
from ..models.industry import IndustryStat
from .numpy_cache_middleware import numpy_cache
from .api_cache import api_cache
from sqlalchemy import desc, func

logger = logging.getLogger(__name__)


class IndustryServiceDB:
    """行业趋势服务（内存缓存版）"""
    
    CACHE_TTL = 1800  # 30分钟
    
    def __init__(self):
        """初始化服务"""
        pass  # 使用全局 api_cache
    
    def get_db(self):
        """获取数据库会话（仅在必要时使用）"""
        return SessionLocal()
    
    def analyze_industry(
        self,
        period: int = 3,
        top_n: int = 20,
        target_date = None
    ) -> List[IndustryStat]:
        """
        行业趋势分析（从内存缓存）
        
        Args:
            period: 分析周期
            top_n: 每天TOP N股票
            target_date: 目标日期（date对象）
        
        Returns:
            行业趋势列表
        """
        # 生成缓存key
        date_str = target_date.strftime('%Y%m%d') if target_date else None
        cache_key = f"industry_stats_{period}_{top_n}_{date_str}"
        cached = api_cache.get(cache_key)
        if cached is not None:
            logger.info(f"✨ 缓存命中: {cache_key}")
            return cached
        
        logger.info(f"🔄 计算行业统计: period={period}, top_n={top_n}")
        
        # 1. 从内存获取日期范围
        if target_date:
            target_date_obj = target_date
        else:
            target_date_obj = numpy_cache.get_latest_date()
        
        if not target_date_obj:
            return []
        
        # 获取最近N天日期
        all_dates = numpy_cache.get_dates_range(period * 2)
        target_dates = [d for d in all_dates if d <= target_date_obj][:period]
        
        if not target_dates:
            return []
        
        # 2. 从内存获取这些日期的TOP N股票（批量优化）
        industry_counts = defaultdict(int)
        
        # 收集所有需要查询的股票代码
        all_stock_codes = set()
        date_stocks_map = {}
        
        for date in target_dates:
            top_stocks = numpy_cache.get_top_n_by_rank(date, top_n)  # 返回Dict列表
            date_stocks_map[date] = top_stocks
            all_stock_codes.update(stock['stock_code'] for stock in top_stocks)
        
        # 批量获取股票信息（一次性查询，避免循环）
        stocks_info = numpy_cache.get_stocks_batch(list(all_stock_codes))
        
        # 统计行业
        for date, top_stocks in date_stocks_map.items():
            for stock_data in top_stocks:
                stock_info = stocks_info.get(stock_data['stock_code'])
                if stock_info and stock_info.industry:
                    # 处理行业字段
                    industry = stock_info.industry
                    if isinstance(industry, list) and industry:
                        industry = industry[0]
                    elif isinstance(industry, str) and industry:
                        if industry.startswith('['):
                            try:
                                import ast
                                industry_list = ast.literal_eval(industry)
                                industry = industry_list[0] if industry_list else None
                            except:
                                industry = industry.strip('[]').strip("'\"")
                    
                    if industry:
                        industry_counts[industry] += 1
        
        # 3. 构建结果并缓存
        stats = []
        total_stocks = period * top_n
        for industry, count in industry_counts.items():
            stats.append(IndustryStat(
                industry=industry,
                count=count,
                percentage=round(count / total_stocks * 100, 2)
            ))
        
        # 按股票数量排序
        stats.sort(key=lambda x: x.count, reverse=True)
        
        # 缓存结果
        api_cache.set(cache_key, stats, ttl=self.CACHE_TTL)
        logger.info(f"✅ 行业分析完成: {len(stats)}个行业")
        
        return stats


# 全局实例
industry_service_db = IndustryServiceDB()
