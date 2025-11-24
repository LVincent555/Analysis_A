"""
板块数据服务 - 内存缓存版
使用memory_cache替代数据库查询，大幅提升性能
"""
from typing import List, Dict, Optional
from datetime import datetime, date
from ..models import SectorRankingResult, SectorInfo, SectorDetail
from ..utils.ttl_cache import TTLCache
from .memory_cache import memory_cache
import logging

logger = logging.getLogger(__name__)


class SectorServiceDB:
    """板块数据服务（内存缓存版）"""
    
    def __init__(self):
        """初始化计算结果缓存"""
        self.cache = TTLCache(default_ttl_seconds=1800)  # 30分钟TTL缓存
    
    def get_available_dates(self) -> List[str]:
        """
        获取所有可用的数据日期（从内存缓存）
        
        Returns:
            日期列表（降序）
        """
        return memory_cache.get_sector_available_dates()
    
    def get_sector_ranking(
        self,
        target_date: Optional[str] = None,
        limit: int = 100
    ) -> SectorRankingResult:
        """
        获取板块排名（从内存缓存）
        """
        # 确定查询日期
        if target_date:
            try:
                query_date = datetime.strptime(target_date, '%Y%m%d').date()
            except ValueError:
                logger.error(f"无效的日期格式: {target_date}")
                return SectorRankingResult(date='', sectors=[], total_count=0)
        else:
            query_date = memory_cache.get_sector_latest_date()
            if not query_date:
                return SectorRankingResult(date='', sectors=[], total_count=0)
        
        # 从内存获取数据
        daily_data_list = memory_cache.get_top_n_sectors(query_date, limit)
        total_count = len(memory_cache.get_sector_daily_data_by_date(query_date))
        
        sectors = []
        for daily_data in daily_data_list:
            # 从内存缓存获取板块名称
            sector_info = memory_cache.get_sector_info(daily_data.sector_id)
            sector_name = sector_info.sector_name if sector_info else str(daily_data.sector_id)
            
            info = SectorInfo(
                name=sector_name,
                rank=daily_data.rank,
                total_score=float(daily_data.total_score) if daily_data.total_score else None,
                price_change=float(daily_data.price_change) if daily_data.price_change else None,
                turnover_rate=float(daily_data.turnover_rate_percent) if daily_data.turnover_rate_percent else None,
                volume=daily_data.volume,
                volatility=float(daily_data.volatility) if daily_data.volatility else None
            )
            sectors.append(info)
        
        return SectorRankingResult(
            date=query_date.strftime('%Y%m%d'),
            sectors=sectors,
            total_count=total_count
        )
    
    def get_sector_detail(
        self,
        sector_name: str,
        days: int = 30,
        target_date: Optional[str] = None
    ) -> Optional[SectorDetail]:
        """
        获取板块详细信息和历史数据（从内存缓存）
        """
        # 1. 查找板块ID
        target_sector = None
        for sector in memory_cache.sectors.values():
            if sector.sector_name == sector_name:
                target_sector = sector
                break
        
        if not target_sector:
            logger.warning(f"板块不存在: {sector_name}")
            return None
        
        # 2. 确定日期范围
        if target_date:
            try:
                target_date_obj = datetime.strptime(target_date, '%Y%m%d').date()
            except ValueError:
                return None
        else:
            target_date_obj = memory_cache.get_sector_latest_date()
            
        if not target_date_obj:
            return None
            
        # 获取最近N天日期
        all_dates = memory_cache.sector_dates
        target_dates = [d for d in all_dates if d <= target_date_obj][:days]
        
        # 3. 获取历史数据
        history_data = memory_cache.get_sector_history(target_sector.id, target_dates)
        
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
            name=target_sector.sector_name,
            history=history,
            days_count=len(history)
        )
    
    def search_sectors(self, keyword: str) -> List[str]:
        """
        搜索板块（从内存缓存）
        
        Args:
            keyword: 搜索关键词
        
        Returns:
            匹配的板块名称列表
        """
        search_pattern = keyword.lower()
        results = []
        
        for sector in memory_cache.sectors.values():
            if search_pattern in sector.sector_name.lower():
                results.append(sector.sector_name)
                if len(results) >= 20:
                    break
                    
        return results


# 创建全局实例
sector_service_db = SectorServiceDB()
