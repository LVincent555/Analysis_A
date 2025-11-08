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
from ..utils.ttl_cache import TTLCache
from .memory_cache import memory_cache
from sqlalchemy import desc, func

logger = logging.getLogger(__name__)


class IndustryServiceDB:
    """行业趋势服务（内存缓存版）"""
    
    def __init__(self):
        """初始化计算结果缓存"""
        self.cache = TTLCache(default_ttl_seconds=1800)  # 30分钟TTL缓存
    
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
        if cache_key in self.cache:
            logger.info(f"✨ 缓存命中: {cache_key}")
            return self.cache[cache_key]
        
        logger.info(f"🔄 计算行业统计: period={period}, top_n={top_n}")
        
        # 1. 从内存获取日期范围
        if target_date:
            target_date_obj = target_date
        else:
            target_date_obj = memory_cache.get_latest_date()
        
        if not target_date_obj:
            return []
        
        # 获取最近N天日期
        all_dates = memory_cache.get_dates_range(period * 2)
        target_dates = [d for d in all_dates if d <= target_date_obj][:period]
        
        if not target_dates:
            return []
        
        # 2. 从内存获取这些日期的TOP N股票
        industry_counts = defaultdict(int)
        
        for date in target_dates:
            top_stocks = memory_cache.get_top_n_stocks(date, top_n)
            
            for stock_data in top_stocks:
                # 获取股票信息
                stock_info = memory_cache.get_stock_info(stock_data.stock_code)
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
        self.cache[cache_key] = stats
        logger.info(f"✅ 行业分析完成: {len(stats)}个行业")
        
        return stats


# 全局实例
industry_service_db = IndustryServiceDB()
