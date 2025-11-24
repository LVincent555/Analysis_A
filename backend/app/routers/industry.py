"""
行业分析相关API路由
"""
from fastapi import APIRouter, HTTPException
from typing import List
from ..services.industry_service_db import industry_service_db
from ..models import IndustryStat, IndustryStats, IndustryStatsWeighted

router = APIRouter(prefix="/api", tags=["industry"])

# 使用数据库服务
industry_service = industry_service_db


@router.get("/industry/stats", response_model=List[IndustryStat])
async def get_industry_stats(period: int = 3, top_n: int = 20):
    """
    获取行业统计数据
    
    Args:
        period: 分析周期（天数），默认3
        top_n: 每天TOP N股票，默认20
    
    Returns:
        行业统计列表
    """
    try:
        return industry_service.analyze_industry(period=period, top_n=top_n)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/industry/trend")
async def get_industry_trend(period: int = 14, top_n: int = 100, date: str = None):
    """
    获取行业趋势数据（多日期动态变化）- 使用内存缓存优化
    
    Args:
        period: 分析周期（天数），默认14
        top_n: 每天TOP N股票，默认100
        date: 指定日期 (YYYYMMDD格式)，不传则使用最新日期
    
    Returns:
        行业趋势数据，包含每日的行业分布
    """
    try:
        from datetime import datetime
        from collections import Counter
        from ..services.memory_cache import memory_cache
        
        # 1. 从内存缓存获取日期范围
        if date:
            target_date = datetime.strptime(date, '%Y%m%d').date()
        else:
            target_date = memory_cache.get_latest_date()
        
        if not target_date:
            return {"data": [], "industries": []}
        
        # 获取最近N天日期
        all_dates = memory_cache.get_dates_range(period * 2)
        target_dates = [d for d in all_dates if d <= target_date][:period]
        
        if not target_dates:
            return {"data": [], "industries": []}
        
        # 2. 收集所有需要查询的股票代码
        all_stock_codes = set()
        date_stocks_map = {}
        
        for date_obj in target_dates:
            top_stocks = memory_cache.get_top_n_stocks(date_obj, top_n)
            date_stocks_map[date_obj] = top_stocks
            all_stock_codes.update(stock.stock_code for stock in top_stocks)
        
        # 3. 批量获取股票信息
        stocks_info = memory_cache.get_stocks_batch(list(all_stock_codes))
        
        # 4. 按日期统计行业分布
        date_industry_map = {}
        all_industries = set()
        
        for date_obj, top_stocks in date_stocks_map.items():
            date_str = date_obj.strftime('%Y%m%d')
            date_industry_map[date_str] = Counter()
            
            for stock_data in top_stocks:
                stock_info = stocks_info.get(stock_data.stock_code)
                if stock_info and stock_info.industry:
                    # 处理行业字段
                    industry = stock_info.industry
                    if isinstance(industry, list) and industry:
                        industry = industry[0]
                    elif isinstance(industry, str) and industry.startswith('['):
                        import ast
                        try:
                            industry_list = ast.literal_eval(industry)
                            industry = industry_list[0] if industry_list else '未知'
                        except:
                            industry = industry.strip('[]').strip("'\"")
                    else:
                        industry = industry if industry else '未知'
                    
                    all_industries.add(industry)
                    date_industry_map[date_str][industry] += 1
        
        # 5. 构建返回数据（从旧到新排序）
        data = []
        for date_str in sorted(date_industry_map.keys()):
            data.append({
                "date": date_str,
                "industry_counts": dict(date_industry_map[date_str])
            })
        
        return {
            "data": data,
            "industries": sorted(list(all_industries))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/industry/top1000", response_model=IndustryStats)
async def get_top1000_industry(limit: int = 1000, date: str = None):
    """
    获取前N名行业统计
    
    Args:
        limit: 前N名数量，默认1000，可选1000/2000/3000/5000
        date: 指定日期 (YYYYMMDD格式)，不传则使用最新日期
    
    Returns:
        行业统计数据（包含日期和stats列表）
    """
    try:
        from datetime import datetime
        from ..services.memory_cache import memory_cache
        
        # 参数验证
        if limit not in [1000, 2000, 3000, 5000]:
            limit = 1000  # 默认值
        
        # 从内存缓存获取日期（避免数据库查询）
        if date:
            target_date = datetime.strptime(date, '%Y%m%d').date()
        else:
            target_date = memory_cache.get_latest_date()
        
        if not target_date:
            raise HTTPException(status_code=404, detail="没有可用数据")
        
        date_str = target_date.strftime('%Y%m%d')
        
        # 获取统计数据（使用limit参数，传递日期）
        stats = industry_service.analyze_industry(
            period=1, 
            top_n=limit,
            target_date=target_date
        )
        total_stocks = sum(s.count for s in stats)
        
        return IndustryStats(
            date=date_str,
            total_stocks=total_stocks,
            stats=stats
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/industry/weighted", response_model=IndustryStatsWeighted)
async def get_industry_weighted(
    date: str = None,
    k: float = 0.618,
    metric: str = 'B1'
):
    """
    获取行业热度统计（加权版本）
    
    始终使用全部数据，通过k值和指标调节视角
    
    Args:
        date: 指定日期 (YYYYMMDD格式)，不传则使用最新日期
        k: 幂律系数，默认0.618，建议范围[0.382, 1.618]
        metric: 排序指标，可选：'B1'(总热度), 'B2'(平均热度), 'C1'(总分), 'C2'(平均分)
    
    Returns:
        行业加权统计数据，包含4个维度的完整计算结果
    """
    try:
        from ..database import SessionLocal
        from ..db_models import DailyStockData, Stock
        from sqlalchemy import desc
        from datetime import datetime
        from collections import defaultdict
        from ..models.industry import IndustryStatWeighted
        
        # 参数验证
        if k < 0.3 or k > 2.0:
            raise HTTPException(status_code=400, detail="k值必须在0.3-2.0之间")
        
        if metric not in ['B1', 'B2', 'C1', 'C2']:
            raise HTTPException(status_code=400, detail="metric必须是B1/B2/C1/C2之一")
        
        # 1. 从内存缓存获取日期
        from ..services.memory_cache import memory_cache
        
        if date:
            target_date = datetime.strptime(date, '%Y%m%d').date()
        else:
            target_date = memory_cache.get_latest_date()
        
        if not target_date:
            raise HTTPException(status_code=404, detail="没有可用数据")
        
        date_str = target_date.strftime('%Y%m%d')
        
        # 2. 从内存缓存获取该日期的所有股票数据
        all_stocks = memory_cache.get_daily_data_by_date(target_date)
        
        if not all_stocks:
            raise HTTPException(status_code=404, detail="该日期没有数据")
        
        # 3. 批量获取股票信息
        stock_codes = [s.stock_code for s in all_stocks]
        stocks_info = memory_cache.get_stocks_batch(stock_codes)
        
        # 4. 构建结果（rank, score, industry）
        results = []
        for stock_data in all_stocks:
            stock_info = stocks_info.get(stock_data.stock_code)
            if stock_info and stock_info.industry:
                results.append((
                    stock_data.rank,
                    stock_data.total_score,
                    stock_info.industry
                ))
        
        if not results:
            raise HTTPException(status_code=404, detail="该日期没有数据")
        
        # 5. 一次遍历，计算所有4个指标
        industry_data = defaultdict(lambda: {
            'count': 0,
            'total_heat_rank': 0.0,
            'total_score': 0.0
        })
        
        total_stocks = len(results)
        
        for rank, score, industry in results:
            # 处理行业字段（可能是数组或字符串）
            if isinstance(industry, list) and industry:
                industry = industry[0]
            elif isinstance(industry, str) and industry.startswith('['):
                import ast
                try:
                    industry_list = ast.literal_eval(industry)
                    industry = industry_list[0] if industry_list else '未知'
                except:
                    industry = industry.strip('[]').strip("'\"")
            elif not industry:
                industry = '未知'
            
            # B方案：基于排名的加权
            weight_b = 1.0 / (rank ** k)
            
            # C方案：基于总分的加权
            weight_c = float(score) if score else 0.0
            
            # 累加
            industry_data[industry]['count'] += 1
            industry_data[industry]['total_heat_rank'] += weight_b
            industry_data[industry]['total_score'] += weight_c
        
        # 6. 计算平均值并构建结果
        stats = []
        for industry, data in industry_data.items():
            count = data['count']
            percentage = round(count / total_stocks * 100, 2)
            
            stats.append(IndustryStatWeighted(
                industry=industry,
                count=count,
                percentage=percentage,
                total_heat_rank=data['total_heat_rank'],
                avg_heat_rank=data['total_heat_rank'] / count,
                total_score=data['total_score'],
                avg_score=data['total_score'] / count
            ))
        
        # 7. 根据指定的metric排序
        if metric == 'B1':
            stats.sort(key=lambda x: x.total_heat_rank, reverse=True)
        elif metric == 'B2':
            stats.sort(key=lambda x: x.avg_heat_rank, reverse=True)
        elif metric == 'C1':
            stats.sort(key=lambda x: x.total_score, reverse=True)
        elif metric == 'C2':
            stats.sort(key=lambda x: x.avg_score, reverse=True)
        
        return IndustryStatsWeighted(
            date=date_str,
            total_stocks=total_stocks,
            k_value=k,
            metric_type=metric,
            stats=stats
        )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
