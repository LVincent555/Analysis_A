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
    获取行业趋势数据（多日期动态变化）
    
    Args:
        period: 分析周期（天数），默认14
        top_n: 每天TOP N股票，默认100
        date: 指定日期 (YYYYMMDD格式)，不传则使用最新日期
    
    Returns:
        行业趋势数据，包含每日的行业分布
    """
    try:
        from ..database import SessionLocal
        from ..db_models import DailyStockData, Stock
        from sqlalchemy import desc
        from collections import Counter
        
        db = SessionLocal()
        try:
            # 1. 获取最近N天的日期
            from datetime import datetime
            
            # 如果指定date，从该日期往前推period天
            if date:
                target_date = datetime.strptime(date, '%Y%m%d').date()
                dates = db.query(DailyStockData.date)\
                    .distinct()\
                    .filter(DailyStockData.date <= target_date)\
                    .order_by(desc(DailyStockData.date))\
                    .limit(period)\
                    .all()
            else:
                dates = db.query(DailyStockData.date)\
                    .distinct()\
                    .order_by(desc(DailyStockData.date))\
                    .limit(period)\
                    .all()
            
            if not dates:
                return {"data": [], "industries": []}
            
            target_dates = [d[0] for d in dates]
            
            # 2. 查询这些日期的TOP N股票
            results = db.query(DailyStockData, Stock)\
                .join(Stock, DailyStockData.stock_code == Stock.stock_code)\
                .filter(DailyStockData.date.in_(target_dates))\
                .filter(DailyStockData.rank <= top_n)\
                .order_by(DailyStockData.date)\
                .all()
            
            # 3. 按日期统计行业分布
            date_industry_map = {}
            all_industries = set()
            
            for daily_data, stock in results:
                date_str = daily_data.date.strftime('%Y%m%d')
                
                # 处理行业字段
                industry = stock.industry
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
                
                all_industries.add(industry)
                
                if date_str not in date_industry_map:
                    date_industry_map[date_str] = Counter()
                
                date_industry_map[date_str][industry] += 1
            
            # 4. 构建返回数据（从旧到新排序）
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
        finally:
            db.close()
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
        from ..database import SessionLocal
        from ..db_models import DailyStockData
        from sqlalchemy import desc
        
        # 参数验证
        if limit not in [1000, 2000, 3000, 5000]:
            limit = 1000  # 默认值
        
        # 获取日期
        db = SessionLocal()
        try:
            from datetime import datetime
            
            if date:
                target_date = datetime.strptime(date, '%Y%m%d').date()
                latest_date = db.query(DailyStockData.date)\
                    .distinct()\
                    .filter(DailyStockData.date == target_date)\
                    .first()
            else:
                latest_date = db.query(DailyStockData.date)\
                    .distinct()\
                    .order_by(desc(DailyStockData.date))\
                    .first()
            
            if not latest_date:
                raise HTTPException(status_code=404, detail="没有可用数据")
            
            date_str = latest_date[0].strftime('%Y%m%d')
            
            # 获取统计数据（使用limit参数，传递日期）
            stats = industry_service.analyze_industry(
                period=1, 
                top_n=limit,
                target_date=latest_date[0]
            )
            total_stocks = sum(s.count for s in stats)
            
            return IndustryStats(
                date=date_str,
                total_stocks=total_stocks,
                stats=stats
            )
        finally:
            db.close()
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
        
        db = SessionLocal()
        try:
            # 1. 获取目标日期
            if date:
                target_date = datetime.strptime(date, '%Y%m%d').date()
                latest_date = db.query(DailyStockData.date)\
                    .distinct()\
                    .filter(DailyStockData.date == target_date)\
                    .first()
            else:
                latest_date = db.query(DailyStockData.date)\
                    .distinct()\
                    .order_by(desc(DailyStockData.date))\
                    .first()
            
            if not latest_date:
                raise HTTPException(status_code=404, detail="没有可用数据")
            
            date_str = latest_date[0].strftime('%Y%m%d')
            
            # 2. 查询该日期的所有股票数据（不限制数量）
            results = db.query(
                DailyStockData.rank,
                DailyStockData.total_score,
                Stock.industry
            ).join(Stock, DailyStockData.stock_code == Stock.stock_code)\
             .filter(DailyStockData.date == latest_date[0])\
             .order_by(DailyStockData.rank)\
             .all()
            
            if not results:
                raise HTTPException(status_code=404, detail="该日期没有数据")
            
            # 3. 一次遍历，计算所有4个指标
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
            
            # 4. 计算平均值并构建结果
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
            
            # 5. 根据指定的metric排序
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
            
        finally:
            db.close()
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
