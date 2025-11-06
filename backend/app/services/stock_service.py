"""
股票服务
负责个股查询相关业务逻辑
"""
from pathlib import Path
from typing import Optional
import logging

from ..models import StockHistory, DateRankInfo
from ..utils import get_sorted_files, cache_manager
from .data_loader import DataLoader

logger = logging.getLogger(__name__)


class StockService:
    """股票服务"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_loader = DataLoader()
    
    def query_stock_history(self, stock_code: str) -> StockHistory:
        """
        查询个股历史排名数据
        
        Args:
            stock_code: 股票代码
        
        Returns:
            股票历史数据
        """
        # 规范化股票代码（去除前导0用于比较）
        normalized_code = stock_code.lstrip('0')
        
        cache_key = f"stock_{stock_code}"
        cached = cache_manager.get(cache_key)
        if cached:
            logger.info(f"使用缓存: {cache_key}")
            return cached
        
        logger.info(f"查询股票: {stock_code} (规范化: {normalized_code})")
        
        files_with_dates = get_sorted_files(self.data_dir)
        
        if not files_with_dates:
            raise ValueError("未找到数据文件")
        
        # 在所有文件中查找该股票
        date_rank_info = []
        stock_name = ""
        stock_industry = ""
        found_dates = []
        
        for date, file_path in files_with_dates:
            stocks = self.data_loader.load_stock_data(
                file_path,
                filter_stocks=False,
                include_details=True,  # 加载详细技术指标数据
                max_count=None  # 不限制查找范围，查询所有股票
            )
            
            for stock in stocks:
                # 规范化比较：去除前导0
                stock_code_normalized = stock['code'].lstrip('0')
                if stock_code_normalized == normalized_code:
                    if not stock_name:
                        stock_name = stock['name']
                        stock_industry = stock['industry']
                    
                    # 创建DateRankInfo，包含技术指标
                    date_rank_info.append(DateRankInfo(
                        date=date,
                        rank=stock['rank'],
                        price_change=stock.get('price_change', 0.0),
                        turnover_rate=stock.get('turnover_rate', 0.0),
                        volume_days=stock.get('volume_days', 0.0),
                        avg_volume_ratio_50=stock.get('avg_volume_ratio_50', 0.0),
                        volatility=stock.get('volatility', 0.0)
                    ))
                    found_dates.append(date)
                    break
        
        if not date_rank_info:
            raise ValueError(f"未找到股票代码: {stock_code}")
        
        result = StockHistory(
            code=stock_code,
            name=stock_name,
            industry=stock_industry,
            date_rank_info=date_rank_info,
            appears_count=len(date_rank_info),
            dates=found_dates
        )
        
        cache_manager.set(cache_key, result)
        return result
