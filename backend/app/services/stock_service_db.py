"""
股票服务 - 内存缓存版
使用memory_cache替代数据库查询，大幅提升性能
"""
from typing import Optional
from datetime import datetime, timedelta
import logging

from ..database import SessionLocal
from ..db_models import Stock, DailyStockData
from ..models.stock import StockHistory
from ..utils.ttl_cache import TTLCache
from .memory_cache import memory_cache
from sqlalchemy import desc, or_

logger = logging.getLogger(__name__)


class StockServiceDB:
    """股票服务（内存缓存版）"""
    
    def __init__(self):
        """初始化计算结果缓存"""
        self.cache = TTLCache(default_ttl_seconds=1800)  # 30分钟TTL缓存
    
    def get_db(self):
        """获取数据库会话"""
        return SessionLocal()
    
    def search_stock(self, keyword: str, target_date: Optional[str] = None) -> Optional[StockHistory]:
        """
        搜索股票（从内存缓存）
        
        Args:
            keyword: 股票代码或名称
            target_date: 指定日期 (YYYYMMDD格式)
        
        Returns:
            股票历史数据
        """
        # 缓存key
        cache_key = f"stock_{keyword}_{target_date}"
        if cache_key in self.cache:
            logger.info(f"✨ 缓存命中: {cache_key}")
            return self.cache[cache_key]
        
        logger.info(f"🔄 搜索股票: {keyword}")
        
        # 1. 从内存中查找股票
        keyword_lower = keyword.lower()
        stock_info = None
        stock_code = None
        
        # 先精确匹配代码
        if keyword in memory_cache.get_all_stocks():
            stock_code = keyword
            stock_info = memory_cache.get_stock_info(keyword)
        else:
            # 模糊匹配代码或名称
            for code, stock in memory_cache.get_all_stocks().items():
                if (keyword_lower in code.lower() or 
                    (stock.stock_name and keyword_lower in stock.stock_name.lower())):
                    stock_code = code
                    stock_info = stock
                    break
        
        if not stock_info or not stock_code:
            return None
        
        # 2. 从内存获取历史数据（30天）
        if target_date:
            target_date_obj = datetime.strptime(target_date, '%Y%m%d').date()
        else:
            target_date_obj = memory_cache.get_latest_date()
        
        if not target_date_obj:
            return None
        
        # 获取30天日期
        all_dates = memory_cache.get_dates_range(60)
        target_dates = [d for d in all_dates if d <= target_date_obj][:30]
        
        # 获取该股票的历史数据
        history_data = memory_cache.get_stock_history(stock_code, target_dates)
        
        if not history_data:
            return None
        
        # 3. 组装日期排名信息
        date_rank_info = []
        for data in history_data:
            info = {
                'date': data.date.strftime('%Y%m%d'),
                'rank': data.rank,
                'price_change': float(data.price_change) if data.price_change else None,
                'turnover_rate': float(data.turnover_rate_percent) if data.turnover_rate_percent else None,
                'volume_days': float(data.volume_days) if data.volume_days else None,
                'avg_volume_ratio_50': float(data.avg_volume_ratio_50) if data.avg_volume_ratio_50 else None,
                'volatility': float(data.volatility) if data.volatility else None,
            }
            date_rank_info.append(info)
        
        # 4. 构建结果并缓存
        result = StockHistory(
            code=stock_info.stock_code,
            name=stock_info.stock_name,
            industry=stock_info.industry or '未知',
            date_rank_info=date_rank_info,
            appears_count=len(date_rank_info),
            dates=[info['date'] for info in date_rank_info]
        )
        
        self.cache[cache_key] = result
        logger.info(f"✅ 股票查询完成: {stock_info.stock_name}")
        
        return result


# 全局实例
stock_service_db = StockServiceDB()
