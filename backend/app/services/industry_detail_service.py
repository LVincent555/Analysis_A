"""
板块成分股详细分析服务
提供板块成分股查询、信号计算、趋势分析等功能
"""
import logging
from typing import List, Optional, Dict
from datetime import date, datetime
from collections import defaultdict

from ..models.industry_detail import (
    StockSignalInfo, IndustryStocksResponse, IndustryDetailResponse,
    IndustryTrendResponse, IndustryCompareResponse
)
from ..utils.ttl_cache import TTLCache
from .memory_cache import memory_cache
from .signal_calculator import SignalCalculator, SignalThresholds

logger = logging.getLogger(__name__)


class IndustryDetailService:
    """板块成分股详细分析服务"""
    
    def __init__(self):
        """初始化缓存"""
        self.cache = TTLCache(default_ttl_seconds=1800)  # 30分钟缓存
    
    def get_industry_stocks(
        self,
        industry_name: str,
        target_date: Optional[str] = None,
        sort_mode: str = "rank",
        calculate_signals: bool = True,
        signal_thresholds: Optional[SignalThresholds] = None
    ) -> Optional[IndustryStocksResponse]:
        """
        获取板块成分股列表（完整版，Phase 2）
        
        Args:
            industry_name: 板块名称（如：食品、建材）
            target_date: 目标日期 YYYYMMDD，默认最新日期
            sort_mode: 排序模式 rank|score|price_change|volume|signal
            calculate_signals: 是否计算信号（Phase 2功能）
            signal_thresholds: 信号阈值配置，None使用默认值
        
        Returns:
            板块成分股列表响应
        """
        # 缓存key（包含信号计算标志和阈值配置）
        # 如果开启信号计算，缓存key需要包含阈值配置，否则修改配置后仍返回旧结果
        if calculate_signals and signal_thresholds:
            logger.info(f"📊 信号配置: mode={signal_thresholds.hot_list_mode}, version={signal_thresholds.hot_list_version}")
            threshold_hash = (
                f"{signal_thresholds.hot_list_mode}_"
                f"{signal_thresholds.hot_list_version}_"
                f"{signal_thresholds.hot_list_top}_"
                f"{signal_thresholds.rank_jump_min}_"
                f"{signal_thresholds.steady_rise_days_min}_"
                f"{signal_thresholds.price_surge_min}_"
                f"{signal_thresholds.volume_surge_min}_"
                f"{signal_thresholds.volatility_surge_min}"
            )
            cache_key = f"industry_stocks_{industry_name}_{target_date}_{sort_mode}_{calculate_signals}_{threshold_hash}"
        else:
            cache_key = f"industry_stocks_{industry_name}_{target_date}_{sort_mode}_{calculate_signals}"
        
        if cache_key in self.cache:
            logger.info(f"✨ 缓存命中: {cache_key}")
            return self.cache[cache_key]
        
        logger.info(f"🔄 查询板块成分股: {industry_name}, 日期: {target_date}, 排序: {sort_mode}")
        
        # 1. 确定查询日期
        if target_date:
            query_date = datetime.strptime(target_date, '%Y%m%d').date()
        else:
            query_date = memory_cache.get_latest_date()
        
        if not query_date:
            logger.warning("无可用日期")
            return None
        
        # 2. 从内存缓存获取该日期的所有数据
        all_stocks = memory_cache.get_daily_data_by_date(query_date)
        if not all_stocks:
            logger.warning(f"日期 {query_date} 无数据")
            return None
        
        # 3. 筛选该板块的股票
        industry_stocks = []
        for stock_data in all_stocks:
            stock_info = memory_cache.get_stock_info(stock_data.stock_code)
            if stock_info and stock_info.industry:
                # 处理行业字段（可能是列表格式）
                industry = stock_info.industry
                if isinstance(industry, list) and industry:
                    industry = industry[0]
                elif isinstance(industry, str) and industry:
                    if industry.startswith('['):
                        try:
                            import ast
                            industry_list = ast.literal_eval(industry)
                            industry = industry_list[0] if industry_list else None
                        except:
                            industry = industry.strip('[]').strip("'\"")
                
                # 匹配行业名称
                if industry == industry_name:
                    industry_stocks.append((stock_info, stock_data))
        
        if not industry_stocks:
            logger.warning(f"板块 {industry_name} 无成分股")
            return None
        
        logger.info(f"  找到 {len(industry_stocks)} 只成分股")
        
        # 4. 初始化信号计算器（如果需要）
        signal_calculator = None
        if calculate_signals:
            signal_calculator = SignalCalculator(signal_thresholds)
            logger.info(f"  计算信号中...")
        
        # 5. 构建响应数据（完整版，包含信号）
        stocks_list = []
        for stock_info, stock_data in industry_stocks:
            # 基础数据
            stock_signal = StockSignalInfo(
                stock_code=stock_info.stock_code,
                stock_name=stock_info.stock_name,
                rank=stock_data.rank,
                total_score=float(stock_data.total_score) if stock_data.total_score else 0.0,
                price_change=float(stock_data.price_change) if stock_data.price_change else None,
                turnover_rate_percent=float(stock_data.turnover_rate_percent) if stock_data.turnover_rate_percent else None,
                volume_days=float(stock_data.volume_days) if stock_data.volume_days else None,
                market_cap_billions=float(stock_data.market_cap_billions) if stock_data.market_cap_billions else None,
            )
            
            # 计算信号（Phase 2）
            if signal_calculator:
                signal_data = signal_calculator.calculate_signals(
                    stock_code=stock_info.stock_code,
                    current_date=query_date,
                    current_data=stock_data,
                    history_days=7,
                    simplify_hot_labels=True  # 🔥 行业板块：简化热点标签，避免信号污染
                )
                # 填充信号数据
                stock_signal.signals = signal_data['signals']
                stock_signal.signal_count = signal_data['signal_count']
                stock_signal.signal_strength = signal_data['signal_strength']
                stock_signal.in_hot_list = signal_data['in_hot_list']
                stock_signal.in_rank_jump = signal_data['in_rank_jump']
                stock_signal.rank_improvement = signal_data['rank_improvement']
                stock_signal.in_steady_rise = signal_data['in_steady_rise']
                stock_signal.rise_days = signal_data['rise_days']
                stock_signal.in_price_surge = signal_data['in_price_surge']
                stock_signal.in_volume_surge = signal_data['in_volume_surge']
                stock_signal.signal_history = signal_data['signal_history']
            
            stocks_list.append(stock_signal)
        
        # 5. 排序
        stocks_list = self._sort_stocks(stocks_list, sort_mode, signal_thresholds)
        
        # 6. 计算统计信息
        statistics = self._calculate_statistics(stocks_list, query_date)
        
        # 7. 构建响应
        response = IndustryStocksResponse(
            industry=industry_name,
            date=query_date.strftime('%Y%m%d'),
            stock_count=len(stocks_list),
            stocks=stocks_list,
            statistics=statistics
        )
        
        # 8. 缓存结果
        self.cache[cache_key] = response
        logger.info(f"✅ 板块成分股查询完成: {industry_name}, {len(stocks_list)}只")
        
        return response
    
    def _sort_stocks(self, stocks: List[StockSignalInfo], sort_mode: str, signal_thresholds: Optional[SignalThresholds] = None) -> List[StockSignalInfo]:
        """
        排序股票列表
        
        Args:
            stocks: 股票列表
            sort_mode: 排序模式
            signal_thresholds: 信号阈值配置（用于判断版本）
            
        Returns:
            排序后的股票列表
        """
        if sort_mode == "rank":
            # 按全市场排名升序（排名小的在前）
            return sorted(stocks, key=lambda x: x.rank)
        elif sort_mode == "score":
            # 按总分降序
            return sorted(stocks, key=lambda x: x.total_score, reverse=True)
        elif sort_mode == "price_change":
            # 按涨跌幅降序
            return sorted(stocks, key=lambda x: x.price_change or -999, reverse=True)
        elif sort_mode == "volume":
            # 按换手率降序
            return sorted(stocks, key=lambda x: x.turnover_rate_percent or -999, reverse=True)
        elif sort_mode == "signal":
            # Phase 2: 按信号排序，根据版本决定优先级
            # v1原版：优先信号数量（多信号共振）
            # v2新版：优先信号强度（质量优先）
            version = signal_thresholds.hot_list_version if signal_thresholds else "v2"
            logger.info(f"🔄 按信号排序，version={version}, 优先级={'数量>强度' if version=='v1' else '强度>数量'}")
            if signal_thresholds and signal_thresholds.hot_list_version == "v1":
                # 原版：数量 > 强度 > 排名
                return sorted(stocks, key=lambda x: (
                    -x.signal_count,     # 第1优先级：信号数量
                    -x.signal_strength,  # 第2优先级：信号强度
                    x.rank               # 第3优先级：原始排名
                ))
            else:
                # 新版（默认）：强度 > 数量 > 排名
                return sorted(stocks, key=lambda x: (
                    -x.signal_strength,  # 第1优先级：信号强度（百分比）
                    -x.signal_count,     # 第2优先级：信号数量
                    x.rank               # 第3优先级：原始排名
                ))
        elif sort_mode == "signal_count":
            # 按信号数量排序（优先级：数量 > 强度 > 排名）
            return sorted(stocks, key=lambda x: (
                -x.signal_count,     # 第1优先级：信号数量
                -x.signal_strength,  # 第2优先级：信号强度
                x.rank               # 第3优先级：原始排名
            ))
        else:
            # 默认按排名
            return sorted(stocks, key=lambda x: x.rank)
    
    def _calculate_statistics(
        self,
        stocks: List[StockSignalInfo],
        query_date: date
    ) -> Dict:
        """
        计算统计信息
        
        Args:
            stocks: 股票列表
            query_date: 查询日期
        
        Returns:
            统计数据字典
        """
        if not stocks:
            return {}
        
        # 基础统计
        total = len(stocks)
        ranks = [s.rank for s in stocks]
        avg_rank = sum(ranks) / total if total > 0 else 0
        
        # 分层统计
        top_100 = sum(1 for s in stocks if s.rank <= 100)
        top_500 = sum(1 for s in stocks if s.rank <= 500)
        top_1000 = sum(1 for s in stocks if s.rank <= 1000)
        
        # 涨跌幅统计
        price_changes = [s.price_change for s in stocks if s.price_change is not None]
        avg_price_change = sum(price_changes) / len(price_changes) if price_changes else 0
        
        # 信号统计（Phase 2）
        hot_list_count = sum(1 for s in stocks if s.in_hot_list)
        rank_jump_count = sum(1 for s in stocks if s.in_rank_jump)
        steady_rise_count = sum(1 for s in stocks if s.in_steady_rise)
        multi_signal_count = sum(1 for s in stocks if s.signal_count >= 2)
        
        # 平均信号强度
        signal_strengths = [s.signal_strength for s in stocks]
        avg_signal_strength = sum(signal_strengths) / len(signal_strengths) if signal_strengths else 0.0
        
        statistics = {
            "avg_rank": round(avg_rank, 1),
            "top_100_count": top_100,
            "top_500_count": top_500,
            "top_1000_count": top_1000,
            "avg_price_change": round(avg_price_change, 2),
            "date": query_date.strftime('%Y%m%d'),
            # Phase 2 信号统计
            "hot_list_count": hot_list_count,
            "rank_jump_count": rank_jump_count,
            "steady_rise_count": steady_rise_count,
            "multi_signal_count": multi_signal_count,
            "avg_signal_strength": round(avg_signal_strength, 3),
        }
        
        return statistics
    
    def get_industry_detail(
        self,
        industry_name: str,
        target_date: Optional[str] = None,
        k_value: float = 0.618
    ) -> Optional[IndustryDetailResponse]:
        """
        获取板块详细分析（包含4维指标 B1/B2/C1/C2）
        
        Args:
            industry_name: 板块名称
            target_date: 目标日期 YYYYMMDD
            k_value: K值（权重衰减参数）
        
        Returns:
            板块详细分析响应
        """
        # 缓存key
        cache_key = f"industry_detail_{industry_name}_{target_date}_{k_value}"
        if cache_key in self.cache:
            logger.info(f"✨ 缓存命中: {cache_key}")
            return self.cache[cache_key]
        
        logger.info(f"🔄 查询板块详细分析: {industry_name}, K={k_value}")
        
        # 1. 获取成分股数据
        stocks_response = self.get_industry_stocks(
            industry_name=industry_name,
            target_date=target_date,
            sort_mode="rank",
            calculate_signals=True
        )
        
        if not stocks_response:
            return None
        
        # 2. 计算4维指标（使用K值加权）
        b1, b2, c1, c2 = self._calculate_four_metrics(
            stocks_response.stocks, k_value
        )
        
        # 3. 构建响应
        response = IndustryDetailResponse(
            industry=industry_name,
            date=stocks_response.date,
            stock_count=stocks_response.stock_count,
            B1=b1,
            B2=b2,
            C1=c1,
            C2=c2,
            avg_rank=stocks_response.statistics['avg_rank'],
            top_100_count=stocks_response.statistics['top_100_count'],
            top_500_count=stocks_response.statistics['top_500_count'],
            top_1000_count=stocks_response.statistics['top_1000_count'],
            hot_list_count=stocks_response.statistics['hot_list_count'],
            rank_jump_count=stocks_response.statistics['rank_jump_count'],
            steady_rise_count=stocks_response.statistics['steady_rise_count'],
            multi_signal_count=stocks_response.statistics['multi_signal_count'],
            avg_signal_strength=stocks_response.statistics['avg_signal_strength']
        )
        
        # 4. 缓存结果
        self.cache[cache_key] = response
        logger.info(f"✅ 板块详细分析完成: {industry_name}")
        
        return response
    
    def _calculate_four_metrics(
        self,
        stocks: List[StockSignalInfo],
        k: float
    ) -> tuple:
        """
        计算4维指标 B1/B2/C1/C2
        
        Args:
            stocks: 股票列表（已按排名排序）
            k: K值参数
        
        Returns:
            (B1, B2, C1, C2)
        """
        if not stocks:
            return 0.0, 0.0, 0.0, 0.0
        
        # 按排名排序
        sorted_stocks = sorted(stocks, key=lambda x: x.rank)
        
        total_weight = 0.0
        weighted_score = 0.0
        weighted_price_change = 0.0
        weighted_volume = 0.0
        
        for i, stock in enumerate(sorted_stocks):
            # K值加权：w = k^i
            weight = k ** i
            total_weight += weight
            
            # B1: 加权总分
            weighted_score += stock.total_score * weight
            
            # B2: 加权涨跌幅
            if stock.price_change is not None:
                weighted_price_change += stock.price_change * weight
            
            # C1/C2: 加权成交量相关指标
            if stock.turnover_rate_percent is not None:
                weighted_volume += stock.turnover_rate_percent * weight
        
        # 归一化
        B1 = round(weighted_score / total_weight, 2) if total_weight > 0 else 0.0
        B2 = round(weighted_price_change / total_weight, 2) if total_weight > 0 else 0.0
        C1 = round(weighted_volume / total_weight, 2) if total_weight > 0 else 0.0
        
        # C2: 简化版，使用volume_days的加权平均
        weighted_volume_days = 0.0
        for i, stock in enumerate(sorted_stocks):
            weight = k ** i
            if stock.volume_days is not None:
                weighted_volume_days += stock.volume_days * weight
        C2 = round(weighted_volume_days / total_weight, 2) if total_weight > 0 else 0.0
        
        return B1, B2, C1, C2
    
    def get_industry_trend(
        self,
        industry_name: str,
        period: int = 7,
        k_value: float = 0.618
    ) -> Optional[IndustryTrendResponse]:
        """
        获取板块历史趋势
        
        Args:
            industry_name: 板块名称
            period: 追踪天数
            k_value: K值参数
        
        Returns:
            板块历史趋势响应
        """
        # 缓存key（趋势数据缓存时间更长：60分钟）
        cache_key = f"industry_trend_{industry_name}_{period}_{k_value}"
        cache = TTLCache(default_ttl_seconds=3600)  # 60分钟
        if cache_key in cache:
            logger.info(f"✨ 缓存命中: {cache_key}")
            return cache[cache_key]
        
        logger.info(f"🔄 查询板块历史趋势: {industry_name}, {period}天")
        
        # 获取最近N天的日期
        dates = memory_cache.get_dates_range(period)
        if not dates:
            return None
        
        dates = dates[:period]  # 取前N天
        
        # 收集每天的指标
        metrics_history = {
            'B1': [],
            'B2': [],
            'C1': [],
            'C2': [],
            'avg_rank': [],
            'top_100_count': [],
            'hot_list_count': [],
            'avg_signal_strength': []
        }
        date_strs = []
        
        for d in dates:
            date_str = d.strftime('%Y%m%d')
            
            # 获取该日期的板块详情
            detail = self.get_industry_detail(
                industry_name=industry_name,
                target_date=date_str,
                k_value=k_value
            )
            
            if detail:
                metrics_history['B1'].append(detail.B1)
                metrics_history['B2'].append(detail.B2)
                metrics_history['C1'].append(detail.C1)
                metrics_history['C2'].append(detail.C2)
                metrics_history['avg_rank'].append(detail.avg_rank)
                metrics_history['top_100_count'].append(detail.top_100_count)
                metrics_history['hot_list_count'].append(detail.hot_list_count)
                metrics_history['avg_signal_strength'].append(detail.avg_signal_strength)
                date_strs.append(date_str)
        
        if not date_strs:
            return None
        
        # 构建响应
        response = IndustryTrendResponse(
            industry=industry_name,
            period=len(date_strs),
            dates=date_strs,
            metrics_history=metrics_history
        )
        
        cache[cache_key] = response
        logger.info(f"✅ 板块历史趋势完成: {industry_name}, {len(date_strs)}天")
        
        return response
    
    def compare_industries(
        self,
        industry_names: List[str],
        target_date: Optional[str] = None,
        k_value: float = 0.618
    ) -> IndustryCompareResponse:
        """
        多板块对比（2-5个）
        
        Args:
            industry_names: 板块名称列表（2-5个）
            target_date: 目标日期 YYYYMMDD
            k_value: K值参数
        
        Returns:
            板块对比响应
        """
        logger.info(f"🔄 对比板块: {industry_names}, K={k_value}")
        
        # 确定日期
        if target_date:
            query_date = datetime.strptime(target_date, '%Y%m%d').date()
        else:
            query_date = memory_cache.get_latest_date()
        
        # 获取每个板块的详细数据
        industries_detail = []
        for industry_name in industry_names:
            detail = self.get_industry_detail(
                industry_name=industry_name,
                target_date=query_date.strftime('%Y%m%d') if query_date else None,
                k_value=k_value
            )
            if detail:
                industries_detail.append(detail)
        
        # 构建响应
        response = IndustryCompareResponse(
            date=query_date.strftime('%Y%m%d') if query_date else "",
            k_value=k_value,
            industries=industries_detail
        )
        
        logger.info(f"✅ 板块对比完成: {len(industries_detail)}个板块")
        
        return response


# 全局实例
industry_detail_service = IndustryDetailService()
