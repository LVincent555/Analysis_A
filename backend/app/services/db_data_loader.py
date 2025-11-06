"""
数据库版数据加载器
从PostgreSQL数据库加载数据，替代Excel文件读取
"""
from typing import List, Dict, Optional
from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
import logging

from ..database import SessionLocal
from ..db_models import Stock, DailyStockData

logger = logging.getLogger(__name__)


class DBDataLoader:
    """数据库数据加载器"""
    
    def __init__(self):
        """初始化"""
        pass
    
    def get_db(self) -> Session:
        """获取数据库会话"""
        return SessionLocal()
    
    def get_available_dates(self) -> List[str]:
        """
        获取所有可用的日期列表
        
        Returns:
            日期列表，格式：['20251105', '20251104', ...]，倒序排列
        """
        db = self.get_db()
        try:
            dates = db.query(DailyStockData.date)\
                .distinct()\
                .order_by(desc(DailyStockData.date))\
                .all()
            
            # 转换为字符串格式
            date_list = [d[0].strftime('%Y%m%d') for d in dates]
            logger.info(f"找到 {len(date_list)} 个可用日期")
            return date_list
        finally:
            db.close()
    
    def load_stock_data(
        self,
        date_str: str,
        max_count: Optional[int] = None,
        filter_stocks: bool = False,
        include_details: bool = False
    ) -> List[Dict]:
        """
        加载指定日期的股票数据
        
        Args:
            date_str: 日期字符串，格式：'20251105'
            max_count: 最大加载数量，None表示全部
            filter_stocks: 是否过滤双创板股票
            include_details: 是否包含详细技术指标
        
        Returns:
            股票数据列表
        """
        db = self.get_db()
        try:
            # 转换日期格式
            target_date = datetime.strptime(date_str, '%Y%m%d').date()
            
            # 构建查询
            query = db.query(DailyStockData, Stock)\
                .join(Stock, DailyStockData.stock_code == Stock.stock_code)\
                .filter(DailyStockData.date == target_date)\
                .order_by(DailyStockData.rank)
            
            # 应用过滤
            if filter_stocks:
                # 过滤双创板（3开头和68开头）
                query = query.filter(
                    ~DailyStockData.stock_code.like('3%'),
                    ~DailyStockData.stock_code.like('68%')
                )
            
            # 限制数量
            if max_count:
                query = query.limit(max_count)
            
            results = query.all()
            
            # 转换为字典格式
            stocks_data = []
            for daily_data, stock in results:
                stock_dict = {
                    'code': stock.stock_code,
                    'name': stock.stock_name,
                    'industry': stock.industry or '未知',
                    'rank': daily_data.rank
                }
                
                # 如果需要详细信息，添加技术指标
                if include_details:
                    stock_dict.update({
                        'price_change': float(daily_data.price_change) if daily_data.price_change else None,
                        'turnover_rate': float(daily_data.turnover_rate_percent) if daily_data.turnover_rate_percent else None,
                        'volume_days': float(daily_data.volume_days) if daily_data.volume_days else None,
                        'avg_volume_ratio_50': float(daily_data.avg_volume_ratio_50) if daily_data.avg_volume_ratio_50 else None,
                        'volatility': float(daily_data.volatility) if daily_data.volatility else None,
                    })
                
                stocks_data.append(stock_dict)
            
            logger.info(f"加载 {len(stocks_data)} 条股票数据，日期：{date_str}")
            return stocks_data
            
        finally:
            db.close()
    
    def get_stock_history(
        self,
        stock_code: str,
        limit: int = 30
    ) -> Dict:
        """
        获取股票历史数据
        
        Args:
            stock_code: 股票代码
            limit: 返回最近N天的数据
        
        Returns:
            股票历史数据字典
        """
        db = self.get_db()
        try:
            # 查询股票基本信息
            stock = db.query(Stock).filter(Stock.stock_code == stock_code).first()
            if not stock:
                return None
            
            # 查询历史数据
            history_data = db.query(DailyStockData)\
                .filter(DailyStockData.stock_code == stock_code)\
                .order_by(desc(DailyStockData.date))\
                .limit(limit)\
                .all()
            
            if not history_data:
                return None
            
            # 构建返回数据
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
            
            return {
                'code': stock.stock_code,
                'name': stock.stock_name,
                'industry': stock.industry or '未知',
                'date_rank_info': date_rank_info,
                'appears_count': len(date_rank_info),
                'dates': [info['date'] for info in date_rank_info]
            }
            
        finally:
            db.close()
    
    def search_stocks(
        self,
        keyword: str,
        limit: int = 20
    ) -> List[Dict]:
        """
        模糊搜索股票
        
        Args:
            keyword: 搜索关键词（股票代码或名称）
            limit: 返回数量限制
        
        Returns:
            匹配的股票列表
        """
        db = self.get_db()
        try:
            query = db.query(Stock)
            
            # 模糊匹配代码或名称
            search_pattern = f'%{keyword}%'
            query = query.filter(
                (Stock.stock_code.like(search_pattern)) |
                (Stock.stock_name.like(search_pattern))
            )
            
            results = query.limit(limit).all()
            
            return [
                {
                    'code': stock.stock_code,
                    'name': stock.stock_name,
                    'industry': stock.industry or '未知'
                }
                for stock in results
            ]
            
        finally:
            db.close()


# 全局实例
db_data_loader = DBDataLoader()
