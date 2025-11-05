from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import pandas as pd
import os
import glob
from collections import defaultdict
from datetime import datetime
import hashlib
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading

# 创建线程池用于并发处理
executor = ThreadPoolExecutor(max_workers=4)

app = FastAPI(title="股票分析API", version="1.0.0")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 数据文件目录
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# 缓存存储（线程安全）
cache_lock = threading.Lock()
analysis_cache = {}
file_hash_cache = {}

class DateRankInfo(BaseModel):
    date: str
    rank: int

class StockAnalysisResult(BaseModel):
    stock_code: str
    stock_name: str
    industry: str
    appearances: int
    latest_rank: int
    date_rank_info: List[DateRankInfo]

class StockDetail(BaseModel):
    stock_code: str
    stock_name: str
    industry: str
    price_change: float  # 涨跌幅
    turnover_rate: float  # 换手率
    volume_days: float  # 放量天数
    avg_volume_ratio_50: float  # 平均量比_50天
    volatility: float  # 波动率
    rank: int  # 当前排名
    date: str  # 日期

class IndustryStats(BaseModel):
    industry: str
    count: int
    percentage: float

class IndustryTrendData(BaseModel):
    date: str
    industry_counts: Dict[str, int]

class IndustryTrendResponse(BaseModel):
    dates: List[str]
    industries: List[str]
    data: List[IndustryTrendData]

class AnalysisResponse(BaseModel):
    period: str
    period_days: int
    analysis_dates: List[str]
    total_stocks: int
    stocks: List[StockAnalysisResult]

class AvailableDatesResponse(BaseModel):
    dates: List[str]
    latest_date: str
    total_files: int

def get_files_hash(files):
    """计算文件列表的哈希值"""
    hash_str = ""
    for date, file_path in files:
        if os.path.exists(file_path):
            mtime = os.path.getmtime(file_path)
            hash_str += f"{file_path}_{mtime}_"
    return hashlib.md5(hash_str.encode()).hexdigest()

def extract_date(filename):
    """从文件名提取日期"""
    basename = os.path.basename(filename)
    date_str = basename[:8]
    return date_str

def get_excel_files(directory):
    """自动获取目录下所有Excel文件并按日期排序"""
    pattern = os.path.join(directory, '*_data_sma_feature_color.xlsx')
    files = glob.glob(pattern)
    
    # 过滤掉Excel临时文件
    files = [f for f in files if not os.path.basename(f).startswith('~$')]
    
    # 按日期排序，最新的在前
    files_with_dates = []
    for file in files:
        date = extract_date(file)
        files_with_dates.append((date, file))
    
    files_with_dates.sort(reverse=True)
    return files_with_dates

def load_stock_data(file_path, filter_stocks=True, include_details=False, max_count=100):
    """加载股票数据并过滤"""
    df = pd.read_excel(file_path)
    
    # 找到关键列
    code_column = None
    name_column = None
    industry_column = None
    for col in df.columns:
        if '代码' in str(col) or 'code' in str(col).lower():
            code_column = col
        if '名称' in str(col) or 'name' in str(col).lower():
            name_column = col
        if '行业' in str(col) or 'industry' in str(col).lower():
            industry_column = col
    
    if code_column is None:
        code_column = df.columns[1]
    if name_column is None:
        name_column = df.columns[2]
    
    # 获取股票数据
    stocks_data = []
    for idx in range(min(max_count, len(df))):
        stock_code = str(df[code_column].iloc[idx]).strip()
        stock_name = str(df[name_column].iloc[idx]).strip() if name_column else stock_code
        stock_industry = str(df[industry_column].iloc[idx]).strip() if industry_column and pd.notna(df[industry_column].iloc[idx]) else "未知"
        
        # 根据filter_stocks参数过滤
        if filter_stocks:
            if (stock_code.startswith('300') or stock_code.startswith('301') or 
                stock_code.startswith('688') or stock_code.startswith('920')):
                continue
        
        stock_item = {
            'code': stock_code,
            'name': stock_name,
            'industry': stock_industry,
            'rank': idx + 1
        }
        
        # 如果需要详细信息，添加更多字段
        if include_details:
            row = df.iloc[idx]
            stock_item['price_change'] = float(row['涨跌幅']) if '涨跌幅' in df.columns and pd.notna(row['涨跌幅']) else 0.0
            stock_item['turnover_rate'] = float(row['换手率%']) if '换手率%' in df.columns and pd.notna(row['换手率%']) else 0.0
            stock_item['volume_days'] = float(row['放量天数']) if '放量天数' in df.columns and pd.notna(row['放量天数']) else 0.0
            stock_item['avg_volume_ratio_50'] = float(row['平均量比_50天']) if '平均量比_50天' in df.columns and pd.notna(row['平均量比_50天']) else 0.0
            stock_item['volatility'] = float(row['波动率']) if '波动率' in df.columns and pd.notna(row['波动率']) else 0.0
        
        stocks_data.append(stock_item)
    
    return stocks_data

