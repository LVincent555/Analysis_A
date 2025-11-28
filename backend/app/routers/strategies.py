"""
策略路由
Strategies Router

提供各种策略的API接口
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime
import logging

from ..services.strategies.needle_under_20 import NeedleUnder20Strategy, get_washout_detector
from ..services.memory_cache import memory_cache

logger = logging.getLogger(__name__)

# 洗盘检测器单例
_washout_detector = get_washout_detector(short_period=3, long_period=10)


router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.get("/needle-under-20")
async def get_needle_under_20_stocks(
    date: str = Query(None, description="日期，格式：YYYYMMDD，默认最新"),
    days: int = Query(2, description="分析天数范围"),
    min_score: int = Query(0, description="最低评分阈值"),
    position_threshold: int = Query(20, description="短期位置阈值，默认20"),
    pattern: str = Query(None, description="形态筛选：sky_refuel/double_bottom/low_washout"),
    bbi_filter: bool = Query(True, description="是否排除BBI破位股票"),
    max_drop_pct: float = Query(None, description="股价最大跌幅阈值(%)，如5/6/8/10，超过则排除")
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
            target_date = memory_cache.get_latest_date()
        
        if not target_date:
            return {"data": [], "total_count": 0, "date_range": [], "industry_distribution": {}}
        
        # 获取信号日期范围（用于显示）
        all_dates = memory_cache.get_dates_range(days * 2)
        signal_dates = [d for d in all_dates if d <= target_date][:days]
        
        if not signal_dates:
            return {"data": [], "total_count": 0, "date_range": [], "industry_distribution": {}}
        
        # 初始化策略（传递动态阈值）
        from ..services.strategies.needle_under_20.config import NEEDLE_UNDER_20_CONFIG
        custom_config = NEEDLE_UNDER_20_CONFIG.copy()
        custom_config['NEEDLE_THRESHOLD'] = position_threshold
        strategy = NeedleUnder20Strategy(config=custom_config)
        results = []
        industry_count = {}
        
        # 遍历所有股票
        for stock_code in memory_cache.get_all_stocks().keys():
            try:
                # 使用memory_cache的新方法获取数据
                stock_data = memory_cache.get_stock_data_for_strategy(stock_code, target_date, lookback_days=30)
                if not stock_data:
                    continue
                
                # ========== 核心：使用洗盘检测器v2 ==========
                bbis = stock_data.get('bbis', [])
                
                washout = _washout_detector.detect(
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
                
                # 股价跌幅筛选（可选）
                if max_drop_pct is not None and washout.price_change_pct < -max_drop_pct:
                    continue
                
                # 形态筛选
                if pattern and washout.pattern.value != pattern:
                    continue
                
                # 获取股票信息
                stock_info = memory_cache.get_stock_info(stock_code)
                
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
                    'washout_analysis': washout.to_dict()
                }
                
                results.append(result_dict)
                
                # 统计行业分布
                industry = result_dict['industry']
                industry_count[industry] = industry_count.get(industry, 0) + 1
                
            except Exception as e:
                logger.debug(f"分析股票 {stock_code} 失败: {e}")
                continue
        
        # ========== 按评分排序 ==========
        # 1. 空中加油(70分) > 双底共振(55分) > 低位洗盘(40分)
        # 2. 同形态按白线下杀幅度排序
        results.sort(key=lambda x: (x['total_score'], x.get('washout_analysis', {}).get('白线下杀', 0)), reverse=True)
        for i, r in enumerate(results, 1):
            r['rank'] = i
        
        return {
            "data": results,
            "total_count": len(results),
            "date_range": [d.strftime('%Y%m%d') for d in signal_dates],
            "industry_distribution": industry_count
        }
        
    except Exception as e:
        logger.error(f"获取单针下二十列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/needle-under-20/{stock_code}")
async def get_stock_needle_detail(
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
            target_date = memory_cache.get_latest_date()
        
        if not target_date:
            raise HTTPException(status_code=404, detail="无可用数据")
        
        # 使用memory_cache的新方法获取数据
        stock_data = memory_cache.get_stock_data_for_strategy(stock_code, target_date, lookback_days=30)
        
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
        stock_info = memory_cache.get_stock_info(stock_code)
        
        result_dict = result.to_dict()
        result_dict['industry'] = stock_info.industry if stock_info else '未知'
        
        return result_dict
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取股票详情失败 [{stock_code}]: {e}")
        raise HTTPException(status_code=500, detail=str(e))
