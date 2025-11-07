"""
热点分析服务 - 数据库版
简单SQL查询 + 后端计算逻辑
"""
from typing import List, Dict, Optional
from datetime import datetime
from collections import Counter
import logging
import ast

from ..database import SessionLocal
from ..db_models import Stock, DailyStockData
from ..models.analysis import AnalysisResult
from ..models.stock import StockInfo
from ..utils.board_filter import should_filter_stock
from sqlalchemy import desc

logger = logging.getLogger(__name__)


class AnalysisServiceDB:
    """热点分析服务（数据库版）"""
    
    def get_db(self):
        """获取数据库会话"""
        return SessionLocal()
    
    def get_available_dates(self) -> List[str]:
        """获取可用日期列表"""
        db = self.get_db()
        try:
            # 简单SQL：查询所有不同的日期
            dates = db.query(DailyStockData.date)\
                .distinct()\
                .order_by(desc(DailyStockData.date))\
                .all()
            
            return [d[0].strftime('%Y%m%d') for d in dates]
        finally:
            db.close()
    
    def analyze_period(
        self,
        period: int = 3,
        max_count: int = 100,
        board_type: str = 'main'
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
        
        Returns:
            分析结果
        """
        # 添加详细日志
        print(f"\n🔍 Service层收到参数:")
        print(f"   period={period}")
        print(f"   max_count={max_count}")
        print(f"   board_type={board_type}")
        print()
        
        db = self.get_db()
        try:
            # 1. 获取最近N天的日期
            dates = db.query(DailyStockData.date)\
                .distinct()\
                .order_by(desc(DailyStockData.date))\
                .limit(period)\
                .all()
            
            if not dates:
                return AnalysisResult(
                    period=period,
                    total_stocks=0,
                    stocks=[],
                    start_date="",
                    end_date="",
                    all_dates=[]
                )
            
            target_dates = [d[0] for d in dates]
            date_strs = [d.strftime('%Y%m%d') for d in target_dates]
            latest_date = target_dates[0]  # 最新日期
            
            # 2. 锚定最新日期：先查询最新日期的TOP N股票
            latest_query = db.query(DailyStockData, Stock)\
                .join(Stock, DailyStockData.stock_code == Stock.stock_code)\
                .filter(DailyStockData.date == latest_date)\
                .filter(DailyStockData.rank <= max_count)\
                .order_by(DailyStockData.rank)
            
            latest_results = latest_query.all()
            
            # 获取锚定股票的代码列表
            anchor_stocks = set()
            for daily_data, stock in latest_results:
                code = stock.stock_code
                # 后端板块筛选逻辑
                if should_filter_stock(code, board_type):
                    continue
                anchor_stocks.add(code)
            
            # 3. 查询所有日期的这些锚定股票的数据
            query = db.query(DailyStockData, Stock)\
                .join(Stock, DailyStockData.stock_code == Stock.stock_code)\
                .filter(DailyStockData.date.in_(target_dates))\
                .filter(DailyStockData.stock_code.in_(anchor_stocks))\
                .filter(DailyStockData.rank <= max_count)\
                .order_by(DailyStockData.date.desc(), DailyStockData.rank)
            
            results = query.all()
            
            # 4. 统计每只股票的出现次数（只统计锚定的股票）
            stock_appearances = {}
            
            for daily_data, stock in results:
                code = stock.stock_code
                
                if code not in stock_appearances:
                    # 处理行业字段（可能是数组、字符串或字符串形式的数组）
                    industry = stock.industry
                    if isinstance(industry, list) and industry:
                        industry = industry[0]  # 真正的数组，取第一个元素
                    elif isinstance(industry, str):
                        # 处理字符串形式的数组，如 "['电网设备']"
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
                    
                    stock_appearances[code] = {
                        'code': code,
                        'name': stock.stock_name,
                        'industry': industry,
                        'dates': [],
                        'date_rank_info': []
                    }
                
                date_str = daily_data.date.strftime('%Y%m%d')
                stock_appearances[code]['dates'].append(date_str)
                stock_appearances[code]['date_rank_info'].append({
                    'date': date_str,
                    'rank': daily_data.rank,
                    'price_change': float(daily_data.price_change) if daily_data.price_change else None,
                    'turnover_rate': float(daily_data.turnover_rate_percent) if daily_data.turnover_rate_percent else None,
                })
            
            # 5. 构建结果列表
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
            
            # 6. 后端计算：行业统计
            industry_counter = Counter(s.industry for s in stocks_list)
            industry_stats = [
                {"industry": industry, "count": count}
                for industry, count in industry_counter.most_common(10)
            ]
            
            # 构建结果
            result = AnalysisResult(
                period=period,
                total_stocks=len(stocks_list),
                stocks=stocks_list,
                start_date=date_strs[0] if date_strs else "",
                end_date=date_strs[-1] if date_strs else "",
                all_dates=date_strs
            )
            
            logger.info(f"分析完成: period={period}, max_count={max_count}, 股票数={len(stocks_list)}")
            
            return result
            
        finally:
            db.close()


# 全局实例
analysis_service_db = AnalysisServiceDB()