def analyze_stocks_period(directory, days, filter_stocks=True):
    """分析特定时间周期的股票重复出现"""
    files_with_dates = get_excel_files(directory)
    
    if len(files_with_dates) == 0:
        raise HTTPException(status_code=404, detail="未找到数据文件")
    
    # 计算文件哈希，用于缓存验证
    files_hash = get_files_hash(files_with_dates)
    cache_key = f"{days}_{filter_stocks}_{files_hash}"
    
    # 检查缓存（线程安全）
    with cache_lock:
        if cache_key in analysis_cache:
            print(f"✓ 使用缓存: {cache_key}")
            return analysis_cache[cache_key]
    
    print(f"⚙ 计算新数据: {cache_key}")
    
    # 加载所有日期的股票数据
    all_stocks_data = {}
    stock_names = {}  # 保存股票代码对应的名称
    stock_industries = {}  # 保存股票代码对应的行业
    for date, file in files_with_dates:
        stocks = load_stock_data(file, filter_stocks)
        all_stocks_data[date] = {stock['code']: stock['rank'] for stock in stocks}
        # 保存股票名称和行业（总是更新为最新的）
        for stock in stocks:
            stock_names[stock['code']] = stock['name']
            stock_industries[stock['code']] = stock['industry']
    
    # 获取最新日期
    latest_date = files_with_dates[0][0]
    
    # 确定要分析的日期范围
    dates_to_check = [date for date, _ in files_with_dates[:days]]
    
    # 统计每个股票出现的次数和详情
    stock_appearances = defaultdict(lambda: {'dates': [], 'ranks': []})
    
    for date in dates_to_check:
        if date in all_stocks_data:
            for stock_code, rank in all_stocks_data[date].items():
                stock_appearances[stock_code]['dates'].append(date)
                stock_appearances[stock_code]['ranks'].append(rank)
    
    # 找出符合条件的股票
    result_list = []
    
    for stock_code, info in stock_appearances.items():
        appearances = len(info['dates'])
        
        # 根据天数要求判断
        if days <= 3:
            # 2天或3天：必须恰好出现该天数
            if appearances == days and latest_date in info['dates']:
                latest_rank = info['ranks'][info['dates'].index(latest_date)]
                date_rank_info = [{'date': date, 'rank': rank}
                                for date, rank in zip(info['dates'], info['ranks'])]
                
                result_list.append({
                    'stock_code': stock_code,
                    'stock_name': stock_names.get(stock_code, stock_code),
                    'industry': stock_industries.get(stock_code, '未知'),
                    'appearances': appearances,
                    'latest_rank': latest_rank,
                    'date_rank_info': date_rank_info
                })
        else:
            # 5天、7天、14天：在最新日期出现，且至少出现2次
            if latest_date in info['dates'] and appearances >= 2:
                latest_rank = info['ranks'][info['dates'].index(latest_date)]
                date_rank_info = [{'date': date, 'rank': rank}
                                for date, rank in zip(info['dates'], info['ranks'])]
                
                result_list.append({
                    'stock_code': stock_code,
                    'stock_name': stock_names.get(stock_code, stock_code),
                    'industry': stock_industries.get(stock_code, '未知'),
                    'appearances': appearances,
                    'latest_rank': latest_rank,
                    'date_rank_info': date_rank_info
                })
    
    # 按最新排名排序
    result_list.sort(key=lambda x: x['latest_rank'])
    
    result = {
        'period': f'{days}天',
        'period_days': days,
        'analysis_dates': dates_to_check,
        'total_stocks': len(result_list),
        'stocks': result_list
    }
    
    # 保存到缓存（线程安全）
    with cache_lock:
        analysis_cache[cache_key] = result
    print(f"✓ 缓存已保存: {cache_key}, 共{len(result_list)}个股票")
    
    return result

