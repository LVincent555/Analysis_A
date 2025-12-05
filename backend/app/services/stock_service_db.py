"""
股票服务 - Numpy缓存版
使用numpy_cache替代memory_cache，大幅提升性能并减少内存占用

v0.5.0: 使用统一缓存系统
"""
from typing import Optional
from datetime import datetime, timedelta
import logging

from ..database import SessionLocal
from ..db_models import Stock, DailyStockData
from ..models.stock import StockHistory, StockFullHistory, StockDailyFull
from .numpy_cache_middleware import numpy_cache
from ..core.caching import cache  # v0.5.0: 统一缓存
from sqlalchemy import desc, or_

logger = logging.getLogger(__name__)


class StockServiceDB:
    """股票服务（内存缓存版）"""
    
    CACHE_TTL = 1800  # 30分钟
    
    def __init__(self):
        """初始化服务"""
        pass  # 使用全局 api_cache
    
    def get_db(self):
        """获取数据库会话"""
        return SessionLocal()

    def _convert_to_daily_full(self, data: DailyStockData) -> StockDailyFull:
        """将DailyStockData转换为StockDailyFull"""
        # 使用字典推导式快速转换，注意处理DECIMAL转float
        def to_float(val):
            return float(val) if val is not None else None
            
        def to_int(val):
            return int(val) if val is not None else None

        return StockDailyFull(
            date=data.date.strftime('%Y%m%d'),
            rank=data.rank,
            
            # 基础价格
            open_price=to_float(data.open_price),
            high_price=to_float(data.high_price),
            low_price=to_float(data.low_price),
            close_price=to_float(data.close_price),
            price_change=to_float(data.price_change),
            total_score=to_float(data.total_score),
            
            # 成交量
            volume=data.volume,
            turnover_rate_percent=to_float(data.turnover_rate_percent),
            volume_days=to_float(data.volume_days),
            avg_volume_ratio_50=to_float(data.avg_volume_ratio_50),
            volume_days_volume=to_float(data.volume_days_volume),
            avg_volume_ratio_50_volume=to_float(data.avg_volume_ratio_50_volume),
            obv=data.obv,
            obv_consec=data.obv_consec,
            obv_2=data.obv_2,
            
            # 波动率
            volatility=to_float(data.volatility),
            volatile_consec=data.volatile_consec,
            beta=to_float(data.beta),
            beta_consec=data.beta_consec,
            correlation=to_float(data.correlation),
            
            # 市场
            market_cap_billions=to_float(data.market_cap_billions),
            jump=to_float(data.jump),
            
            # 趋势
            long_term=to_float(data.long_term),
            short_term=data.short_term,
            overbought=data.overbought,
            oversold=data.oversold,
            
            # MACD
            macd_signal=to_float(data.macd_signal),
            dif_dem=to_float(data.dif_dem),
            macd_consec=data.macd_consec,
            dif_0=to_float(data.dif_0),
            macdcons_consec=data.macdcons_consec,
            dem_0=to_float(data.dem_0),
            demcons_consec=data.demcons_consec,
            histgram=to_float(data.histgram),
            dif=to_float(data.dif),
            dem=to_float(data.dem),
            
            # LON
            lon_lonma=to_float(data.lon_lonma),
            lon_consec=data.lon_consec,
            lon_0=to_float(data.lon_0),
            loncons_consec=data.loncons_consec,
            lonma_0=to_float(data.lonma_0),
            lonmacons_consec=data.lonmacons_consec,
            lon_lonma_diff=to_float(data.lon_lonma_diff),
            lon=to_float(data.lon),
            lonma=to_float(data.lonma),
            
            # KDJ
            slowkdj_signal=to_float(data.slowkdj_signal),
            k_kdj=to_float(data.k_kdj),
            slowkdj_consec=data.slowkdj_consec,
            slowk=to_float(data.slowk),
            
            # DMA
            dma=to_float(data.dma),
            dma_consec=data.dma_consec,
            
            # DMI
            pdi_adx=to_float(data.pdi_adx),
            dmiadx_consec=data.dmiadx_consec,
            pdi_ndi=to_float(data.pdi_ndi),
            dmi_consec=data.dmi_consec,
            adx=to_float(data.adx),
            plus_di=to_float(data.plus_di),
            
            # RSI
            rsi=to_float(data.rsi),
            rsi_consec=data.rsi_consec,
            rsi_2=to_float(data.rsi_2),
            
            # CCI
            cci_neg_90=to_float(data.cci_neg_90),
            cci_lower_consec=data.cci_lower_consec,
            cci_pos_90=to_float(data.cci_pos_90),
            cci_upper_consec=data.cci_upper_consec,
            cci_neg_90_2=to_float(data.cci_neg_90_2),
            cci_pos_90_2=to_float(data.cci_pos_90_2),
            
            # BOLL
            bands_lower=to_float(data.bands_lower),
            bands_lower_consec=data.bands_lower_consec,
            bands_middle=to_float(data.bands_middle),
            bands_middle_consec=data.bands_middle_consec,
            bands_upper=to_float(data.bands_upper),
            bands_upper_consec=data.bands_upper_consec,
            lower_band=to_float(data.lower_band),
            middle_band=to_float(data.middle_band),
            upper_band=to_float(data.upper_band),
            
            # 其他
            lst_close=to_float(data.lst_close),
            code2=data.code2,
            name2=data.name2,
            zhangdiefu2=to_float(data.zhangdiefu2),
            volume_consec2=to_float(data.volume_consec2),
            volume_50_consec2=to_float(data.volume_50_consec2)
        )

    def search_stock_full(self, keyword: str, limit: int = 5) -> list[StockFullHistory]:
        """
        搜索股票并返回全量历史数据（需要完整83个指标，使用数据库查询）
        
        Args:
            keyword: 搜索关键词（代码或名称）
            limit: 返回的最大股票数量（防止数据量过大）
            
        Returns:
            List[StockFullHistory]
        """
        keyword_lower = keyword.lower()
        matched_stocks = []
        
        # 1. 搜索匹配的股票 (使用numpy_cache)
        all_stocks = numpy_cache.get_all_stocks()
        
        # 先尝试精确匹配
        if keyword in all_stocks:
            matched_stocks.append(all_stocks[keyword])
        
        # 如果没找到或者需要更多，进行模糊匹配
        if len(matched_stocks) < limit:
            for code, stock in all_stocks.items():
                if code == keyword:  # 已经添加过了
                    continue
                    
                if keyword_lower in code.lower() or (stock.stock_name and keyword_lower in stock.stock_name.lower()):
                    matched_stocks.append(stock)
                    if len(matched_stocks) >= limit:
                        break
        
        if not matched_stocks:
            return []
            
        # 2. 使用数据库查询获取全量历史数据（包含完整83个指标）
        results = []
        db = SessionLocal()
        try:
            for stock in matched_stocks:
                # 从数据库查询完整数据
                daily_data = db.query(DailyStockData).filter(
                    DailyStockData.stock_code == stock.stock_code
                ).order_by(desc(DailyStockData.date)).all()
                
                if not daily_data:
                    continue
                    
                # 转换为全量模型
                full_daily_list = [self._convert_to_daily_full(data) for data in daily_data]
                
                results.append(StockFullHistory(
                    code=stock.stock_code,
                    name=stock.stock_name,
                    industry=stock.industry or '未知',
                    total_count=len(full_daily_list),
                    daily_data=full_daily_list
                ))
        finally:
            db.close()
            
        return results
    
    def search_stock(self, keyword: str, target_date: Optional[str] = None, signal_thresholds=None) -> Optional[StockHistory]:
        """
        搜索股票（从内存缓存）
        
        Args:
            keyword: 股票代码或名称
            target_date: 指定日期 (YYYYMMDD格式)
            signal_thresholds: 信号配置
        
        Returns:
            股票历史数据
        """
        # 缓存key（包含信号配置）
        if signal_thresholds:
            threshold_hash = (
                f"{signal_thresholds.hot_list_mode}_"
                f"{signal_thresholds.hot_list_top}_"
                f"{signal_thresholds.rank_jump_min}_"
                f"{signal_thresholds.steady_rise_days_min}_"
                f"{signal_thresholds.price_surge_min}_"
                f"{signal_thresholds.volume_surge_min}_"
                f"{signal_thresholds.volatility_surge_min}"
            )
            cache_key = f"stock_{keyword}_{target_date}_{threshold_hash}"
        else:
            cache_key = f"stock_{keyword}_{target_date}_default"
        
        # v0.5.0: 使用统一缓存系统
        cached = cache.get_api_cache("stock_search", cache_key)
        if cached is not None:
            logger.info(f"✨ 缓存命中: {cache_key}")
            return cached
        
        logger.info(f"🔄 搜索股票: {keyword}")
        
        # 1. 从Numpy缓存中查找股票
        keyword_lower = keyword.lower()
        stock_info = None
        stock_code = None
        
        # 先精确匹配代码
        all_stocks = numpy_cache.get_all_stocks()
        if keyword in all_stocks:
            stock_code = keyword
            stock_info = numpy_cache.get_stock_info(keyword)
        else:
            # 模糊匹配代码或名称
            for code, stock in all_stocks.items():
                if (keyword_lower in code.lower() or 
                    (stock.stock_name and keyword_lower in stock.stock_name.lower())):
                    stock_code = code
                    stock_info = stock
                    break
        
        if not stock_info or not stock_code:
            return None
        
        # 2. 从Numpy缓存获取历史数据（30天）
        if target_date:
            target_date_obj = datetime.strptime(target_date, '%Y%m%d').date()
        else:
            target_date_obj = numpy_cache.get_latest_date()
        
        if not target_date_obj:
            return None
        
        # 获取该股票的历史数据 (返回Dict列表，按日期降序)
        history_data = numpy_cache.get_stock_history(stock_code, 30, target_date_obj)
        
        if not history_data:
            return None
        
        # 3. 组装日期排名信息（反转为升序：旧→新，图表需要这个顺序）
        date_rank_info = []
        for data in reversed(history_data):  # 反转：降序变升序
            info = {
                'date': data['date'],
                'rank': data['rank'],
                'price_change': data['price_change'],
                'turnover_rate': data['turnover_rate'],
                'volume_days': data['volume_days'],
                'avg_volume_ratio_50': data['avg_volume_ratio_50'],
                'volatility': data['volatility'],
            }
            date_rank_info.append(info)
        
        # 4. 计算信号（最新日期）
        # SignalCalculator 现已迁移到 numpy_cache
        signals = []
        if history_data:
            from .signal_calculator import SignalCalculator
            from datetime import datetime as dt
            
            latest_date_str = history_data[0]['date']
            latest_date_obj = dt.strptime(latest_date_str, '%Y%m%d').date()
            
            # 从 numpy_cache 获取 Dict 数据用于信号计算
            latest_data = numpy_cache.get_daily_data(stock_code, latest_date_obj)
            
            if latest_data:
                calculator = SignalCalculator(signal_thresholds)
                signal_result = calculator.calculate_signals(
                    stock_code=stock_code,
                    current_date=latest_date_obj,
                    current_data=latest_data,  # 现在是 Dict
                    history_days=7
                )
                signals = signal_result.get('signals', [])
        
        # 5. 构建结果并缓存
        result = StockHistory(
            code=stock_info.stock_code,
            name=stock_info.stock_name,
            industry=stock_info.industry or '未知',
            date_rank_info=date_rank_info,
            appears_count=len(date_rank_info),
            dates=[info['date'] for info in date_rank_info],
            signals=signals
        )
        
        # v0.5.0: 使用统一缓存系统
        cache.set_api_cache("stock_search", cache_key, result, ttl=self.CACHE_TTL)
        logger.info(f"✅ 股票查询完成: {stock_info.stock_name}")
        
        return result


# 全局实例
stock_service_db = StockServiceDB()
