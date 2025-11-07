"""
股票服务 - 数据库版
简单SQL查询 + 后端计算
"""
from typing import Optional
from datetime import datetime, timedelta
import logging

from ..database import SessionLocal
from ..db_models import Stock, DailyStockData
from ..models.stock import StockHistory
from sqlalchemy import desc, or_

logger = logging.getLogger(__name__)


class StockServiceDB:
    """股票服务（数据库版）"""
    
    def __init__(self):
        """初始化"""
        pass
    
    def get_db(self):
        """获取数据库会话"""
        return SessionLocal()
    
    def search_stock(self, keyword: str, target_date: Optional[str] = None) -> Optional[StockHistory]:
        """
        搜索股票
        
        逻辑：
        1. 简单SQL：模糊查询股票
        2. 简单SQL：查询历史数据
        3. 后端计算：组装结果
        
        Args:
            keyword: 股票代码或名称
            target_date: 指定日期 (YYYYMMDD格式)，不传则使用最新日期
        
        Returns:
            股票历史数据
        """
        db = self.get_db()
        try:
            # 1. 简单SQL：查找股票
            search_pattern = f'%{keyword}%'
            stock = db.query(Stock).filter(
                or_(
                    Stock.stock_code.like(search_pattern),
                    Stock.stock_name.like(search_pattern)
                )
            ).first()
            
            if not stock:
                return None
            
            # 2. 简单SQL：查询该股票的所有历史数据（从旧到新排序）
            # 如果指定target_date，查询从该日期往前30天
            if target_date:
                target_date_obj = datetime.strptime(target_date, '%Y%m%d').date()
                history_data = db.query(DailyStockData)\
                    .filter(DailyStockData.stock_code == stock.stock_code)\
                    .filter(DailyStockData.date <= target_date_obj)\
                    .order_by(desc(DailyStockData.date))\
                    .limit(30)\
                    .all()
                # 反转以保持从旧到新的顺序
                history_data = list(reversed(history_data))
            else:
                history_data = db.query(DailyStockData)\
                    .filter(DailyStockData.stock_code == stock.stock_code)\
                    .order_by(DailyStockData.date)\
                    .limit(30)\
                    .all()
            
            if not history_data:
                return None
            
            # 3. 后端计算：组装日期排名信息
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
            
            # 构建结果
            return StockHistory(
                code=stock.stock_code,
                name=stock.stock_name,
                industry=stock.industry or '未知',
                date_rank_info=date_rank_info,
                appears_count=len(date_rank_info),
                dates=[info['date'] for info in date_rank_info]
            )
            
        finally:
            db.close()


# 全局实例
stock_service_db = StockServiceDB()
