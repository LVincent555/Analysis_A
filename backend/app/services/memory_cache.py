"""
全量内存缓存管理器
启动时一次性加载所有数据到内存，后续操作都走内存
"""
import logging
from typing import Dict, List, Optional
from datetime import date
from collections import defaultdict
from ..database import SessionLocal
from ..db_models import Stock, DailyStockData

logger = logging.getLogger(__name__)


class MemoryCacheManager:
    """全量内存缓存管理器（单例模式）"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # 内存数据结构
        self.stocks: Dict[str, Stock] = {}  # stock_code -> Stock对象
        self.daily_data_by_date: Dict[date, List[DailyStockData]] = defaultdict(list)  # date -> [数据列表]
        self.daily_data_by_stock: Dict[str, Dict[date, DailyStockData]] = defaultdict(dict)  # stock_code -> {date -> 数据}
        self.dates: List[date] = []  # 所有可用日期（降序）
        
        self._initialized = True
        logger.info("✅ MemoryCacheManager 初始化完成（尚未加载数据）")
    
    def load_all_data(self):
        """一次性加载所有数据到内存"""
        logger.info("🔄 开始全量加载数据到内存...")
        
        db = SessionLocal()
        try:
            # 1. 加载所有股票基础信息
            logger.info("  1/3 加载股票基础信息...")
            stocks = db.query(Stock).all()
            for stock in stocks:
                self.stocks[stock.stock_code] = stock
            logger.info(f"  ✅ 加载了 {len(self.stocks)} 只股票")
            
            # 2. 加载所有每日数据（一次性查询）
            logger.info("  2/3 加载所有每日数据...")
            daily_data_list = db.query(DailyStockData).all()
            
            # 构建内存索引
            date_set = set()
            for data in daily_data_list:
                # 按日期索引
                self.daily_data_by_date[data.date].append(data)
                # 按股票+日期索引
                self.daily_data_by_stock[data.stock_code][data.date] = data
                # 收集日期
                date_set.add(data.date)
            
            logger.info(f"  ✅ 加载了 {len(daily_data_list)} 条每日数据")
            
            # 3. 排序日期（降序，最新日期在前）
            logger.info("  3/3 构建日期索引...")
            self.dates = sorted(list(date_set), reverse=True)
            logger.info(f"  ✅ 共 {len(self.dates)} 个交易日")
            
            # 4. 对每个日期的数据按rank排序
            for date_key in self.daily_data_by_date:
                self.daily_data_by_date[date_key].sort(key=lambda x: x.rank)
            
            logger.info("🎉 全量数据加载完成！")
            logger.info(f"   - 股票数量: {len(self.stocks)}")
            logger.info(f"   - 数据记录: {len(daily_data_list)}")
            logger.info(f"   - 交易日数: {len(self.dates)}")
            logger.info(f"   - 最新日期: {self.dates[0] if self.dates else 'N/A'}")
            logger.info(f"   - 最早日期: {self.dates[-1] if self.dates else 'N/A'}")
            
        except Exception as e:
            logger.error(f"❌ 加载数据失败: {e}")
            raise
        finally:
            db.close()
    
    def get_available_dates(self) -> List[str]:
        """获取所有可用日期"""
        return [d.strftime('%Y%m%d') for d in self.dates]
    
    def get_latest_date(self) -> Optional[date]:
        """获取最新日期"""
        return self.dates[0] if self.dates else None
    
    def get_dates_range(self, period: int) -> List[date]:
        """获取最近N天的日期"""
        return self.dates[:period]
    
    def get_daily_data_by_date(self, target_date: date) -> List[DailyStockData]:
        """获取指定日期的所有数据"""
        return self.daily_data_by_date.get(target_date, [])
    
    def get_daily_data_by_stock(self, stock_code: str, target_date: date) -> Optional[DailyStockData]:
        """获取指定股票在指定日期的数据"""
        return self.daily_data_by_stock.get(stock_code, {}).get(target_date)
    
    def get_stock_history(self, stock_code: str, dates: List[date]) -> List[DailyStockData]:
        """获取指定股票在多个日期的历史数据"""
        stock_data = self.daily_data_by_stock.get(stock_code, {})
        return [stock_data[d] for d in dates if d in stock_data]
    
    def get_top_n_stocks(self, target_date: date, max_count: int) -> List[DailyStockData]:
        """获取指定日期的TOP N股票"""
        all_data = self.daily_data_by_date.get(target_date, [])
        return [d for d in all_data if d.rank <= max_count]
    
    def get_stock_info(self, stock_code: str) -> Optional[Stock]:
        """获取股票基础信息"""
        return self.stocks.get(stock_code)
    
    def get_all_stocks(self) -> Dict[str, Stock]:
        """获取所有股票"""
        return self.stocks
    
    def is_loaded(self) -> bool:
        """检查数据是否已加载"""
        return len(self.stocks) > 0 and len(self.dates) > 0
    
    def get_memory_stats(self) -> dict:
        """获取内存使用统计"""
        return {
            "stocks_count": len(self.stocks),
            "dates_count": len(self.dates),
            "daily_data_count": sum(len(data_list) for data_list in self.daily_data_by_date.values()),
            "date_index_keys": len(self.daily_data_by_date),
            "stock_index_keys": len(self.daily_data_by_stock)
        }


# 全局单例
memory_cache = MemoryCacheManager()
