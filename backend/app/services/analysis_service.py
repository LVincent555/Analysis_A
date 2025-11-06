"""
分析服务
负责股票重复分析相关业务逻辑
"""
from pathlib import Path
from typing import Dict, List
from collections import defaultdict
import logging

from ..models import AnalysisResult, AvailableDates, StockInfo, DateRankInfo
from ..utils import get_sorted_files, cache_manager
from .data_loader import DataLoader

logger = logging.getLogger(__name__)


class AnalysisService:
    """分析服务"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_loader = DataLoader()
    
    def get_available_dates(self) -> AvailableDates:
        """获取可用的日期列表"""
        cache_key = "available_dates"
        cached = cache_manager.get(cache_key)
        if cached:
            return cached
        
        files_with_dates = get_sorted_files(self.data_dir)
        
        if not files_with_dates:
            raise ValueError("未找到数据文件")
        
        dates = [date for date, _ in files_with_dates]
        result = AvailableDates(
            dates=dates,
            latest_date=dates[-1] if dates else ""
        )
        
        cache_manager.set(cache_key, result)
        return result
    
    def analyze_period(self, period: int, filter_stocks: bool = True) -> AnalysisResult:
        """
        分析特定周期的股票重复出现
        
        Args:
            period: 分析周期（天数）
            filter_stocks: 是否过滤特定板块
        
        Returns:
            分析结果
        """
        cache_key = f"analysis_{period}_{filter_stocks}"
        cached = cache_manager.get(cache_key)
        if cached:
            logger.info(f"使用缓存: {cache_key}")
            return cached
        
        logger.info(f"计算新数据: {cache_key}")
        
        files_with_dates = get_sorted_files(self.data_dir)
        
        if not files_with_dates:
            raise ValueError("未找到数据文件")
        
        # 取最新的N天数据
        selected_files = files_with_dates[-period:] if len(files_with_dates) >= period else files_with_dates
        
        # 加载所有日期的股票数据
        all_stocks_data = {}
        stock_names = {}
        stock_industries = {}
        
        for date, file_path in selected_files:
            stocks = self.data_loader.load_stock_data(file_path, filter_stocks=filter_stocks)
            all_stocks_data[date] = {stock['code']: stock['rank'] for stock in stocks}
            for stock in stocks:
                stock_names[stock['code']] = stock['name']
                stock_industries[stock['code']] = stock['industry']
        
        # 统计每个股票出现的次数和排名信息
        stock_appearances = defaultdict(list)
        for date, stocks in all_stocks_data.items():
            for code, rank in stocks.items():
                stock_appearances[code].append((date, rank))
        
        from ..models.stock import DateRankInfo
        repeated_stocks = []
        
        # 获取日期列表
        dates = [date for date, _ in selected_files]
        
        if period == 2:
            # 2天分析：必须在2天都出现（筛选重复热点）
            for code, appearances in stock_appearances.items():
                if len(appearances) >= 2:
                    # 按日期排序
                    appearances.sort(key=lambda x: x[0])
                    
                    date_rank_list = [
                        DateRankInfo(date=date, rank=rank) 
                        for date, rank in appearances
                    ]
                    
                    repeated_stocks.append(StockInfo(
                        code=code,
                        name=stock_names.get(code, code),
                        industry=stock_industries.get(code, "未知"),
                        rank=appearances[-1][1],  # 最新排名
                        count=len(appearances),
                        date_rank_info=date_rank_list
                    ))
            
            # 按出现次数排序
            repeated_stocks.sort(key=lambda x: x.count, reverse=True)
        else:
            # 3天及以上：锚定最新一天，显示最新榜单的股票及其历史
            # 但只显示出现2次及以上的股票
            latest_date = dates[-1] if dates else None
            if latest_date and latest_date in all_stocks_data:
                latest_stocks = all_stocks_data[latest_date]
                
                for code, latest_rank in latest_stocks.items():
                    # 获取该股票在所有日期的出现记录
                    appearances = stock_appearances.get(code, [])
                    
                    # 只显示出现2次及以上的股票
                    if len(appearances) >= 2:
                        appearances.sort(key=lambda x: x[0])
                        
                        date_rank_list = [
                            DateRankInfo(date=date, rank=rank) 
                            for date, rank in appearances
                        ]
                        
                        repeated_stocks.append(StockInfo(
                            code=code,
                            name=stock_names.get(code, code),
                            industry=stock_industries.get(code, "未知"),
                            rank=latest_rank,  # 最新排名
                            count=len(appearances),  # 在分析期间出现的总次数
                            date_rank_info=date_rank_list
                        ))
                
                # 排序：优先按出现次数倒序（3次>2次），然后按最新排名正序
                repeated_stocks.sort(key=lambda x: (-x.count, x.rank))
        
        # 构建结果
        result = AnalysisResult(
            period=period,
            total_stocks=len(repeated_stocks),
            stocks=repeated_stocks,
            start_date=dates[0] if dates else "",
            end_date=dates[-1] if dates else "",
            all_dates=dates  # 添加所有分析日期
        )
        
        cache_manager.set(cache_key, result)
        return result
