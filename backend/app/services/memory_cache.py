"""
全量内存缓存管理器
一次性加载所有数据到内存，避免频繁数据库查询
使用Numpy数组优化存储，减少内存占用
"""
import logging
from typing import Dict, List, Optional, TYPE_CHECKING
from datetime import date
from collections import defaultdict
from ..database import SessionLocal
from ..db_models import Stock, DailyStockData
from .numpy_cache import numpy_stock_cache

if TYPE_CHECKING:
    from ..db_models import Sector

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
        """初始化缓存管理器"""
        if self._initialized:
            return
        
        # === 股票数据缓存 ===
        # 股票基础信息缓存 {stock_code: Stock对象}
        self.stocks: Dict[str, Stock] = {}
        
        # 每日数据缓存
        self.daily_data_by_date: Dict[date, List[DailyStockData]] = defaultdict(list)  # {date: [DailyStockData对象列表]}
        self.daily_data_by_stock: Dict[str, Dict[date, DailyStockData]] = defaultdict(dict)  # {stock_code: {date: DailyStockData对象}}
        
        # 可用日期列表（降序，最新日期在前）
        self.dates: List[date] = []
        
        # === 板块数据缓存 ===
        # 板块基础信息缓存 {sector_id: Sector对象}
        self.sectors: Dict[int, Sector] = {}
        
        # 板块每日数据缓存
        self.sector_daily_data_by_date: Dict[date, List[DailyStockData]] = defaultdict(list)  # {date: [SectorDailyData对象列表]}
        self.sector_daily_data_by_name: Dict[str, Dict[date, DailyStockData]] = defaultdict(dict)  # {sector_name: {date: SectorDailyData对象}}
        
        # 板块可用日期列表（降序）
        self.sector_dates: List[date] = []
        
        self._initialized = True
        logger.info("✅ MemoryCacheManager 初始化完成（尚未加载数据）")
    
    def clear_cache(self):
        """清空所有缓存数据"""
        logger.info("🧹 清空内存缓存...")
        self.stocks.clear()
        self.daily_data_by_date.clear()
        self.daily_data_by_stock.clear()
        self.dates.clear()
        self.sectors.clear()
        self.sector_daily_data_by_date.clear()
        self.sector_daily_data_by_name.clear()
        self.sector_dates.clear()
        # 清空numpy缓存
        numpy_stock_cache.clear()
        logger.info("✅ 内存缓存已清空")
    
    def load_all_data(self):
        """一次性加载数据到内存（限制最近30天）"""
        logger.info("🔄 开始加载数据到内存...")
        
        # 先清空旧数据，避免重复累加导致内存爆炸
        self.clear_cache()
        
        db = SessionLocal()
        try:
            from sqlalchemy import func
            from datetime import timedelta
            
            # 1. 加载所有股票基础信息
            logger.info("  1/3 加载股票基础信息...")
            stocks = db.query(Stock).all()
            for stock in stocks:
                self.stocks[stock.stock_code] = stock
            logger.info(f"  ✅ 加载了 {len(self.stocks)} 只股票")
            
            # 2. 只加载最近30天的每日数据（性能优化）
            logger.info("  2/3 加载最近30天每日数据...")
            latest_date = db.query(func.max(DailyStockData.date)).scalar()
            if latest_date:
                cutoff_date = latest_date - timedelta(days=30)
                logger.info(f"  ⚡ 只加载 {cutoff_date} 至 {latest_date} 的数据")
                daily_data_list = db.query(DailyStockData).filter(
                    DailyStockData.date >= cutoff_date
                ).all()
            else:
                daily_data_list = []
            
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
            
            # 3.5 构建Numpy优化数组（性能优化）
            logger.info("  3.5/5 构建Numpy优化数组...")
            numpy_stock_cache.build_from_data(daily_data_list)
            usage = numpy_stock_cache.get_memory_usage()
            logger.info(f"  ✅ Numpy缓存: {usage['total_mb']:.2f} MB ({usage['n_records']} 条记录)")
            
            # 4. 对每个日期的数据按rank排序
            for date_key in self.daily_data_by_date:
                self.daily_data_by_date[date_key].sort(key=lambda x: x.rank)
            
            # 5. 加载板块数据
            logger.info("  4/5 加载板块数据...")
            from ..db_models import SectorDailyData, Sector
            
            # 4.1 加载板块基础信息
            sectors = db.query(Sector).all()
            for sector in sectors:
                self.sectors[sector.id] = sector
            logger.info(f"  ✅ 加载了 {len(self.sectors)} 个板块基础信息")
            
            # 4.2 只加载最近30天的板块每日数据（性能优化）
            sector_latest_date = db.query(func.max(SectorDailyData.date)).scalar()
            if sector_latest_date:
                sector_cutoff_date = sector_latest_date - timedelta(days=30)
                logger.info(f"  ⚡ 只加载 {sector_cutoff_date} 至 {sector_latest_date} 的板块数据")
                sector_data_list = db.query(SectorDailyData).filter(
                    SectorDailyData.date >= sector_cutoff_date
                ).all()
            else:
                sector_data_list = []
            
            # 构建板块索引
            sector_date_set = set()
            for data in sector_data_list:
                # 按日期索引
                self.sector_daily_data_by_date[data.date].append(data)
                # 按板块ID+日期索引（使用sector_id而不是sector_name）
                self.sector_daily_data_by_name[data.sector_id][data.date] = data
                # 收集日期
                sector_date_set.add(data.date)
            
            logger.info(f"  ✅ 加载了 {len(sector_data_list)} 条板块数据")
            
            # 5. 排序板块日期（降序）
            logger.info("  5/5 构建板块日期索引...")
            self.sector_dates = sorted(list(sector_date_set), reverse=True)
            logger.info(f"  ✅ 板块共 {len(self.sector_dates)} 个交易日")
            
            # 6. 对每个日期的板块数据按rank排序
            for date_key in self.sector_daily_data_by_date:
                self.sector_daily_data_by_date[date_key].sort(key=lambda x: x.rank)
            
            logger.info("🎉 全量数据加载完成！")
            logger.info(f"   【股票】")
            logger.info(f"   - 股票数量: {len(self.stocks)}")
            logger.info(f"   - 数据记录: {len(daily_data_list)}")
            logger.info(f"   - 交易日数: {len(self.dates)}")
            logger.info(f"   - 最新日期: {self.dates[0] if self.dates else 'N/A'}")
            logger.info(f"   - 最早日期: {self.dates[-1] if self.dates else 'N/A'}")
            logger.info(f"   【板块】")
            logger.info(f"   - 板块数据: {len(sector_data_list)} 条")
            logger.info(f"   - 交易日数: {len(self.sector_dates)}")
            logger.info(f"   - 最新日期: {self.sector_dates[0] if self.sector_dates else 'N/A'}")
            logger.info(f"   - 最早日期: {self.sector_dates[-1] if self.sector_dates else 'N/A'}")
            
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
    
    def get_stock_data_for_strategy(self, stock_code: str, target_date: date = None, lookback_days: int = 30) -> Optional[dict]:
        """
        获取股票策略分析所需的数据
        
        Args:
            stock_code: 股票代码
            target_date: 目标日期，默认最新日期
            lookback_days: 回溯天数
            
        Returns:
            包含closes, highs, lows, opens, volumes, turnovers, ranks的字典，或None
        """
        # 获取股票基础信息
        stock_info = self.get_stock_info(stock_code)
        if not stock_info:
            return None
        
        # 确定目标日期
        if target_date is None:
            target_date = self.get_latest_date()
        if not target_date:
            return None
        
        # 获取该股票的所有可用数据
        stock_daily = self.daily_data_by_stock.get(stock_code, {})
        if not stock_daily:
            return None
        
        # 筛选目标日期之前的数据，按日期排序
        available_dates = sorted([d for d in stock_daily.keys() if d <= target_date])
        if len(available_dates) < 5:
            return None
        
        # 取最近N天
        target_dates = available_dates[-lookback_days:] if len(available_dates) > lookback_days else available_dates
        
        # 收集数据
        closes, highs, lows, opens = [], [], [], []
        volumes, turnovers, ranks, bbis, price_changes = [], [], [], [], []
        
        for d in target_dates:
            data = stock_daily[d]
            closes.append(float(data.close_price) if data.close_price else 0)
            highs.append(float(data.high_price) if data.high_price else 0)
            lows.append(float(data.low_price) if data.low_price else 0)
            opens.append(float(data.open_price) if data.open_price else 0)
            volumes.append(float(data.volume) if data.volume else 0)
            turnovers.append(float(data.turnover_rate_percent) if data.turnover_rate_percent else 0)
            ranks.append(int(data.rank) if data.rank else 0)
            # BBI用middle_band(布林中轨)代替
            bbis.append(float(data.middle_band) if hasattr(data, 'middle_band') and data.middle_band else 0)
            # 当天涨跌幅
            price_changes.append(float(data.price_change) if hasattr(data, 'price_change') and data.price_change else 0)
        
        return {
            'stock_code': stock_code,
            'stock_name': stock_info.stock_name,
            'signal_date': target_dates[-1].strftime('%Y-%m-%d'),
            'closes': closes,
            'highs': highs,
            'lows': lows,
            'opens': opens,
            'volumes': volumes,
            'turnovers': turnovers,
            'ranks': ranks if any(ranks) else None,
            'bbis': bbis,
            'dates': target_dates,
            'price_changes': price_changes,  # 每天涨跌幅
        }
    
    def get_all_stocks_for_strategy(self, target_date: date = None, lookback_days: int = 30) -> List[dict]:
        """
        获取所有股票的策略分析数据
        
        用于批量扫描策略信号
        """
        results = []
        for stock_code in self.stocks.keys():
            data = self.get_stock_data_for_strategy(stock_code, target_date, lookback_days)
            if data:
                results.append(data)
        return results
    
    def get_top_n_stocks(self, target_date: date, max_count: int) -> List[DailyStockData]:
        """获取指定日期的TOP N股票"""
        all_data = self.daily_data_by_date.get(target_date, [])
        return [d for d in all_data if d.rank <= max_count]
    
    def get_stock_info(self, stock_code: str) -> Optional[Stock]:
        """获取股票基础信息"""
        return self.stocks.get(stock_code)
    
    def get_stocks_batch(self, stock_codes: List[str]) -> Dict[str, Stock]:
        """批量获取股票信息（性能优化）"""
        return {code: self.stocks[code] for code in stock_codes if code in self.stocks}
    
    def get_all_stocks(self) -> Dict[str, Stock]:
        """获取所有股票"""
        return self.stocks
    
    def is_loaded(self) -> bool:
        """检查数据是否已加载"""
        return len(self.stocks) > 0 and len(self.dates) > 0
    
    # === 板块数据查询方法 ===
    
    def get_sector_info(self, sector_id: int) -> Optional["Sector"]:
        """获取板块基础信息"""
        return self.sectors.get(sector_id)

    def get_sector_available_dates(self) -> List[str]:
        """获取所有板块可用日期"""
        return [d.strftime('%Y%m%d') for d in self.sector_dates]
    
    def get_sector_latest_date(self) -> Optional[date]:
        """获取板块最新日期"""
        return self.sector_dates[0] if self.sector_dates else None
    
    def get_sector_dates_range(self, period: int) -> List[date]:
        """获取最近N天的板块日期"""
        return self.sector_dates[:period]
    
    def get_sector_daily_data_by_date(self, target_date: date):
        """获取指定日期的所有板块数据"""
        return self.sector_daily_data_by_date.get(target_date, [])
    
    def get_sector_daily_data_by_id(self, sector_id: int, target_date: date):
        """获取指定板块在指定日期的数据"""
        return self.sector_daily_data_by_name.get(sector_id, {}).get(target_date)
    
    def get_sector_history(self, sector_id: int, dates: List[date]):
        """获取指定板块在多个日期的历史数据"""
        sector_data = self.sector_daily_data_by_name.get(sector_id, {})
        return [sector_data[d] for d in dates if d in sector_data]
    
    def get_top_n_sectors(self, target_date: date, max_count: int):
        """获取指定日期的TOP N板块"""
        all_data = self.sector_daily_data_by_date.get(target_date, [])
        return [d for d in all_data if d.rank <= max_count]
    
    def get_memory_stats(self) -> dict:
        """获取内存使用统计"""
        return {
            "stocks_count": len(self.stocks),
            "dates_count": len(self.dates),
            "daily_data_count": sum(len(data_list) for data_list in self.daily_data_by_date.values()),
            "date_index_keys": len(self.daily_data_by_date),
            "stock_index_keys": len(self.daily_data_by_stock),
            # 板块统计
            "sector_dates_count": len(self.sector_dates),
            "sector_daily_data_count": sum(len(data_list) for data_list in self.sector_daily_data_by_date.values()),
            "sector_date_index_keys": len(self.sector_daily_data_by_date),
            "sector_name_index_keys": len(self.sector_daily_data_by_name)
        }


# 全局单例
memory_cache = MemoryCacheManager()
