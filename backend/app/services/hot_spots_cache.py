"""
热点榜排名缓存管理器
用于缓存14天聚合热点榜数据，提供快速排名查询
"""
import time
import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class HotSpotsCache:
    """热点榜排名缓存
    
    缓存结构：
    {
        "20251107": {
            "data": [...],           # 完整榜单数据（前端展示用）
            "rank_map": {...},       # {股票代码: 排名} 映射（信号计算用）
            "timestamp": 1699603200  # 缓存时间戳
        }
    }
    """
    
    _cache: Dict[str, Dict] = {}
    _ttl: int = 86400  # 24小时过期
    _max_days: int = 30  # 最多保留30天历史数据
    
    @classmethod
    def get_rank(cls, stock_code: str, date: str) -> Optional[tuple]:
        """获取股票在指定日期的热点榜排名和出现次数
        
        Args:
            stock_code: 股票代码
            date: 日期 (YYYYMMDD)
            
        Returns:
            (rank, hit_count) 元组，如果不在榜单中返回None
            例如：(15, 12) 表示排名第15，出现12次
        """
        # 确保数据已加载
        if date not in cls._cache or cls._is_expired(date):
            cls._load_date(date)
        
        # 从rank_map快速查询（O(1)）
        rank_map = cls._cache.get(date, {}).get("rank_map", {})
        rank_info = rank_map.get(stock_code)
        
        if rank_info:
            return (rank_info["rank"], rank_info["hit_count"])
        
        return None
    
    @classmethod
    def get_full_data(cls, date: str) -> List[dict]:
        """获取指定日期的完整热点榜数据
        
        Args:
            date: 日期 (YYYYMMDD)
            
        Returns:
            完整榜单列表（用于前端展示）
        """
        # 确保数据已加载
        if date not in cls._cache or cls._is_expired(date):
            cls._load_date(date)
        
        return cls._cache.get(date, {}).get("data", [])
    
    @classmethod
    def preload_recent_dates(cls, days: int = 3):
        """预加载最近N天的数据
        
        Args:
            days: 预加载天数
        """
        try:
            from .memory_cache import memory_cache
            
            # 从memory_cache获取最近N天日期
            recent_dates = memory_cache.get_dates_range(days)
            
            if not recent_dates:
                logger.warning("无可用日期，跳过热点榜缓存预加载")
                return
            
            logger.info(f"预加载最近{days}天的热点榜数据: {[d.strftime('%Y%m%d') for d in recent_dates]}")
            
            for date_obj in recent_dates:
                date_str = date_obj.strftime('%Y%m%d')
                cls._load_date(date_str)
                
            logger.info("热点榜数据预加载完成")
        except Exception as e:
            logger.error(f"预加载热点榜数据失败: {e}")
    
    @classmethod
    def _load_date(cls, date: str):
        """从memory_cache加载指定日期的热点榜数据
        
        Args:
            date: 日期 (YYYYMMDD)
        """
        try:
            from .memory_cache import memory_cache
            from datetime import datetime
            from collections import defaultdict
            
            logger.info(f"加载热点榜数据: {date}")
            
            # 将字符串日期转为date对象
            target_date_obj = datetime.strptime(date, '%Y%m%d').date()
            
            # 获取最近14天的日期
            all_dates = memory_cache.dates
            target_dates = [d for d in all_dates if d <= target_date_obj][:14]
            
            if not target_dates:
                logger.warning(f"日期 {date} 无可用数据")
                return
            
            # 统计每只股票在14天内的出现次数
            stock_appearances = defaultdict(lambda: {'count': 0, 'dates': []})
            
            for date_obj in target_dates:
                # 获取该日期的TOP1000股票
                daily_stocks = memory_cache.get_top_n_stocks(date_obj, 1000)
                
                for stock_data in daily_stocks:
                    code = stock_data.stock_code
                    stock_appearances[code]['count'] += 1
                    stock_appearances[code]['dates'].append(date_obj)
                    
                    # 记录股票基础信息（首次）
                    if 'name' not in stock_appearances[code]:
                        stock_info = memory_cache.get_stock_info(code)
                        if stock_info:
                            stock_appearances[code]['name'] = stock_info.stock_name
                            stock_appearances[code]['industry'] = stock_info.industry or '未知'
            
            # 按出现次数排序，生成榜单
            sorted_stocks = sorted(
                stock_appearances.items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )[:1000]  # 只取前1000名
            
            # 构建完整榜单数据
            stocks = []
            for idx, (code, info) in enumerate(sorted_stocks):
                stock_data = {
                    'code': code,
                    'name': info['name'],
                    'industry': info['industry'],
                    'rank': idx + 1,
                    'hit_count': info['count']
                }
                stocks.append(stock_data)
            
            # 构建rank_map（快速查询用，包含排名和次数）
            rank_map = {
                stock['code']: {
                    "rank": stock["rank"],
                    "hit_count": stock["hit_count"]
                }
                for stock in stocks
            }
            
            # 添加rank_label到每只股票
            for stock in stocks:
                rank = stock["rank"]
                hit_count = stock["hit_count"]
                stock["rank_label"] = cls._get_rank_label(rank, hit_count)
            
            # 存入缓存
            cls._cache[date] = {
                "data": stocks,
                "rank_map": rank_map,
                "timestamp": time.time()
            }
            
            logger.info(f"热点榜数据加载完成: {date}, 共{len(stocks)}只股票")
            
            # 清理过期缓存
            cls._cleanup_old_cache()
            
        except Exception as e:
            logger.error(f"加载热点榜数据失败 {date}: {e}")
            # 存入空数据避免重复加载
            cls._cache[date] = {
                "data": [],
                "rank_map": {},
                "timestamp": time.time()
            }
    
    @classmethod
    def _is_expired(cls, date: str) -> bool:
        """检查缓存是否过期
        
        Args:
            date: 日期
            
        Returns:
            True if expired
        """
        if date not in cls._cache:
            return True
        
        timestamp = cls._cache[date].get("timestamp", 0)
        return (time.time() - timestamp) > cls._ttl
    
    @classmethod
    def _cleanup_old_cache(cls):
        """清理超过max_days的旧缓存"""
        if len(cls._cache) <= cls._max_days:
            return
        
        # 按日期排序，保留最新的max_days天
        sorted_dates = sorted(cls._cache.keys(), reverse=True)
        dates_to_remove = sorted_dates[cls._max_days:]
        
        for date in dates_to_remove:
            del cls._cache[date]
            logger.debug(f"清理旧缓存: {date}")
    
    @classmethod
    def _get_rank_label(cls, rank: int, hit_count: int) -> str:
        """根据排名和出现次数返回标签
        
        Args:
            rank: 排名（1-1000）
            hit_count: 14天内出现次数（2-14）
            
        Returns:
            热点榜TOP100·12次 | 热点榜TOP200·8次 | ...
        """
        # 使用中点符号·连接，更简洁美观
        if rank <= 100:
            return f"TOP100·{hit_count}次"
        elif rank <= 200:
            return f"TOP200·{hit_count}次"
        elif rank <= 400:
            return f"TOP400·{hit_count}次"
        elif rank <= 600:
            return f"TOP600·{hit_count}次"
        elif rank <= 800:
            return f"TOP800·{hit_count}次"
        elif rank <= 1000:
            return f"TOP1000·{hit_count}次"
        return ""
    
    @classmethod
    def clear_cache(cls):
        """清空所有缓存（测试用）"""
        cls._cache.clear()
        logger.info("热点榜缓存已清空")
    
    @classmethod
    def get_cache_stats(cls) -> dict:
        """获取缓存统计信息（调试用）
        
        Returns:
            {
                "cached_dates": [...],
                "total_dates": int,
                "memory_usage_kb": float
            }
        """
        import sys
        
        memory_bytes = sys.getsizeof(cls._cache)
        for date, data in cls._cache.items():
            memory_bytes += sys.getsizeof(data)
            memory_bytes += sys.getsizeof(data.get("data", []))
            memory_bytes += sys.getsizeof(data.get("rank_map", {}))
        
        return {
            "cached_dates": sorted(cls._cache.keys(), reverse=True),
            "total_dates": len(cls._cache),
            "memory_usage_kb": round(memory_bytes / 1024, 2)
        }
