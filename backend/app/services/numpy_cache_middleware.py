"""
Numpy 缓存中间件 - 统一数据访问层

目标：让后端 99% 情况下不访问数据库

⚠️ 关键技术规范：
   - 禁止 ORM 实例化：使用 with_entities 或原生 SQL
   - 价格/金额 → float64：避免精度误差
   - 空值处理：int 类型填充默认值
   - 字符串：只存索引，通过 IndexManager 反查
"""

import logging
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .numpy_stores import IndexManager, DailyDataStore, SectorDataStore

logger = logging.getLogger(__name__)


# ========== 数据类型定义 ==========

@dataclass
class StockInfo:
    """股票基础信息"""
    stock_code: str
    stock_name: str
    industry: str


@dataclass
class SectorInfo:
    """板块基础信息"""
    sector_id: int
    sector_name: str


@dataclass
class StrategyData:
    """策略分析用数据"""
    stock_code: str
    stock_name: str
    signal_date: str
    closes: List[float]
    opens: List[float]
    highs: List[float]
    lows: List[float]
    volumes: List[int]
    turnovers: List[float]
    ranks: List[int]
    price_changes: List[float]
    dates: List[str]


class NumpyCacheMiddleware:
    """
    Numpy 缓存中间件 - 单例模式
    
    提供统一的数据访问接口，替代直接的数据库查询
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # === 股票数据 ===
        self.index_mgr = IndexManager()
        self.daily_store = DailyDataStore()
        
        # === 股票基础信息 (保留Python字典，因为包含字符串) ===
        self.stocks: Dict[str, StockInfo] = {}
        
        # === 板块数据 ===
        self.sector_store = SectorDataStore()
        self.sectors: Dict[int, SectorInfo] = {}
        
        self._initialized = False
        self._loading = False
    
    # ========== 数据加载 ==========
    
    def load_from_db(self, days: int = 30) -> None:
        """
        从数据库加载数据到缓存
        
        ⚠️ 使用 with_entities 避免 ORM 实例化
        
        Args:
            days: 加载最近N天数据
        """
        if self._loading:
            logger.warning("数据正在加载中，跳过重复加载")
            return
        
        self._loading = True
        
        try:
            from ..database import SessionLocal
            from ..db_models import Stock, DailyStockData, Sector, SectorDailyData
            from sqlalchemy import desc, func
            
            db = SessionLocal()
            
            try:
                logger.info(f"🚀 开始加载缓存数据 (最近 {days} 天)...")
                
                # === 1. 加载股票基础信息 ===
                logger.info("  1/5 加载股票基础信息...")
                stock_rows = db.query(
                    Stock.stock_code,
                    Stock.stock_name,
                    Stock.industry
                ).all()
                
                self.stocks.clear()
                stock_codes = []
                for row in stock_rows:
                    self.stocks[row.stock_code] = StockInfo(
                        stock_code=row.stock_code,
                        stock_name=row.stock_name,
                        industry=row.industry or '未知'
                    )
                    stock_codes.append(row.stock_code)
                
                logger.info(f"  ✅ 股票基础信息: {len(self.stocks)} 只")
                
                # === 2. 获取最近N天日期 ===
                logger.info("  2/5 获取日期范围...")
                date_rows = db.query(
                    DailyStockData.date
                ).distinct().order_by(
                    desc(DailyStockData.date)
                ).limit(days).all()
                
                dates = [row.date for row in date_rows]
                
                if not dates:
                    logger.warning("  ⚠️ 没有可用数据")
                    return
                
                logger.info(f"  ✅ 日期范围: {dates[-1]} ~ {dates[0]} ({len(dates)} 天)")
                
                # === 3. 构建索引 ===
                logger.info("  3/5 构建索引...")
                self.index_mgr.build_stock_index(stock_codes)
                self.index_mgr.build_date_index(dates)
                
                # === 4. 加载每日数据 (使用 with_entities，不实例化 ORM) ===
                logger.info("  4/5 加载每日数据...")
                
                # 定义要查询的字段
                daily_rows = db.query(
                    DailyStockData.stock_code,
                    DailyStockData.date,
                    DailyStockData.rank,
                    DailyStockData.total_score,
                    DailyStockData.price_change,
                    DailyStockData.close_price,
                    DailyStockData.open_price,
                    DailyStockData.high_price,
                    DailyStockData.low_price,
                    DailyStockData.market_cap_billions,
                    DailyStockData.volume,
                    DailyStockData.turnover_rate_percent,
                    DailyStockData.volatility,
                    DailyStockData.volume_days,
                    DailyStockData.avg_volume_ratio_50,
                    DailyStockData.macd_signal,
                    DailyStockData.dif,
                    DailyStockData.dem,
                    DailyStockData.histgram,
                    DailyStockData.rsi,
                    DailyStockData.slowk,
                    DailyStockData.adx,
                    DailyStockData.plus_di,
                    DailyStockData.beta,
                    DailyStockData.correlation,
                    DailyStockData.long_term,
                    DailyStockData.short_term,
                    DailyStockData.overbought,
                    DailyStockData.oversold,
                    DailyStockData.lower_band,
                    DailyStockData.middle_band,
                    DailyStockData.upper_band,
                ).filter(
                    DailyStockData.date.in_(dates)
                ).order_by(
                    desc(DailyStockData.date),
                    DailyStockData.rank
                ).all()
                
                # 字段映射
                field_mapping = {
                    'stock_code': 0, 'date': 1, 'rank': 2, 'total_score': 3,
                    'price_change': 4, 'close_price': 5, 'open_price': 6,
                    'high_price': 7, 'low_price': 8, 'market_cap': 9,
                    'volume': 10, 'turnover_rate': 11, 'volatility': 12,
                    'volume_days': 13, 'avg_volume_ratio_50': 14,
                    'macd_signal': 15, 'dif': 16, 'dem': 17, 'histgram': 18,
                    'rsi': 19, 'slowk': 20, 'adx': 21, 'plus_di': 22,
                    'beta': 23, 'correlation': 24, 'long_term': 25,
                    'short_term': 26, 'overbought': 27, 'oversold': 28,
                    'lower_band': 29, 'middle_band': 30, 'upper_band': 31,
                }
                
                self.daily_store.build_from_tuples(daily_rows, self.index_mgr, field_mapping)
                
                # 构建复合索引
                if self.daily_store.data_array is not None and len(self.daily_store.data_array) > 0:
                    self.index_mgr.build_composite_index(
                        self.daily_store.data_array['stock_idx'],
                        self.daily_store.data_array['date_idx']
                    )
                
                # === 5. 加载板块数据 ===
                logger.info("  5/5 加载板块数据...")
                self._load_sector_data(db, days)
                
                self._initialized = True
                
                # 统计内存使用
                daily_mem = self.daily_store.get_memory_usage()
                sector_mem = self.sector_store.get_memory_usage()
                
                logger.info(f"✅ 缓存加载完成!")
                logger.info(f"   股票数据: {daily_mem['n_records']} 条, {daily_mem['mb']:.2f} MB")
                logger.info(f"   板块数据: {sector_mem['n_records']} 条, {sector_mem['mb']:.2f} MB")
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ 缓存加载失败: {e}")
            raise
        finally:
            self._loading = False
    
    def _load_sector_data(self, db, days: int) -> None:
        """加载板块数据"""
        from ..db_models import Sector, SectorDailyData
        from sqlalchemy import desc
        
        # 加载板块基础信息
        sector_rows = db.query(
            Sector.id,
            Sector.sector_name
        ).all()
        
        self.sectors.clear()
        for row in sector_rows:
            self.sectors[row.id] = SectorInfo(
                sector_id=row.id,
                sector_name=row.sector_name
            )
        
        logger.info(f"  ✅ 板块基础信息: {len(self.sectors)} 个")
        
        # 获取板块日期
        sector_dates = db.query(
            SectorDailyData.date
        ).distinct().order_by(
            desc(SectorDailyData.date)
        ).limit(days).all()
        
        sector_dates = [row.date for row in sector_dates]
        
        if not sector_dates:
            return
        
        # 加载板块每日数据
        sector_daily_rows = db.query(
            SectorDailyData.sector_id,
            SectorDailyData.date,
            SectorDailyData.rank,
            SectorDailyData.total_score,
            SectorDailyData.price_change,
            SectorDailyData.close_price,
            SectorDailyData.open_price,
            SectorDailyData.high_price,
            SectorDailyData.low_price,
            SectorDailyData.volume,
            SectorDailyData.turnover_rate_percent,
            SectorDailyData.volatility,
            SectorDailyData.volume_days,
            SectorDailyData.avg_volume_ratio_50,
            SectorDailyData.beta,
            SectorDailyData.correlation,
            SectorDailyData.rsi,
            SectorDailyData.adx,
            SectorDailyData.slowk,
            SectorDailyData.dif,
            SectorDailyData.dem,
            SectorDailyData.macd_signal,
        ).filter(
            SectorDailyData.date.in_(sector_dates)
        ).order_by(
            desc(SectorDailyData.date),
            SectorDailyData.rank
        ).all()
        
        sector_field_mapping = {
            'sector_id': 0, 'date': 1, 'rank': 2, 'total_score': 3,
            'price_change': 4, 'close_price': 5, 'open_price': 6,
            'high_price': 7, 'low_price': 8, 'volume': 9,
            'turnover_rate': 10, 'volatility': 11, 'volume_days': 12,
            'avg_volume_ratio_50': 13, 'beta': 14, 'correlation': 15,
            'rsi': 16, 'adx': 17, 'slowk': 18, 'dif': 19, 'dem': 20,
            'macd_signal': 21,
        }
        
        self.sector_store.build_from_tuples(sector_daily_rows, sector_field_mapping)
        
        # 打印板块缓存统计
        sector_dates = self.sector_store.index_mgr.get_all_dates()
        logger.info(f"  ✅ 板块日数据: {len(sector_daily_rows)} 条, {len(sector_dates)} 天")
    
    def clear(self) -> None:
        """清空所有缓存"""
        self.index_mgr.clear()
        self.daily_store.clear()
        self.stocks.clear()
        self.sector_store.clear()
        self.sectors.clear()
        self._initialized = False
        logger.info("✅ 缓存已清空")
    
    def reload(self, days: int = 30) -> None:
        """重新加载数据"""
        self.clear()
        self.load_from_db(days)
    
    def is_loaded(self) -> bool:
        """检查缓存是否已加载"""
        return self._initialized
    
    # ========== 日期查询 ==========
    
    def get_available_dates(self) -> List[str]:
        """获取所有可用日期 (YYYYMMDD字符串列表, 降序)"""
        return [d.strftime('%Y%m%d') for d in self.index_mgr.get_all_dates()]
    
    def get_latest_date(self) -> Optional[date]:
        """获取最新日期"""
        return self.index_mgr.get_latest_date()
    
    def get_dates_range(self, n: int) -> List[date]:
        """获取最近N天日期 (降序)"""
        return self.index_mgr.get_dates_range(n)
    
    def has_date(self, target_date: date) -> bool:
        """检查日期是否有数据"""
        return self.index_mgr.has_date(target_date)
    
    # ========== 股票基础信息 ==========
    
    def get_stock_info(self, stock_code: str) -> Optional[StockInfo]:
        """获取股票基础信息"""
        return self.stocks.get(stock_code)
    
    def get_all_stocks(self) -> Dict[str, StockInfo]:
        """获取所有股票"""
        return self.stocks.copy()
    
    def get_stocks_batch(self, stock_codes: List[str]) -> Dict[str, StockInfo]:
        """批量获取股票信息"""
        return {code: self.stocks[code] for code in stock_codes if code in self.stocks}
    
    def search_stocks(self, keyword: str, limit: int = 10) -> List[StockInfo]:
        """搜索股票 (代码/名称模糊匹配)"""
        keyword_lower = keyword.lower()
        results = []
        
        for code, info in self.stocks.items():
            if keyword_lower in code.lower() or keyword_lower in info.stock_name.lower():
                results.append(info)
                if len(results) >= limit:
                    break
        
        return results
    
    # ========== 股票日数据查询 ==========
    
    def get_daily_data(self, stock_code: str, target_date: date) -> Optional[Dict]:
        """获取单股票单日数据"""
        row_idx = self.index_mgr.get_row_idx_by_code_date(stock_code, target_date)
        if row_idx is None:
            return None
        
        row = self.daily_store.get_row(row_idx)
        if row is None:
            return None
        
        return self.daily_store.row_to_dict(row, self.index_mgr)
    
    def get_daily_data_batch(
        self, 
        stock_codes: List[str], 
        target_date: date
    ) -> Dict[str, Dict]:
        """批量获取多股票单日数据"""
        result = {}
        date_idx = self.index_mgr.get_date_idx(target_date)
        
        if date_idx is None:
            return result
        
        for code in stock_codes:
            stock_idx = self.index_mgr.get_stock_idx(code)
            if stock_idx is None:
                continue
            
            row_idx = self.index_mgr.get_row_idx(stock_idx, date_idx)
            if row_idx is None:
                continue
            
            row = self.daily_store.get_row(row_idx)
            if row is not None:
                result[code] = self.daily_store.row_to_dict(row, self.index_mgr)
        
        return result
    
    def get_stock_history(
        self, 
        stock_code: str, 
        days: int = 30,
        end_date: Optional[date] = None
    ) -> List[Dict]:
        """获取单股票历史数据 (按日期降序)"""
        stock_idx = self.index_mgr.get_stock_idx(stock_code)
        if stock_idx is None:
            return []
        
        row_indices = self.index_mgr.get_rows_by_stock(stock_idx)
        if not row_indices:
            return []
        
        # 如果指定了结束日期，需要过滤
        if end_date:
            end_date_idx = self.index_mgr.get_date_idx(end_date)
            if end_date_idx is not None:
                row_indices = [
                    idx for idx in row_indices
                    if self.daily_store.data_array[idx]['date_idx'] >= end_date_idx
                ]
        
        # 限制数量
        row_indices = row_indices[:days]
        
        rows = self.daily_store.get_rows_by_indices(row_indices)
        return self.daily_store.rows_to_dicts(rows, self.index_mgr)
    
    def get_all_by_date(self, target_date: date) -> List[Dict]:
        """获取某日期的所有股票数据"""
        date_idx = self.index_mgr.get_date_idx(target_date)
        if date_idx is None:
            return []
        
        range_info = self.index_mgr.get_rows_by_date(date_idx)
        if range_info is None:
            return []
        
        start, end = range_info
        rows = self.daily_store.get_rows_slice(start, end)
        return self.daily_store.rows_to_dicts(rows, self.index_mgr)
    
    def get_top_n_by_rank(self, target_date: date, n: int) -> List[Dict]:
        """获取某日期排名前N的股票 (按rank升序)"""
        date_idx = self.index_mgr.get_date_idx(target_date)
        if date_idx is None:
            return []
        
        range_info = self.index_mgr.get_rows_by_date(date_idx)
        if range_info is None:
            return []
        
        start, end = range_info
        rows = self.daily_store.get_top_n_by_rank(start, end, n)
        return self.daily_store.rows_to_dicts(rows, self.index_mgr)
    
    def get_stocks_by_industry(self, industry: str, target_date: date) -> List[Dict]:
        """获取某行业的所有股票数据"""
        # 先获取该日期所有数据
        all_data = self.get_all_by_date(target_date)
        
        # 过滤行业
        result = []
        for data in all_data:
            stock_info = self.stocks.get(data['stock_code'])
            if stock_info and stock_info.industry == industry:
                result.append(data)
        
        return result
    
    # ========== 板块日期查询 ==========
    
    def get_sector_available_dates(self) -> List[str]:
        """获取板块所有可用日期"""
        return [d.strftime('%Y%m%d') for d in self.sector_store.index_mgr.get_all_dates()]
    
    def get_sector_latest_date(self) -> Optional[date]:
        """获取板块最新日期"""
        return self.sector_store.index_mgr.get_latest_date()
    
    def get_sector_dates_range(self, n: int) -> List[date]:
        """获取板块最近N天日期"""
        return self.sector_store.index_mgr.get_dates_range(n)
    
    # ========== 板块基础信息 ==========
    
    def get_sector_info(self, sector_id: int) -> Optional[SectorInfo]:
        """获取板块基础信息"""
        return self.sectors.get(sector_id)
    
    def get_all_sectors(self) -> Dict[int, SectorInfo]:
        """获取所有板块"""
        return self.sectors.copy()
    
    def search_sectors(self, keyword: str) -> List[SectorInfo]:
        """搜索板块"""
        keyword_lower = keyword.lower()
        return [
            info for info in self.sectors.values()
            if keyword_lower in info.sector_name.lower()
        ]
    
    # ========== 板块日数据查询 ==========
    
    def get_sector_daily_data(self, sector_id: int, target_date: date) -> Optional[Dict]:
        """获取板块单日数据"""
        sector_idx = self.sector_store.index_mgr.get_sector_idx(sector_id)
        date_idx = self.sector_store.index_mgr.get_date_idx(target_date)
        
        if sector_idx is None or date_idx is None:
            return None
        
        row_idx = self.sector_store.index_mgr.get_row_idx(sector_idx, date_idx)
        if row_idx is None:
            return None
        
        row = self.sector_store.get_row(row_idx)
        if row is None:
            return None
        
        return self.sector_store.row_to_dict(row)
    
    def get_sector_history(self, sector_id: int, days: int = 30, end_date: date = None) -> List[Dict]:
        """获取板块历史数据
        
        Args:
            sector_id: 板块ID
            days: 返回天数（从 end_date 往前）
            end_date: 结束日期，不传则返回所有可用数据
        """
        sector_idx = self.sector_store.index_mgr.get_sector_idx(sector_id)
        if sector_idx is None:
            return []
        
        row_indices = self.sector_store.index_mgr.get_rows_by_sector(sector_idx)
        if not row_indices:
            return []
        
        result = []
        for idx in row_indices:
            row = self.sector_store.get_row(idx)
            if row is not None:
                row_dict = self.sector_store.row_to_dict(row)
                # 如果指定了 end_date，只返回 end_date 及之前的数据
                if end_date:
                    row_date_str = row_dict.get('date')
                    if row_date_str:
                        from datetime import datetime
                        row_date = datetime.strptime(row_date_str, '%Y%m%d').date()
                        if row_date > end_date:
                            continue  # 跳过比 end_date 更新的数据
                result.append(row_dict)
                if len(result) >= days:
                    break
        
        return result
    
    def get_top_n_sectors(self, target_date: date, n: int) -> List[Dict]:
        """获取某日期排名前N的板块"""
        date_idx = self.sector_store.index_mgr.get_date_idx(target_date)
        if date_idx is None:
            return []
        
        range_info = self.sector_store.index_mgr.get_rows_by_date(date_idx)
        if range_info is None:
            return []
        
        start, end = range_info
        rows = self.sector_store.get_top_n_by_rank(start, end, n)
        return self.sector_store.rows_to_dicts(rows)
    
    def get_sector_all_by_date(self, target_date: date) -> List[Dict]:
        """获取某日期的所有板块数据"""
        date_idx = self.sector_store.index_mgr.get_date_idx(target_date)
        if date_idx is None:
            return []
        
        range_info = self.sector_store.index_mgr.get_rows_by_date(date_idx)
        if range_info is None:
            return []
        
        start, end = range_info
        rows = self.sector_store.get_rows_slice(start, end)
        return self.sector_store.rows_to_dicts(rows)
    
    # ========== 专用接口：联表查询 ==========
    
    def get_stock_daily_full(self, stock_code: str, target_date: date) -> Optional[Dict]:
        """获取股票完整数据 (基础信息 + 日数据)"""
        daily_data = self.get_daily_data(stock_code, target_date)
        if daily_data is None:
            return None
        
        stock_info = self.stocks.get(stock_code)
        if stock_info:
            daily_data['stock_name'] = stock_info.stock_name
            daily_data['industry'] = stock_info.industry
        
        return daily_data
    
    def get_top_n_stocks_full(self, target_date: date, n: int) -> List[Dict]:
        """获取排名前N的股票完整数据 (已联表)"""
        top_n = self.get_top_n_by_rank(target_date, n)
        
        for data in top_n:
            stock_info = self.stocks.get(data['stock_code'])
            if stock_info:
                data['stock_name'] = stock_info.stock_name
                data['industry'] = stock_info.industry
        
        return top_n
    
    # ========== 专用接口：策略数据 ==========
    
    def get_stock_data_for_strategy(
        self,
        stock_code: str,
        target_date: date,
        lookback_days: int = 30
    ) -> Optional[StrategyData]:
        """获取策略分析用的完整数据"""
        stock_info = self.stocks.get(stock_code)
        if not stock_info:
            return None
        
        history = self.get_stock_history(stock_code, lookback_days, target_date)
        if not history:
            return None
        
        # 按日期升序排列（最旧到最新）
        history = list(reversed(history))
        
        return StrategyData(
            stock_code=stock_code,
            stock_name=stock_info.stock_name,
            signal_date=target_date.strftime('%Y%m%d'),
            closes=[h['close_price'] for h in history],
            opens=[h['open_price'] for h in history],
            highs=[h['high_price'] for h in history],
            lows=[h['low_price'] for h in history],
            volumes=[h['volume'] for h in history],
            turnovers=[h['turnover_rate'] for h in history],
            ranks=[h['rank'] for h in history],
            price_changes=[h['price_change'] for h in history],
            dates=[h['date'] for h in history],
        )
    
    # ========== 专用接口：聚合计算 ==========
    
    def get_market_volatility_summary(self, days: int = 3) -> Dict:
        """全市场波动率汇总"""
        import numpy as np
        
        dates = self.get_dates_range(days)
        if not dates:
            return {'error': '没有可用数据'}
        
        result_days = []
        
        for d in dates:
            date_idx = self.index_mgr.get_date_idx(d)
            if date_idx is None:
                continue
            
            range_info = self.index_mgr.get_rows_by_date(date_idx)
            if range_info is None:
                continue
            
            start, end = range_info
            slice_data = self.daily_store.data_array[start:end]
            
            volatilities = slice_data['volatility']
            avg_vol = float(np.mean(volatilities[volatilities > 0]))
            
            result_days.append({
                'date': d.strftime('%Y%m%d'),
                'avg_volatility': round(avg_vol, 2),
                'stock_count': end - start,
            })
        
        if not result_days:
            return {'error': '没有有效数据'}
        
        current = result_days[0]['avg_volatility']
        
        # 计算趋势
        if len(result_days) >= 2:
            if current > result_days[1]['avg_volatility']:
                trend = 'up'
            elif current < result_days[1]['avg_volatility']:
                trend = 'down'
            else:
                trend = 'flat'
        else:
            trend = 'flat'
        
        return {
            'current': current,
            'days': result_days,
            'trend': trend,
            'stock_count': result_days[0]['stock_count'],
        }
    
    def get_industry_statistics(self, target_date: date) -> Dict[str, int]:
        """获取行业分布统计"""
        all_data = self.get_all_by_date(target_date)
        
        stats = {}
        for data in all_data:
            stock_info = self.stocks.get(data['stock_code'])
            if stock_info:
                industry = stock_info.industry
                stats[industry] = stats.get(industry, 0) + 1
        
        return stats
    
    def get_rank_statistics(self, target_date: date) -> Dict:
        """获取排名分布统计 (使用numpy加速)"""
        import numpy as np
        
        date_idx = self.index_mgr.get_date_idx(target_date)
        if date_idx is None:
            return {'error': '无数据'}
        
        # 获取该日期的数据范围
        start, end = self.index_mgr.get_date_range(date_idx)
        ranks = self.daily_store.data['rank'][start:end]
        
        # 过滤有效排名
        valid_ranks = ranks[ranks > 0]
        if len(valid_ranks) == 0:
            return {'error': '无有效排名数据'}
        
        return {
            'date': target_date.strftime('%Y%m%d'),
            'total_count': int(len(valid_ranks)),
            'min_rank': int(np.min(valid_ranks)),
            'max_rank': int(np.max(valid_ranks)),
            'mean_rank': float(np.mean(valid_ranks)),
            'median_rank': float(np.median(valid_ranks)),
            'std_rank': float(np.std(valid_ranks)),
            'top100_count': int(np.sum(valid_ranks <= 100)),
            'top500_count': int(np.sum(valid_ranks <= 500)),
            'top1000_count': int(np.sum(valid_ranks <= 1000)),
            'top2000_count': int(np.sum(valid_ranks <= 2000)),
            'top3000_count': int(np.sum(valid_ranks <= 3000)),
        }
    
    # ========== 批量联表查询 ==========
    
    def get_stocks_daily_full_batch(
        self, 
        stock_codes: List[str], 
        target_date: date
    ) -> List[Dict]:
        """批量获取股票完整数据 (基础信息 + 日数据)"""
        daily_batch = self.get_daily_data_batch(stock_codes, target_date)
        
        result = []
        for code, daily_data in daily_batch.items():
            stock_info = self.stocks.get(code)
            if stock_info:
                daily_data['stock_name'] = stock_info.stock_name
                daily_data['industry'] = stock_info.industry
            result.append(daily_data)
        
        return result
    
    def get_sector_daily_full(self, sector_id: int, target_date: date) -> Optional[Dict]:
        """获取板块完整数据 (基础信息 + 日数据)"""
        sector_data = self.get_sector_daily_data(sector_id, target_date)
        if sector_data is None:
            return None
        
        sector_info = self.sectors.get(sector_id)
        if sector_info:
            sector_data['sector_name'] = sector_info.sector_name
        
        return sector_data
    
    def get_top_n_sectors_full(self, target_date: date, n: int) -> List[Dict]:
        """获取排名前N的板块完整数据"""
        top_n = self.get_top_n_sectors(target_date, n)
        
        for data in top_n:
            sector_info = self.sectors.get(data.get('sector_id'))
            if sector_info:
                data['sector_name'] = sector_info.sector_name
        
        return top_n
    
    # ========== 策略数据接口 ==========
    
    def get_stock_data_for_strategy(self, stock_code: str, target_date: date = None, lookback_days: int = 30) -> Optional[Dict]:
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
        
        # 获取历史数据
        history_data = self.get_stock_history(stock_code, lookback_days)
        if not history_data or len(history_data) < 5:
            return None
        
        # 筛选目标日期之前的数据
        filtered_data = []
        for data in history_data:
            data_date = datetime.strptime(data['date'], '%Y%m%d').date()
            if data_date <= target_date:
                filtered_data.append(data)
        
        if len(filtered_data) < 5:
            return None
        
        # 按日期正序排列（历史数据是倒序的）
        filtered_data = list(reversed(filtered_data))
        
        # 收集数据
        closes, highs, lows, opens = [], [], [], []
        volumes, turnovers, ranks, bbis, price_changes = [], [], [], [], []
        target_dates = []
        
        for data in filtered_data:
            closes.append(float(data['close_price']) if data.get('close_price') else 0)
            highs.append(float(data['high_price']) if data.get('high_price') else 0)
            lows.append(float(data['low_price']) if data.get('low_price') else 0)
            opens.append(float(data['open_price']) if data.get('open_price') else 0)
            volumes.append(float(data['volume']) if data.get('volume') else 0)
            turnovers.append(float(data['turnover_rate']) if data.get('turnover_rate') else 0)
            ranks.append(int(data['rank']) if data.get('rank') else 0)
            # BBI用middle_band(布林中轨)代替
            bbis.append(float(data['middle_band']) if data.get('middle_band') else 0)
            # 当天涨跌幅
            price_changes.append(float(data['price_change']) if data.get('price_change') else 0)
            target_dates.append(datetime.strptime(data['date'], '%Y%m%d').date())
        
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
            'price_changes': price_changes,
        }
    
    def get_stocks_data_for_strategy_batch(
        self,
        stock_codes: List[str],
        target_date: date = None,
        lookback_days: int = 30
    ) -> Dict[str, Dict]:
        """批量获取股票策略数据"""
        result = {}
        for code in stock_codes:
            data = self.get_stock_data_for_strategy(code, target_date, lookback_days)
            if data:
                result[code] = data
        return result
    
    # ========== 状态查询 ==========
    
    def get_memory_stats(self) -> Dict:
        """获取内存使用统计"""
        daily_mem = self.daily_store.get_memory_usage()
        sector_mem = self.sector_store.get_memory_usage()
        index_stats = self.index_mgr.get_stats()
        
        return {
            'initialized': self._initialized,
            'stocks_count': len(self.stocks),
            'sectors_count': len(self.sectors),
            'daily_data': daily_mem,
            'sector_data': sector_mem,
            'index_stats': index_stats,
            'total_mb': daily_mem['mb'] + sector_mem['mb'],
        }


# 全局单例
numpy_cache = NumpyCacheMiddleware()
