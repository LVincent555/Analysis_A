"""
排名跳变服务 - Numpy缓存版
使用numpy缓存 + api_cache二级缓存
"""
from typing import List, Optional
import statistics
import logging
from datetime import datetime

from .numpy_cache_middleware import numpy_cache
from .api_cache import api_cache
from ..models.stock import RankJumpResult, RankJumpStock
from ..utils.board_filter import should_filter_stock

logger = logging.getLogger(__name__)

# 缓存TTL: 30分钟
RANK_JUMP_CACHE_TTL = 1800


class RankJumpServiceDB:
    """排名跳变服务（Numpy缓存版）"""
    
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
        
        ✅ 使用numpy缓存 + api_cache二级缓存
        
        Args:
            jump_threshold: 跳变阈值
            board_type: 板块类型 ('all': 全部, 'main': 主板, 'bjs': 北交所)
            sigma_multiplier: σ倍数
            target_date: 指定日期 (YYYYMMDD格式)，不传则使用最新日期
        
        Returns:
            排名跳变结果
        """
        # 获取目标日期
        if target_date:
            target_date_obj = datetime.strptime(target_date, '%Y%m%d').date()
        else:
            target_date_obj = numpy_cache.get_latest_date()
        
        if not target_date_obj:
            return self._empty_result()
        
        date_str = target_date_obj.strftime('%Y%m%d')
        
        # ========== 检查api_cache二级缓存 ==========
        if calculate_signals and signal_thresholds:
            threshold_hash = (
                f"{signal_thresholds.hot_list_mode}_"
                f"{signal_thresholds.hot_list_top}_"
                f"{signal_thresholds.rank_jump_min}_"
                f"{signal_thresholds.steady_rise_days_min}_"
                f"{signal_thresholds.price_surge_min}_"
                f"{signal_thresholds.volume_surge_min}_"
                f"{signal_thresholds.volatility_surge_min}"
            )
            cache_key = f"rank_jump_{jump_threshold}_{board_type}_{sigma_multiplier}_{date_str}_{threshold_hash}"
        else:
            cache_key = f"rank_jump_{jump_threshold}_{board_type}_{sigma_multiplier}_{date_str}"
        
        cached = api_cache.get(cache_key)
        if cached:
            logger.info(f"✨ 缓存命中: {cache_key}")
            return RankJumpResult(**cached)
        
        # ========== 使用numpy缓存计算 ==========
        # 1. 获取最近2天的日期
        all_dates = numpy_cache.get_dates_range(5)
        target_dates = [d for d in all_dates if d <= target_date_obj][:2]
        
        if len(target_dates) < 2:
            return self._empty_result()
        
        date1, date2 = target_dates[0], target_dates[1]  # 新->旧
        date1_str = date1.strftime('%Y%m%d')
        date2_str = date2.strftime('%Y%m%d')
        
        # 2. 从numpy缓存获取两天的数据
        day1_data = {}  # {stock_code: {rank, name, industry, indicators}}
        day2_data = {}  # {stock_code: rank}
        
        # 批量获取第一天数据
        all_daily1 = numpy_cache.get_all_by_date(date1)
        for daily in all_daily1:
            stock_code = daily.get('stock_code')
            if not stock_code:
                continue
            stock_info = numpy_cache.get_stock_info(stock_code)
            day1_data[stock_code] = {
                'rank': daily.get('rank', 9999),
                'name': stock_info.stock_name if stock_info else '',
                'industry': stock_info.industry if stock_info else '未知',
                'price_change': daily.get('price_change'),
                'turnover_rate': daily.get('turnover_rate'),
                'volatility': daily.get('volatility')
            }
        
        # 批量获取第二天数据
        all_daily2 = numpy_cache.get_all_by_date(date2)
        for daily in all_daily2:
            stock_code = daily.get('stock_code')
            if stock_code:
                day2_data[stock_code] = daily.get('rank', 9999)
        
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
                        turnover_rate=info['turnover_rate'],
                        volatility=info['volatility']
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
        
        # ========== 存入api_cache二级缓存 ==========
        api_cache.set(cache_key, result.model_dump(), ttl=RANK_JUMP_CACHE_TTL)
        logger.info(f"✓ 排名跳变分析完成并缓存: {len(jump_stocks)}只股票")
        
        return result
    
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
