"""
行业分析相关API路由
"""
from fastapi import APIRouter, HTTPException
from typing import List
from ..services.industry_service_db import industry_service_db
from ..models import IndustryStat, IndustryStats

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
async def get_industry_trend(period: int = 3, top_n: int = 100):
    """
    获取行业趋势数据（多日期动态变化）
    
    Args:
        period: 分析周期（天数），默认3
        top_n: 每天TOP N股票，默认100
    
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
                .order_by(DailyStockData.date.desc())\
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
async def get_top1000_industry():
    """
    获取前1000名行业统计
    
    Returns:
        行业统计数据（包含日期和stats列表）
    """
    try:
        from ..database import SessionLocal
        from ..db_models import DailyStockData
        from sqlalchemy import desc
        
        # 获取最新日期
        db = SessionLocal()
        try:
            latest_date = db.query(DailyStockData.date)\
                .distinct()\
                .order_by(desc(DailyStockData.date))\
                .first()
            
            if not latest_date:
                raise HTTPException(status_code=404, detail="没有可用数据")
            
            date_str = latest_date[0].strftime('%Y%m%d')
            
            # 获取统计数据
            stats = industry_service.analyze_industry(period=1, top_n=1000)
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
