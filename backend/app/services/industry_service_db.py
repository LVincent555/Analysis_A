"""
行业趋势服务 - 数据库版
简单SQL查询 + 后端计算
"""
from typing import List
from collections import defaultdict
import logging

from ..database import SessionLocal
from ..db_models import Stock, DailyStockData
from ..models.industry import IndustryStat
from sqlalchemy import desc, func

logger = logging.getLogger(__name__)


class IndustryServiceDB:
    """行业趋势服务（数据库版）"""
    
    def __init__(self):
        """初始化"""
        self.cache = {}
    
    def get_db(self):
        """获取数据库会话"""
        return SessionLocal()
    
    def analyze_industry(
        self,
        period: int = 3,
        top_n: int = 20
    ) -> List[IndustryStat]:
        """
        行业趋势分析
        
        逻辑：
        1. 简单SQL：获取最近N天TOP股票
        2. 后端计算：按行业分组统计
        3. 后端计算：排序
        
        Args:
            period: 分析周期
            top_n: 每天TOP N股票
        
        Returns:
            行业趋势列表
        """
        cache_key = f"industry_{period}_{top_n}"
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
            
            if not recent_dates:
                return []
            
            target_dates = [d[0] for d in recent_dates]
            
            # 2. 简单SQL：查询这些日期的TOP N股票
            query = db.query(Stock.industry)\
                .join(DailyStockData, Stock.stock_code == DailyStockData.stock_code)\
                .filter(DailyStockData.date.in_(target_dates))\
                .filter(DailyStockData.rank <= top_n)
            
            # 3. 后端计算：统计每个行业出现次数
            industry_counts = defaultdict(int)
            for (industry,) in query.all():
                if industry:
                    industry_counts[industry] += 1
            
            # 4. 后端计算：转换为统计列表并排序
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
            
            self.cache[cache_key] = stats
            logger.info(f"行业分析完成: {len(stats)}个行业")
            
            return stats
            
        finally:
            db.close()


# 全局实例
industry_service_db = IndustryServiceDB()
