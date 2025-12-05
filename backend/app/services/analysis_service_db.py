"""
热点分析服务 - Numpy缓存版

v0.5.0: 使用统一缓存系统
"""
from typing import List, Dict, Optional
from datetime import datetime
from collections import Counter, defaultdict
import logging
import ast

from ..database import SessionLocal
from ..db_models import Stock, DailyStockData
from ..models.analysis import AnalysisResult
from ..models.stock import StockInfo
from ..utils.board_filter import should_filter_stock
from .numpy_cache_middleware import numpy_cache
from ..core.caching import cache  # v0.5.0: 统一缓存
from sqlalchemy import desc

logger = logging.getLogger(__name__)


class AnalysisServiceDB:
    """热点分析服务（内存缓存版）"""
    
    # v0.5.0: 缓存TTL改为25小时
    CACHE_TTL = 90000
    CACHE_PREFIX = 'analysis'
    
    def __init__(self):
        """初始化服务"""
        pass  # 使用全局 api_cache
    
    def get_db(self):
        """获取数据库会话（仅在必要时使用）"""
        return SessionLocal()
    
    def get_available_dates(self) -> List[str]:
        """获取可用日期列表（从Numpy缓存）"""
        return numpy_cache.get_available_dates()
    
    def analyze_period(
        self,
        period: int = 3,
        max_count: int = 100,
        board_type: str = 'main',
        target_date: Optional[str] = None
    ) -> AnalysisResult:
        """
        周期热点分析
        
        逻辑：
        1. 简单SQL：获取最近N天的所有数据
        2. 后端计算：统计每只股票出现次数
        3. 后端计算：筛选和排序
        
        Args:
            period: 分析周期（天数）
            max_count: 最大返回数量
            board_type: 板块类型 ('all': 全部, 'main': 主板, 'bjs': 北交所)
            target_date: 指定日期 (YYYYMMDD格式)，不传则使用最新日期
        
        Returns:
            分析结果
        """
        # v0.5.0: 使用统一缓存系统
        cache_key = f"analyze_{period}_{max_count}_{board_type}_{target_date}"
        cached = cache.get_api_cache("analysis", cache_key)
        if cached is not None:
            logger.info(f"✨ 缓存命中: {cache_key}")
            return cached
        
        logger.info(f"🔄 计算热点分析: period={period}, max_count={max_count}, board_type={board_type}")
        
        # 1. 从内存获取日期范围
        if target_date:
            target_date_obj = datetime.strptime(target_date, '%Y%m%d').date()
        else:
            target_date_obj = numpy_cache.get_latest_date()
        
        if not target_date_obj:
            return AnalysisResult(
                period=period,
                total_stocks=0,
                stocks=[],
                start_date="",
                end_date="",
                all_dates=[]
            )
        
        # 获取最近N天日期
        all_dates = numpy_cache.get_dates_range(period * 2)  # 多取一些以防不够
        target_dates = [d for d in all_dates if d <= target_date_obj][:period]
        
        if not target_dates:
            return AnalysisResult(
                period=period,
                total_stocks=0,
                stocks=[],
                start_date="",
                end_date="",
                all_dates=[]
            )
        
        date_strs = [d.strftime('%Y%m%d') for d in target_dates]
        latest_date = target_dates[0]  # 最新日期
        
        # 2. 从Numpy缓存获取最新日期的TOP N股票（锚定）
        latest_top_stocks = numpy_cache.get_top_n_by_rank(latest_date, max_count)
        
        # 获取锚定股票的代码列表（应用板块过滤）
        anchor_stocks = set()
        for stock_data in latest_top_stocks:
            if should_filter_stock(stock_data['stock_code'], board_type):
                continue
            anchor_stocks.add(stock_data['stock_code'])
        
        # 3. 从内存获取这些锚定股票在所有日期的数据
        stock_appearances = defaultdict(lambda: {
            'code': '',
            'name': '',
            'industry': '',
            'dates': [],
            'date_rank_info': []
        })
        
        for target_date_item in target_dates:
            # 获取该日期的所有数据 (返回Dict列表)
            daily_stocks = numpy_cache.get_all_by_date(target_date_item)
            
            for stock_data in daily_stocks:
                code = stock_data['stock_code']
                rank = stock_data['rank'] if stock_data['rank'] is not None else 9999
                
                # 只处理锚定的股票，且在TOP范围内
                if code not in anchor_stocks or rank > max_count:
                    continue
                
                # 获取股票基础信息
                if not stock_appearances[code]['code']:
                    stock_info = numpy_cache.get_stock_info(code)
                    if stock_info:
                        # 处理行业字段
                        industry = stock_info.industry
                        if isinstance(industry, list) and industry:
                            industry = industry[0]
                        elif isinstance(industry, str):
                            if industry.startswith('[') and industry.endswith(']'):
                                try:
                                    industry_list = ast.literal_eval(industry)
                                    industry = industry_list[0] if industry_list else '未知'
                                except:
                                    industry = industry.strip('[]').strip("'\"")
                            elif not industry:
                                industry = '未知'
                        else:
                            industry = '未知'
                        
                        stock_appearances[code]['code'] = code
                        stock_appearances[code]['name'] = stock_info.stock_name
                        stock_appearances[code]['industry'] = industry
                
                # 记录出现信息
                date_str = target_date_item.strftime('%Y%m%d')
                stock_appearances[code]['dates'].append(date_str)
                stock_appearances[code]['date_rank_info'].append({
                    'date': date_str,
                    'rank': rank,
                    'price_change': stock_data['price_change'],
                    'turnover_rate': stock_data['turnover_rate'],
                    'volatility': stock_data['volatility'],
                })
        
        # 4. 构建结果列表
        stocks_list = []
        for stock_data in stock_appearances.values():
            appears_count = len(stock_data['dates'])
            
            # 过滤：只保留出现次数>=2的股票
            if appears_count < 2:
                continue
            
            # 对date_rank_info按日期排序（从旧到新）
            sorted_date_rank_info = sorted(
                stock_data['date_rank_info'], 
                key=lambda x: x['date']
            )
            
            # 最新排名（排序后的最后一条记录）
            latest_rank = sorted_date_rank_info[-1]['rank']
            
            stocks_list.append(StockInfo(
                code=stock_data['code'],
                name=stock_data['name'],
                industry=stock_data['industry'],
                rank=latest_rank,
                count=appears_count,
                date_rank_info=sorted_date_rank_info
            ))
        
        # 按出现次数排序（从多到少）
        stocks_list.sort(key=lambda x: x.count, reverse=True)
        
        # 5. 后端计算：行业统计
        industry_counter = Counter(s.industry for s in stocks_list)
        industry_stats = [
            {"industry": industry, "count": count}
            for industry, count in industry_counter.most_common(10)
        ]
            
        # 6. 构建结果并缓存
        result = AnalysisResult(
            period=period,
            total_stocks=len(stocks_list),
            stocks=stocks_list,
            start_date=date_strs[0] if date_strs else "",
            end_date=date_strs[-1] if date_strs else "",
            all_dates=date_strs
        )
        
        # v0.5.0: 使用统一缓存系统
        cache.set_api_cache("analysis", cache_key, result, ttl=self.CACHE_TTL)
        logger.info(f"✅ 热点分析完成并缓存: {len(stocks_list)}只股票, key={cache_key}")
        
        return result


# 全局实例
analysis_service_db = AnalysisServiceDB()
