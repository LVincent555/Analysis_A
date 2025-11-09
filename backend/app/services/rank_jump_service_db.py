"""
排名跳变服务 - 数据库版
简单SQL查询 + 后端计算
"""
from typing import List, Optional
import statistics
import logging

from ..database import SessionLocal
from ..db_models import Stock, DailyStockData
from ..models.stock import RankJumpResult, RankJumpStock
from ..utils.board_filter import should_filter_stock
from sqlalchemy import desc

logger = logging.getLogger(__name__)


class RankJumpServiceDB:
    """排名跳变服务（数据库版）"""
    
    def __init__(self):
        """初始化"""
        self.cache = {}
    
    def get_db(self):
        """获取数据库会话"""
        return SessionLocal()
    
    def analyze_rank_jump(
        self,
        jump_threshold: int = 2500,
        board_type: str = 'main',
        sigma_multiplier: float = 1.0,
        target_date: Optional[str] = None,
        calculate_signals: bool = False,
        signal_thresholds = None
    ) -> RankJumpResult:
        """
        排名跳变分析
        
        逻辑：
        1. 简单SQL：获取最近2天的数据
        2. 后端计算：匹配同一股票的两天排名
        3. 后端计算：计算排名变化
        4. 后端计算：统计和筛选
        
        Args:
            jump_threshold: 跳变阈值
            board_type: 板块类型 ('all': 全部, 'main': 主板, 'bjs': 北交所)
            sigma_multiplier: σ倍数
            target_date: 指定日期 (YYYYMMDD格式)，不传则使用最新日期
        
        Returns:
            排名跳变结果
        """
        # 缓存键包含target_date和signal配置，避免不同参数返回相同数据
        if calculate_signals and signal_thresholds:
            threshold_hash = f"{signal_thresholds.rank_jump_min}_{signal_thresholds.hot_list_top}"
            cache_key = f"rank_jump_{jump_threshold}_{board_type}_{sigma_multiplier}_{target_date}_{threshold_hash}"
        else:
            cache_key = f"rank_jump_{jump_threshold}_{board_type}_{sigma_multiplier}_{target_date}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        db = self.get_db()
        try:
            # 1. 简单SQL：获取最近2天的日期
            # 如果指定target_date，获取该日期和前一天
            from datetime import datetime
            if target_date:
                target_date_obj = datetime.strptime(target_date, '%Y%m%d').date()
                recent_dates = db.query(DailyStockData.date)\
                    .distinct()\
                    .filter(DailyStockData.date <= target_date_obj)\
                    .order_by(desc(DailyStockData.date))\
                    .limit(2)\
                    .all()
            else:
                recent_dates = db.query(DailyStockData.date)\
                    .distinct()\
                    .order_by(desc(DailyStockData.date))\
                    .limit(2)\
                    .all()
            
            if len(recent_dates) < 2:
                return self._empty_result()
            
            date1, date2 = recent_dates[0][0], recent_dates[1][0]  # 新->旧
            date1_str = date1.strftime('%Y%m%d')
            date2_str = date2.strftime('%Y%m%d')
            
            # 2. 简单SQL：分别查询两天的数据（包含技术指标）
            day1_data = {}  # {stock_code: {rank, name, industry, indicators}}
            query1 = db.query(
                DailyStockData.stock_code, 
                DailyStockData.rank, 
                Stock.stock_name, 
                Stock.industry,
                DailyStockData.price_change,
                DailyStockData.turnover_rate_percent
            ).join(Stock, DailyStockData.stock_code == Stock.stock_code)\
             .filter(DailyStockData.date == date1)
            
            for code, rank, name, industry, price_change, turnover_rate in query1.all():
                day1_data[code] = {
                    'rank': rank, 
                    'name': name, 
                    'industry': industry or '未知',
                    'price_change': float(price_change) if price_change else None,
                    'turnover_rate': float(turnover_rate) if turnover_rate else None
                }
            
            day2_data = {}
            query2 = db.query(DailyStockData.stock_code, DailyStockData.rank)\
                .filter(DailyStockData.date == date2)
            
            for code, rank in query2.all():
                day2_data[code] = rank
            
            # 3. 后端计算：找出排名跳变的股票
            jump_stocks = []
            for code, info in day1_data.items():
                if code in day2_data:
                    rank_change = day2_data[code] - info['rank']  # 正数=向前跳
                    
                    # 后端板块筛选逻辑
                    if should_filter_stock(code, board_type):
                        continue
                    
                    # 只保留向前跳的股票（rank_change > 0）
                    if rank_change >= jump_threshold:
                        jump_stocks.append(RankJumpStock(
                            code=code,
                            name=info['name'],
                            industry=info['industry'],
                            latest_rank=info['rank'],
                            previous_rank=day2_data[code],
                            rank_change=rank_change,
                            latest_date=date1_str,
                            previous_date=date2_str,
                            price_change=info['price_change'],
                            turnover_rate=info['turnover_rate']
                        ))
            
            if not jump_stocks:
                return self._empty_result()
            
            # 4. 后端计算：统计（现在都是正值，直接计算）
            rank_changes = [s.rank_change for s in jump_stocks]
            mean_rank_change = statistics.mean(rank_changes)
            std_rank_change = statistics.stdev(rank_changes) if len(rank_changes) > 1 else 0
            
            # 5. 后端计算：±σ筛选
            lower_bound = max(0, mean_rank_change - std_rank_change * sigma_multiplier)  # 确保>=0
            upper_bound = mean_rank_change + std_rank_change * sigma_multiplier
            
            sigma_stocks = [
                stock for stock in jump_stocks
                if lower_bound <= stock.rank_change <= upper_bound
            ]
            
            # 构建结果
            result = RankJumpResult(
                latest_date=date1_str,
                previous_date=date2_str,
                jump_threshold=jump_threshold,
                total_count=len(jump_stocks),
                stocks=jump_stocks,
                mean_rank_change=mean_rank_change,
                std_rank_change=std_rank_change,
                sigma_range=[lower_bound, upper_bound],
                sigma_stocks=sigma_stocks
            )
            
            self.cache[cache_key] = result
            logger.info(f"排名跳变分析完成: {len(jump_stocks)}只股票")
            
            return result
            
        finally:
            db.close()
    
    def _empty_result(self) -> RankJumpResult:
        """空结果"""
        return RankJumpResult(
            latest_date="",
            previous_date="",
            jump_threshold=0,
            total_count=0,
            stocks=[],
            mean_rank_change=0,
            std_rank_change=0,
            sigma_range=[0, 0],
            sigma_stocks=[]
        )


# 全局实例
rank_jump_service_db = RankJumpServiceDB()
