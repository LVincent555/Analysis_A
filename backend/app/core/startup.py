"""
应用启动时的初始化操作
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from ..services.analysis_service_db import AnalysisServiceDB
from ..services.industry_service_db import IndustryServiceDB

logger = logging.getLogger(__name__)


def preload_cache():
    """并行预加载所有缓存数据"""
    logger.info("开始预加载缓存...")
    
    # 使用数据库版本的服务
    analysis_service = AnalysisServiceDB()
    industry_service = IndustryServiceDB()
    
    # 使用线程池并行加载
    with ThreadPoolExecutor(max_workers=4) as executor:
        # 提交所有预加载任务
        futures = []
        
        # 加载可用日期
        futures.append(executor.submit(analysis_service.get_available_dates))
        
        # 加载各周期分析结果
        for period in [2, 3, 5, 7, 14]:
            futures.append(executor.submit(analysis_service.analyze_period, period, 100, 'main'))
            futures.append(executor.submit(analysis_service.analyze_period, period, 100, 'all'))
            futures.append(executor.submit(analysis_service.analyze_period, period, 100, 'bjs'))
        
        # 加载行业数据（使用analyze_industry方法）
        futures.append(executor.submit(industry_service.analyze_industry, 1, 1000))
        futures.append(executor.submit(industry_service.analyze_industry, 3, 20))
        futures.append(executor.submit(industry_service.analyze_industry, 14, 100))
        
        # 等待所有任务完成
        for future in futures:
            try:
                future.result()
            except Exception as e:
                logger.error(f"预加载任务失败: {e}")
    
    logger.info("缓存预加载完成！")
