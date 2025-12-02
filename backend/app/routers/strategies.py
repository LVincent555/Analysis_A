"""
策略路由
Strategies Router

提供各种策略的API接口
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from collections import OrderedDict
import logging
import time

from ..services.strategies.needle_under_20 import NeedleUnder20Strategy, get_washout_detector
from ..services.numpy_cache_middleware import numpy_cache
from ..services.api_cache import api_cache

logger = logging.getLogger(__name__)

# 策略缓存 TTL: 25小时
STRATEGY_CACHE_TTL = 90000

# 洗盘检测器
def _get_detector(long_period: int = 10):
    return get_washout_detector(short_period=3, long_period=long_period)


router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.get("/needle-under-20")
def get_needle_under_20_stocks(  # ✅ 同步，CPU密集型
    date: str = Query(None, description="日期，格式：YYYYMMDD，默认最新"),
    days: int = Query(5, description="分析天数范围，默认5天"),
    min_score: int = Query(0, description="最低评分阈值"),
    pattern: str = Query(None, description="形态筛选：sky_refuel/bottom_volume"),
    bbi_filter: bool = Query(True, description="是否排除BBI破位股票"),
    max_drop_pct: float = Query(None, description="股价最大跌幅阈值(%)，默认不限"),
    long_period: int = Query(10, description="计算周期：10天(数据有限) 或 21天(对齐同花顺)")
):
    """
    获取单针下二十信号股票列表
    
    返回：按评分降序排列的股票列表
    """
    try:
        # 解析日期
        if date:
            target_date = datetime.strptime(date, '%Y%m%d').date()
        else:
            target_date = numpy_cache.get_latest_date()  # 使用numpy_cache
        
        if not target_date:
            return {"data": [], "total_count": 0, "date_range": [], "industry_distribution": {}}
        
        date_str = target_date.strftime('%Y%m%d')
        
        # ========== 检查缓存 (跨进程共享) ==========
        cache_key = f"needle20:{date_str}:{days}:{min_score}:{pattern}:{bbi_filter}:{max_drop_pct}:{long_period}"
        cached = api_cache.get(cache_key)
        if cached:
            logger.info(f"✓ 命中缓存: {cache_key}")
            return cached
        
        start_time = time.time()
        
        # 只检测目标日期当天的信号（白线刚触发，不要已经反弹的）
        signal_dates = [target_date]
        
        # 获取日期范围用于显示
        all_dates = numpy_cache.get_dates_range(days * 2)  # 使用numpy_cache
        display_dates = [d for d in all_dates if d <= target_date][:days]
        
        if not signal_dates:
            return {"data": [], "total_count": 0, "date_range": [], "industry_distribution": {}}
        
        # 初始化
        results = []
        industry_count = {}
        seen_stocks = set()
        
        # 检查数据是否充足
        available_dates = numpy_cache.get_dates_range(50)  # 使用numpy_cache
        data_days = len(available_dates)
        required_days = long_period + 7
        data_sufficient = data_days >= required_days
        
        # ========== 只检测目标日期当天 ==========
        for check_date in signal_dates:
            # 遍历所有股票
            for stock_code in numpy_cache.get_all_stocks().keys():  # 使用numpy_cache
                if stock_code in seen_stocks:
                    continue
                    
                try:
                    # 使用numpy_cache获取数据
                    stock_data = numpy_cache.get_stock_data_for_strategy(stock_code, check_date, lookback_days=30)
                    if not stock_data:
                        continue
                    
                    # ========== 先过滤：用简单条件排除大部分股票 ==========
                    price_changes = stock_data.get('price_changes', [])
                    if price_changes:
                        today_pct = price_changes[-1]
                        # 涨幅>5%的不太可能是下杀
                        if today_pct > 5:
                            continue
                        # 跌幅筛选（如果设置了）
                        if max_drop_pct is not None and today_pct < -max_drop_pct:
                            continue
                    
                    # 数据量不足的跳过（避免无效计算）
                    if len(stock_data['closes']) < required_days:
                        continue
                    
                    # ========== 核心：使用洗盘检测器v2 ==========
                    bbis = stock_data.get('bbis', [])
                    
                    washout = _get_detector(long_period).detect(
                        stock_data['closes'],
                        stock_data['highs'],
                        stock_data['lows'],
                        bbis
                    )
                    
                    # 过滤：必须是有效的洗盘形态
                    if not washout or not washout.is_valid:
                        continue
                    
                    # BBI破位筛选（可选）
                    if bbi_filter and washout.bbi_break:
                        continue
                    
                    # 获取当天真实涨跌幅（从数据库，用于筛选和显示）
                    price_changes = stock_data.get('price_changes', [])
                    today_change_pct = price_changes[-1] if price_changes else washout.price_change_pct
                    
                    # 股价跌幅筛选（用当天真实涨跌幅）
                    if max_drop_pct is not None and today_change_pct < -max_drop_pct:
                        continue
                    
                    # 形态筛选
                    if pattern and washout.pattern.value != pattern:
                        continue
                    
                    # 标记已处理
                    seen_stocks.add(stock_code)
                    
                    # 获取股票信息
                    stock_info = numpy_cache.get_stock_info(stock_code)  # 使用numpy_cache
                    
                    # 构建washout_analysis，覆盖涨跌幅
                    washout_dict = washout.to_dict()
                    washout_dict['股价涨跌'] = f"{today_change_pct:+.2f}%"
                    
                    # 构建结果
                    result_dict = {
                        'stock_code': stock_data['stock_code'],
                        'stock_name': stock_data['stock_name'],
                        'signal_date': stock_data['signal_date'],
                        'is_triggered': True,
                        'pattern': washout.pattern.value,
                        'pattern_name': washout.pattern_name,
                        'total_score': washout.score,
                        'industry': stock_info.industry if stock_info else '未知',
                        'latest_rank': stock_data['ranks'][-1] if stock_data['ranks'] else 0,
                        'washout_analysis': washout_dict
                    }
                    
                    results.append(result_dict)
                    
                    # 统计行业分布
                    industry = result_dict['industry']
                    industry_count[industry] = industry_count.get(industry, 0) + 1
                    
                except Exception as e:
                    logger.debug(f"分析股票 {stock_code} 日期 {check_date} 失败: {e}")
                    continue
        
        # ========== 按评分排序 ==========
        # 1. 评分降序
        # 2. 评分相同时按热点排名升序（排名越小越好）
        results.sort(key=lambda x: (-x['total_score'], x.get('latest_rank', 9999)))
        for i, r in enumerate(results, 1):
            r['rank'] = i
        
        elapsed = time.time() - start_time
        
        response = {
            "data": results,
            "total_count": len(results),
            "date_range": [d.strftime('%Y%m%d') for d in display_dates],
            "industry_distribution": industry_count,
            "long_period": long_period,
            "data_days": data_days,
            "required_days": required_days,
            "data_sufficient": data_sufficient
        }
        
        # ========== 存入缓存 (跨进程共享, TTL=25小时) ==========
        api_cache.set(cache_key, response, ttl=STRATEGY_CACHE_TTL)
        logger.info(f"✓ 计算完成并缓存: {len(results)}条, 耗时{elapsed:.2f}s")
        
        return response
        
    except Exception as e:
        logger.error(f"获取单针下二十列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/needle-under-20/{stock_code}")
def get_stock_needle_detail(  # ✅ 同步
    stock_code: str,
    date: str = Query(None, description="日期，格式：YYYYMMDD")
):
    """
    获取单只股票的单针下二十详情
    
    返回：评分详情、形态、标签等
    """
    try:
        # 解析日期
        if date:
            target_date = datetime.strptime(date, '%Y%m%d').date()
        else:
            target_date = numpy_cache.get_latest_date()  # 使用numpy_cache
        
        if not target_date:
            raise HTTPException(status_code=404, detail="无可用数据")
        
        # 使用numpy_cache获取策略数据（需要完整OHLCV）
        stock_data = numpy_cache.get_stock_data_for_strategy(stock_code, target_date, lookback_days=30)
        
        if not stock_data:
            raise HTTPException(status_code=404, detail="股票数据不存在或数据不足")
        
        # 分析
        strategy = NeedleUnder20Strategy()
        result = strategy.analyze(
            stock_code=stock_data['stock_code'],
            stock_name=stock_data['stock_name'],
            signal_date=stock_data['signal_date'],
            closes=stock_data['closes'],
            highs=stock_data['highs'],
            lows=stock_data['lows'],
            opens=stock_data['opens'],
            volumes=stock_data['volumes'],
            turnovers=stock_data['turnovers'],
            ranks=stock_data['ranks']
        )
        
        # 获取股票信息
        stock_info = numpy_cache.get_stock_info(stock_code)  # 使用numpy_cache
        
        result_dict = result.to_dict()
        result_dict['industry'] = stock_info.industry if stock_info else '未知'
        
        return result_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取股票详情失败 [{stock_code}]: {e}")
        raise HTTPException(status_code=500, detail=str(e))
