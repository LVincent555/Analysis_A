"""
日志配置模块

配置说明：
- 控制台: INFO 级别，简洁输出
- 文件: DEBUG 级别，详细日志

日志文件位置: backend/logs/
"""
import os
import logging
import logging.handlers
from datetime import datetime

# 日志目录
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')


def setup_logging(
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    log_to_file: bool = True
):
    """
    配置应用日志系统
    
    Args:
        console_level: 控制台日志级别
        file_level: 文件日志级别
        log_to_file: 是否写入文件
    """
    # 确保日志目录存在
    if log_to_file and not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
    
    # 获取根 logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # 设置最低级别
    
    # 清除已有的 handlers（避免重复添加）
    root_logger.handlers.clear()
    
    # === 控制台 Handler（简洁输出）===
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_format = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)
    
    # === 文件 Handler（详细日志）===
    if log_to_file:
        # 主日志文件（按日期轮转）
        main_log_file = os.path.join(LOG_DIR, 'app.log')
        file_handler = logging.handlers.TimedRotatingFileHandler(
            main_log_file,
            when='midnight',
            interval=1,
            backupCount=7,  # 保留7天
            encoding='utf-8'
        )
        file_handler.setLevel(file_level)
        file_format = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        root_logger.addHandler(file_handler)
        
        # 热点榜专用日志文件
        hotspots_logger = logging.getLogger('app.services.hot_spots_cache')
        hotspots_handler = logging.handlers.RotatingFileHandler(
            os.path.join(LOG_DIR, 'hotspots.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=3,
            encoding='utf-8'
        )
        hotspots_handler.setLevel(logging.DEBUG)
        hotspots_handler.setFormatter(file_format)
        hotspots_logger.addHandler(hotspots_handler)
        
        # v0.5.0: 统一缓存系统专用日志文件 (移除旧的api_cache日志)
        unified_cache_logger = logging.getLogger('app.core.caching')
        unified_cache_handler = logging.handlers.RotatingFileHandler(
            os.path.join(LOG_DIR, 'unified_cache.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=3,
            encoding='utf-8'
        )
        unified_cache_handler.setLevel(logging.DEBUG)
        unified_cache_handler.setFormatter(file_format)
        unified_cache_logger.addHandler(unified_cache_handler)
        unified_cache_logger.propagate = False
        
        # v0.5.0: 审计日志专用文件
        audit_logger = logging.getLogger('app.core.audit')
        audit_handler = logging.handlers.RotatingFileHandler(
            os.path.join(LOG_DIR, 'audit.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,  # 审计日志保留更多
            encoding='utf-8'
        )
        audit_handler.setLevel(logging.INFO)
        audit_handler.setFormatter(file_format)
        audit_logger.addHandler(audit_handler)
        audit_logger.propagate = False
    
    # 降低第三方库日志级别
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"📝 日志系统已初始化")
    if log_to_file:
        logger.info(f"   📁 日志目录: {LOG_DIR}")
        logger.info(f"   📄 主日志: app.log (DEBUG)")
        logger.info(f"   📄 热点榜日志: hotspots.log (DEBUG)")
        logger.info(f"   📄 统一缓存日志: unified_cache.log (DEBUG)")
        logger.info(f"   📄 审计日志: audit.log (INFO)")
    logger.info(f"   🖥️ 控制台级别: {logging.getLevelName(console_level)}")
