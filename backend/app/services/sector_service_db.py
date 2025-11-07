"""
板块数据服务（数据库版）
提供板块查询、排名、趋势分析等功能
"""
from typing import List, Dict, Optional
from datetime import datetime, date
from sqlalchemy import desc, func
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..db_models import Sector, SectorDailyData
from ..models import SectorRankingResult, SectorInfo, SectorDetail
import logging

logger = logging.getLogger(__name__)


class SectorServiceDB:
    """板块数据服务（数据库版）"""
    
    def __init__(self):
        """初始化"""
        self.cache = {}
    
    def get_db(self):
        """获取数据库会话"""
        return SessionLocal()
    
    def get_available_dates(self) -> List[str]:
        """
        获取所有可用的数据日期
        
        Returns:
            日期列表（降序）
        """
        db = self.get_db()
        try:
            dates = db.query(SectorDailyData.date)\
                .distinct()\
                .order_by(desc(SectorDailyData.date))\
                .all()
            
            return [d[0].strftime('%Y%m%d') for d in dates]
        finally:
            db.close()
    
    def get_sector_ranking(
        self,
        target_date: Optional[str] = None,
        limit: int = 100
    ) -> SectorRankingResult:
        """
        获取板块排名
        
        Args:
            target_date: 指定日期 (YYYYMMDD格式)，不传则使用最新日期
            limit: 返回的板块数量
        
        Returns:
            板块排名结果
        """
        db = self.get_db()
        try:
            # 确定查询日期
            if target_date:
                query_date = datetime.strptime(target_date, '%Y%m%d').date()
            else:
                latest_date = db.query(func.max(SectorDailyData.date)).scalar()
                if not latest_date:
                    return SectorRankingResult(
                        date='',
                        sectors=[],
                        total_count=0
                    )
                query_date = latest_date
            
            # 查询该日期的板块数据
            query = db.query(
                SectorDailyData,
                Sector.sector_name
            ).join(Sector, SectorDailyData.sector_id == Sector.id)\
             .filter(SectorDailyData.date == query_date)\
             .order_by(SectorDailyData.rank)\
             .limit(limit)
            
            sectors = []
            for daily_data, sector_name in query.all():
                sector_info = SectorInfo(
                    name=sector_name,
                    rank=daily_data.rank,
                    total_score=float(daily_data.total_score) if daily_data.total_score else None,
                    price_change=float(daily_data.price_change) if daily_data.price_change else None,
                    turnover_rate=float(daily_data.turnover_rate_percent) if daily_data.turnover_rate_percent else None,
                    volume=daily_data.volume,
                    volatility=float(daily_data.volatility) if daily_data.volatility else None
                )
                sectors.append(sector_info)
            
            total_count = db.query(func.count(SectorDailyData.id))\
                .filter(SectorDailyData.date == query_date)\
                .scalar()
            
            return SectorRankingResult(
                date=query_date.strftime('%Y%m%d'),
                sectors=sectors,
                total_count=total_count or 0
            )
            
        finally:
            db.close()
    
    def get_sector_detail(
        self,
        sector_name: str,
        days: int = 30,
        target_date: Optional[str] = None
    ) -> Optional[SectorDetail]:
        """
        获取板块详细信息和历史数据
        
        Args:
            sector_name: 板块名称
            days: 返回的历史天数
            target_date: 指定日期 (YYYYMMDD格式)，不传则使用最新日期
        
        Returns:
            板块详细信息
        """
        db = self.get_db()
        try:
            # 查找板块
            sector = db.query(Sector).filter(
                Sector.sector_name == sector_name
            ).first()
            
            if not sector:
                logger.warning(f"板块不存在: {sector_name}")
                return None
            
            # 查询历史数据
            if target_date:
                target_date_obj = datetime.strptime(target_date, '%Y%m%d').date()
                history_query = db.query(SectorDailyData)\
                    .filter(SectorDailyData.sector_id == sector.id)\
                    .filter(SectorDailyData.date <= target_date_obj)\
                    .order_by(desc(SectorDailyData.date))\
                    .limit(days)
            else:
                history_query = db.query(SectorDailyData)\
                    .filter(SectorDailyData.sector_id == sector.id)\
                    .order_by(desc(SectorDailyData.date))\
                    .limit(days)
            
            history_data = history_query.all()
            
            if not history_data:
                return None
            
            # 构建历史记录
            history = []
            for data in reversed(history_data):  # 从旧到新排序
                record = {
                    'date': data.date.strftime('%Y%m%d'),
                    'rank': data.rank,
                    'total_score': float(data.total_score) if data.total_score else None,
                    'price_change': float(data.price_change) if data.price_change else None,
                    'turnover_rate': float(data.turnover_rate_percent) if data.turnover_rate_percent else None,
                    'volume': data.volume,
                    'volatility': float(data.volatility) if data.volatility else None,
                    'close_price': float(data.close_price) if data.close_price else None
                }
                history.append(record)
            
            return SectorDetail(
                name=sector.sector_name,
                history=history,
                days_count=len(history)
            )
            
        finally:
            db.close()
    
    def search_sectors(self, keyword: str) -> List[str]:
        """
        搜索板块
        
        Args:
            keyword: 搜索关键词
        
        Returns:
            匹配的板块名称列表
        """
        db = self.get_db()
        try:
            search_pattern = f'%{keyword}%'
            sectors = db.query(Sector.sector_name)\
                .filter(Sector.sector_name.like(search_pattern))\
                .limit(20)\
                .all()
            
            return [s[0] for s in sectors]
            
        finally:
            db.close()


# 创建全局实例
sector_service_db = SectorServiceDB()