def query_stock_history(directory, stock_code):
    """查询单个股票的历史数据"""
    files_with_dates = get_excel_files(directory)
    
    if len(files_with_dates) == 0:
        raise HTTPException(status_code=404, detail="未找到数据文件")
    
    stock_history = []
    
    # 遍历所有日期的文件
    for date, file_path in files_with_dates:
        try:
            df = pd.read_excel(file_path)
            
            # 找到代码列
            code_column = None
            for col in df.columns:
                if '代码' in str(col) or 'code' in str(col).lower():
                    code_column = col
                    break
            
            if code_column is None:
                code_column = df.columns[1]
            
            # 查找该股票
            stock_row = df[df[code_column].astype(str).str.strip() == stock_code]
            
            if not stock_row.empty:
                idx = stock_row.index[0]
                row = stock_row.iloc[0]
                
                # 获取名称和行业
                name_column = None
                industry_column = None
                for col in df.columns:
                    if '名称' in str(col) or 'name' in str(col).lower():
                        name_column = col
                    if '行业' in str(col) or 'industry' in str(col).lower():
                        industry_column = col
                
                stock_name = str(row[name_column]).strip() if name_column and pd.notna(row[name_column]) else stock_code
                stock_industry = str(row[industry_column]).strip() if industry_column and pd.notna(row[industry_column]) else "未知"
                
                # 构建详细数据
                stock_detail = {
                    'stock_code': stock_code,
                    'stock_name': stock_name,
                    'industry': stock_industry,
                    'price_change': float(row['涨跌幅']) if '涨跌幅' in df.columns and pd.notna(row['涨跌幅']) else 0.0,
                    'turnover_rate': float(row['换手率%']) if '换手率%' in df.columns and pd.notna(row['换手率%']) else 0.0,
                    'volume_days': float(row['放量天数']) if '放量天数' in df.columns and pd.notna(row['放量天数']) else 0.0,
                    'avg_volume_ratio_50': float(row['平均量比_50天']) if '平均量比_50天' in df.columns and pd.notna(row['平均量比_50天']) else 0.0,
                    'volatility': float(row['波动率']) if '波动率' in df.columns and pd.notna(row['波动率']) else 0.0,
                    'rank': idx + 1,
                    'date': date
                }
                
                stock_history.append(stock_detail)
        except Exception as e:
            print(f"读取文件 {file_path} 时出错: {e}")
            continue
    
    if not stock_history:
        raise HTTPException(status_code=404, detail=f"未找到股票代码 {stock_code} 的数据")
    
    return stock_history

@app.get("/")
async def root():
    return {"message": "股票分析API", "version": "1.0.0"}

@app.post("/api/cache/clear")
async def clear_cache():
    """清空所有缓存"""
    global analysis_cache, file_hash_cache
    cache_count = len(analysis_cache)
    analysis_cache.clear()
    file_hash_cache.clear()
    return {"message": f"已清空 {cache_count} 个缓存项", "status": "success"}

@app.get("/api/dates", response_model=AvailableDatesResponse)
async def get_available_dates():
    """获取所有可用的数据日期"""
    try:
        files_with_dates = get_excel_files(DATA_DIR)
        dates = [date for date, _ in files_with_dates]
        
        return {
            "dates": dates,
            "latest_date": dates[0] if dates else "",
            "total_files": len(dates)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analyze/{period}", response_model=AnalysisResponse)
async def analyze_period(
    period: int,
    board_type: str = "main"
):
    """
    分析指定时间周期的股票重复出现（异步并发支持）
    
    - period: 时间周期（2, 3, 5, 7, 14）
    - board_type: 板块类型（main=主板, all=包含双创）
    """
    if period not in [2, 3, 5, 7, 14]:
        raise HTTPException(status_code=400, detail="period必须是2, 3, 5, 7, 14之一")
    
    if board_type not in ["main", "all"]:
        raise HTTPException(status_code=400, detail="board_type必须是main或all")
    
    filter_stocks = (board_type == "main")
    
    try:
        # 在线程池中异步执行，避免阻塞其他请求
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor, 
            analyze_stocks_period, 
            DATA_DIR, 
            period, 
            filter_stocks
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analyze/all/{board_type}")
async def analyze_all_periods(board_type: str = "main"):
    """
    获取所有时间周期的分析结果
    
    - board_type: 板块类型（main=主板, all=包含双创）
    """
    if board_type not in ["main", "all"]:
        raise HTTPException(status_code=400, detail="board_type必须是main或all")
    
    filter_stocks = (board_type == "main")
    periods = [2, 3, 5, 7, 14]
    results = {}
    
    try:
        for period in periods:
            result = analyze_stocks_period(DATA_DIR, period, filter_stocks)
            results[f"{period}天"] = result
        
        return {
            "board_type": "主板" if board_type == "main" else "全部（含双创）",
            "periods": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stock/{stock_code}", response_model=List[StockDetail])
async def get_stock_history(stock_code: str):
    """
    查询单个股票的历史数据和排名变化
    
    - stock_code: 股票代码
    """
    try:
        # 在线程池中异步执行
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            query_stock_history,
            DATA_DIR,
            stock_code
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def load_top_n_stocks(file_path, top_n=1000):
    """专门用于读取前N名的所有股票数据（不过滤，用于行业统计）"""
    df = pd.read_excel(file_path)
    
    # 找到关键列
    code_column = None
    name_column = None
    industry_column = None
    for col in df.columns:
        if '代码' in str(col) or 'code' in str(col).lower():
            code_column = col
        if '名称' in str(col) or 'name' in str(col).lower():
            name_column = col
        if '行业' in str(col) or 'industry' in str(col).lower():
            industry_column = col
    
    if code_column is None:
        code_column = df.columns[1]
    if name_column is None:
        name_column = df.columns[2]
    
    # 读取前N名股票
    stocks_data = []
    for idx in range(min(top_n, len(df))):
        stock_code = str(df[code_column].iloc[idx]).strip()
        stock_industry = str(df[industry_column].iloc[idx]).strip() if industry_column and pd.notna(df[industry_column].iloc[idx]) else "未知"
        
        stocks_data.append({
            'code': stock_code,
            'industry': stock_industry,
            'rank': idx + 1
        })
    
    return stocks_data

def get_top1000_industry_stats(directory):
    """获取今日前1000名的行业分布统计"""
    cache_key = "top1000_industry_stats"
    
    # 检查缓存
    with cache_lock:
        if cache_key in analysis_cache:
            print(f"✓ 使用缓存: {cache_key}")
            return analysis_cache[cache_key]
    
    print(f"⚙ 计算前1000名行业统计: {cache_key}")
    files_with_dates = get_excel_files(directory)
    if len(files_with_dates) == 0:
        raise HTTPException(status_code=404, detail="未找到数据文件")
    
    # 获取最新日期的文件
    latest_date, latest_file = files_with_dates[0]
    
    # 使用专门的函数加载前1000名数据（不过滤）
    top_1000 = load_top_n_stocks(latest_file, top_n=1000)
    
    # 统计行业
    industry_count = defaultdict(int)
    for stock in top_1000:
        industry = stock.get('industry', '未知')
        industry_count[industry] += 1
    
    total = len(top_1000)
    stats = [
        {
            'industry': industry,
            'count': count,
            'percentage': round(count / total * 100, 2)
        }
        for industry, count in sorted(industry_count.items(), key=lambda x: x[1], reverse=True)
    ]
    
    result = {
        'date': latest_date,
        'total_stocks': total,
        'stats': stats
    }
    
    # 保存到缓存
    with cache_lock:
        analysis_cache[cache_key] = result
    print(f"✓ 缓存已保存: {cache_key}, {len(stats)}个行业")
    
    return result

def get_industry_trend_analysis(directory):
    """获取所有日期的行业分布趋势"""
    cache_key = "industry_trend_all"
    
    # 检查缓存
    with cache_lock:
        if cache_key in analysis_cache:
            print(f"✓ 使用缓存: {cache_key}")
            return analysis_cache[cache_key]
    
    print(f"⚙ 计算行业趋势数据: {cache_key}")
    files_with_dates = get_excel_files(directory)
    
    if len(files_with_dates) == 0:
        raise HTTPException(status_code=404, detail="未找到数据文件")
    
    trend_data = []
    all_industries = set()
    
    # 遍历所有文件，获取每天的行业分布（前1000名）
    for date, file_path in files_with_dates:
        try:
            # 使用专门的函数加载前1000名数据
            top_1000 = load_top_n_stocks(file_path, top_n=1000)
            
            industry_count = defaultdict(int)
            for stock in top_1000:
                industry = stock.get('industry', '未知')
                industry_count[industry] += 1
                all_industries.add(industry)
            
            trend_data.append({
                'date': date,
                'industry_counts': dict(industry_count)
            })
        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {e}")
            continue
    
    # 按日期排序（从旧到新）
    trend_data.sort(key=lambda x: x['date'])
    
    result = {
        'dates': [item['date'] for item in trend_data],
        'industries': sorted(list(all_industries)),
        'data': trend_data
    }
    
    # 保存到缓存
    with cache_lock:
        analysis_cache[cache_key] = result
    print(f"✓ 缓存已保存: {cache_key}, {len(trend_data)}个日期, {len(all_industries)}个行业")
    
    return result

@app.get("/api/industry/top1000")
async def get_top1000_industry():
    """
    获取今日前1000名的行业分布统计
    """
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            get_top1000_industry_stats,
            DATA_DIR
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/industry/trend")
async def get_industry_trend():
    """
    获取所有日期的行业分布趋势（前1000名）
    """
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            get_industry_trend_analysis,
            DATA_DIR
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """服务启动时预加载缓存（并行优化）"""
    print("🚀 服务启动中...")
    print("⚙️  开始并行预加载缓存...")
    
    # 在后台线程中预加载，避免阻塞启动
    def preload_cache():
        try:
            import concurrent.futures
            from concurrent.futures import ThreadPoolExecutor as PreloadExecutor
            
            # 创建专门用于预加载的线程池
            with PreloadExecutor(max_workers=8) as preload_pool:
                futures = []
                
                # 预加载常用的分析周期（并行）
                periods = [2, 3, 5]
                board_types = ['main', 'all']
                
                for period in periods:
                    for board_type in board_types:
                        filter_stocks = (board_type == 'main')
                        future = preload_pool.submit(
                            analyze_stocks_period,
                            DATA_DIR,
                            period,
                            filter_stocks
                        )
                        futures.append((future, f"{period}天 ({board_type})"))
                
                # 预加载行业数据（并行）
                industry_top1000_future = preload_pool.submit(get_top1000_industry_stats, DATA_DIR)
                futures.append((industry_top1000_future, "今日前1000名行业统计"))
                
                industry_trend_future = preload_pool.submit(get_industry_trend_analysis, DATA_DIR)
                futures.append((industry_trend_future, "行业趋势分析"))
                
                # 等待所有任务完成并显示结果
                for future, name in futures:
                    try:
                        future.result()  # 等待完成
                        print(f"  ✓ 预加载完成: {name}")
                    except Exception as e:
                        print(f"  ✗ 预加载失败: {name} - {e}")
            
            print("✅ 缓存预加载全部完成！")
        except Exception as e:
            print(f"❌ 缓存预加载出错: {e}")
    
    # 在线程池中执行预加载
    loop = asyncio.get_event_loop()
    loop.run_in_executor(executor, preload_cache)

if __name__ == "__main__":
    import uvicorn
    # 生产环境建议设置reload=False以保持缓存
    print("=" * 60)
    print("股票分析系统启动")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
