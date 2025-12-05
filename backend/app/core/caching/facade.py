# -*- coding: utf-8 -*-
"""
通用对外接口层 (Public Interface Facade)

设计目标:
1. 统一入口: 业务层只 import cache
2. 错误隔离: 缓存异常不会导致业务崩溃
3. 键值规范: 统一的 Key 格式，防止冲突
4. 类型提示: IDE 友好，自动补全

使用方式:
    from app.core.caching import cache
    
    # 会话心跳
    cache.set_session_heartbeat(sid, status=1, ip="127.0.0.1")
    
    # 股票排行
    rank = cache.stock_rank("2024-01-15", top_n=100)
"""

import time
import logging
from typing import Any, Callable, Optional, TypeVar, List
from functools import wraps

logger = logging.getLogger(__name__)
T = TypeVar("T")


def safe_cache_call(default_return: Any = None):
    """
    [装饰器] 缓存操作的安全熔断器
    
    如果缓存层抛出异常 (如磁盘满、Key错误)，捕获异常并记录日志，
    返回默认值，确保业务逻辑不崩溃。
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"[CacheError] {func.__name__} failed: {e}")
                return default_return
        return wrapper
    return decorator


class KeyBuilder:
    """
    键生成器 - 规范全局 Key 格式
    
    命名规则:
    - 内存缓存: 直接 ID (session, user 等)
    - 磁盘缓存: 前缀:参数 (api:xxx, report:xxx)
    - 业务数据: 业务域:具体标识 (stock:600000, sector:BK0001)
    """
    
    # ========== 通用键 ==========
    @staticmethod
    def session(sid: int) -> str:
        return str(sid)
    
    @staticmethod
    def user(uid: int) -> str:
        return str(uid)
    
    @staticmethod
    def config(key: str) -> str:
        return key
    
    # ========== API 缓存键 ==========
    @staticmethod
    def api(endpoint: str, params_hash: str) -> str:
        return f"api:{endpoint}:{params_hash}"
    
    @staticmethod
    def report(report_type: str, params_hash: str) -> str:
        return f"report:{report_type}:{params_hash}"
    
    # ========== 股票业务键 ==========
    @staticmethod
    def stock_daily(date: str) -> str:
        """日数据缓存键"""
        return f"daily:{date}"
    
    @staticmethod
    def stock_rank(date: str, top_n: int) -> str:
        """排行榜缓存键"""
        return f"rank:{date}:{top_n}"
    
    @staticmethod
    def sector_list(date: str) -> str:
        """板块列表缓存键"""
        return f"sector:{date}"
    
    @staticmethod
    def hotspot(date: str) -> str:
        """热点分析缓存键"""
        return f"hotspot:{date}"
    
    @staticmethod
    def signal(signal_type: str, date: str) -> str:
        """信号扫描缓存键"""
        return f"signal:{signal_type}:{date}"
    
    @staticmethod
    def industry_jump(date: str, days: int) -> str:
        """行业跳变缓存键"""
        return f"industry_jump:{date}:{days}"


class PublicCache:
    """
    通用对外接口层 (Facade)
    
    业务层应该只调用此类，而不是直接调用 UnifiedCache。
    
    分类:
    1. 通用接口: 会话、用户、配置 (所有项目通用)
    2. 专用接口: 股票、板块、热点 (本项目特定)
    3. 管理接口: 统计、GC、清理
    """
    
    # 延迟导入，避免循环依赖
    _manager = None
    
    @classmethod
    def _get_manager(cls):
        """延迟获取 UnifiedCache"""
        if cls._manager is None:
            from .manager import UnifiedCache
            cls._manager = UnifiedCache
        return cls._manager
    
    # ══════════════════════════════════════════════════════════════
    #                    Part 1: 通用接口 (Generic)
    # ══════════════════════════════════════════════════════════════
    
    # ---------- 1.1 会话管理 (Write-Behind) ----------
    
    @staticmethod
    @safe_cache_call(default_return=None)
    def get_session(sid: int) -> Optional[dict]:
        """获取会话状态"""
        manager = PublicCache._get_manager()
        if not manager.has_region("sessions"):
            return None
        return manager.session().get(KeyBuilder.session(sid))
    
    @staticmethod
    @safe_cache_call(default_return=None)
    def set_session_heartbeat(sid: int, status: int, ip: str) -> None:
        """更新会话心跳 (高频调用)"""
        manager = PublicCache._get_manager()
        if not manager.has_region("sessions"):
            return
        data = {
            "status": status,
            "last_active": time.time(),
            "ip_address": ip
        }
        manager.session().set(KeyBuilder.session(sid), data)
    
    @staticmethod
    def remove_session(sid: int) -> None:
        """移除会话 (登出时)"""
        manager = PublicCache._get_manager()
        if manager.has_region("sessions"):
            manager.session().delete(KeyBuilder.session(sid))
    
    # ---------- 1.2 用户信息 (Cache-Aside) ----------
    
    @staticmethod
    @safe_cache_call(default_return=None)
    def get_user(uid: int, loader: Callable[[], dict] = None) -> Optional[dict]:
        """
        获取用户信息 (带回源加载)
        
        Args:
            uid: 用户ID
            loader: 回源加载函数 (未命中时调用)
        """
        manager = PublicCache._get_manager()
        if not manager.has_region("users"):
            return loader() if loader else None
        return manager.user().get(KeyBuilder.user(uid), loader=loader)
    
    @staticmethod
    def invalidate_user(uid: int) -> None:
        """用户数据失效 (修改资料后调用)"""
        manager = PublicCache._get_manager()
        if manager.has_region("users"):
            manager.user().delete(KeyBuilder.user(uid))
    
    # ---------- 1.3 系统配置 (Cache-Aside) ----------
    
    @staticmethod
    @safe_cache_call(default_return=None)
    def get_config(key: str, loader: Callable = None) -> Any:
        """获取系统配置"""
        manager = PublicCache._get_manager()
        if not manager.has_region("config"):
            return loader() if loader else None
        return manager.config().get(KeyBuilder.config(key), loader=loader)
    
    @staticmethod
    def set_config(key: str, value: Any) -> None:
        """设置系统配置 (直接写入缓存)"""
        manager = PublicCache._get_manager()
        if manager.has_region("config"):
            # 使用 set_direct 直接写入，而非 Cache-Aside 的删除逻辑
            from .policies.cache_aside import CacheAsidePolicy
            store = manager.config()
            if hasattr(store.policy, 'set_direct'):
                store.policy.set_direct(KeyBuilder.config(key), value, store.store)
            else:
                store.set(KeyBuilder.config(key), value)
    
    # ---------- 1.4 API 响应缓存 (FileStore) ----------
    
    @staticmethod
    @safe_cache_call(default_return=None)
    def get_api_cache(endpoint: str, params_hash: str, loader: Callable = None) -> Any:
        """
        通用 API 响应缓存
        
        Args:
            endpoint: API 端点名 (如 "daily_rank")
            params_hash: 参数哈希
            loader: 未命中时的计算函数
        """
        manager = PublicCache._get_manager()
        if not manager.has_region("api_response"):
            return loader() if loader else None
        key = KeyBuilder.api(endpoint, params_hash)
        return manager.api().get(key, loader=loader)
    
    @staticmethod
    @safe_cache_call(default_return=None)
    def set_api_cache(endpoint: str, params_hash: str, value: Any, ttl: int = 300) -> None:
        """设置 API 缓存"""
        manager = PublicCache._get_manager()
        if not manager.has_region("api_response"):
            return
        key = KeyBuilder.api(endpoint, params_hash)
        manager.api().set(key, value, ttl=ttl)
    
    # ══════════════════════════════════════════════════════════════
    #                Part 2: 专用接口 (Domain-Specific)
    #                    针对股票分析系统的业务接口
    # ══════════════════════════════════════════════════════════════
    
    # ---------- 2.1 股票数据查询 (VectorStore) ----------
    
    @staticmethod
    def stock_rank(date: str, top_n: int = 100) -> list:
        """
        获取日排行榜
        
        直接透传到 Numpy 层，不加 safe_cache_call
        (VectorStore 是核心功能，异常需要暴露)
        """
        manager = PublicCache._get_manager()
        return manager.stock().query("get_top_n_by_rank", date, top_n)
    
    @staticmethod
    def stock_by_code(code: str) -> Optional[dict]:
        """获取个股详情"""
        manager = PublicCache._get_manager()
        return manager.stock().query("get_stock_by_code", code)
    
    @staticmethod
    def stock_by_codes(codes: list) -> list:
        """批量获取股票数据"""
        manager = PublicCache._get_manager()
        return manager.stock().query("get_stocks_by_codes", codes)
    
    @staticmethod
    def stock_history(code: str, start_date: str, end_date: str) -> list:
        """获取股票历史数据"""
        manager = PublicCache._get_manager()
        return manager.stock().query("get_history", code, start_date, end_date)
    
    # ---------- 2.2 板块数据 (VectorStore + FileStore) ----------
    
    @staticmethod
    def sector_list(date: str) -> list:
        """获取板块列表"""
        manager = PublicCache._get_manager()
        return manager.stock().query("get_sectors", date)
    
    @staticmethod
    def sector_stocks(sector_code: str, date: str) -> list:
        """获取板块成分股"""
        manager = PublicCache._get_manager()
        return manager.stock().query("get_sector_stocks", sector_code, date)
    
    @staticmethod
    @safe_cache_call(default_return=None)
    def sector_analysis(sector_code: str, date: str, loader: Callable = None) -> dict:
        """板块深度分析 (耗时计算，结果缓存到磁盘)"""
        manager = PublicCache._get_manager()
        if not manager.has_region("api_response"):
            return loader() if loader else None
        key = f"sector_analysis:{sector_code}:{date}"
        return manager.api().get(key, loader=loader)
    
    # ---------- 2.3 热点分析 (FileStore) ----------
    
    @staticmethod
    @safe_cache_call(default_return=None)
    def hotspot_daily(date: str, loader: Callable = None) -> dict:
        """每日热点分析 (耗时计算，缓存24小时)"""
        manager = PublicCache._get_manager()
        if not manager.has_region("api_response"):
            return loader() if loader else None
        key = KeyBuilder.hotspot(date)
        return manager.api().get(key, loader=loader)
    
    @staticmethod
    @safe_cache_call(default_return=None)
    def cache_hotspot(date: str, data: dict) -> None:
        """缓存热点分析结果"""
        manager = PublicCache._get_manager()
        if not manager.has_region("api_response"):
            return
        key = KeyBuilder.hotspot(date)
        manager.api().set(key, data, ttl=86400)  # 24小时
    
    # ---------- 2.4 信号系统 (FileStore) ----------
    
    @staticmethod
    @safe_cache_call(default_return=None)
    def signal_scan(date: str, signal_type: str, loader: Callable = None) -> list:
        """
        信号扫描结果 (耗时计算，缓存到磁盘)
        
        Args:
            date: 日期
            signal_type: 信号类型 (如 "danzhen", "tupo")
            loader: 计算函数
        """
        manager = PublicCache._get_manager()
        if not manager.has_region("api_response"):
            return loader() if loader else None
        key = KeyBuilder.signal(signal_type, date)
        return manager.api().get(key, loader=loader)
    
    # ---------- 2.5 行业跳变 (FileStore) ----------
    
    @staticmethod
    @safe_cache_call(default_return=None)
    def industry_jump(date: str, days: int = 5, loader: Callable = None) -> list:
        """行业跳变分析 (跨日期计算，结果较大)"""
        manager = PublicCache._get_manager()
        if not manager.has_region("api_response"):
            return loader() if loader else None
        key = KeyBuilder.industry_jump(date, days)
        return manager.api().get(key, loader=loader)
    
    # ---------- 2.6 报表生成 (FileStore - 大文件) ----------
    
    @staticmethod
    @safe_cache_call(default_return=None)
    def get_report(report_type: str, params_hash: str) -> Optional[str]:
        """获取已生成的报表"""
        manager = PublicCache._get_manager()
        if not manager.has_region("reports"):
            return None
        key = KeyBuilder.report(report_type, params_hash)
        return manager.report().get(key)
    
    @staticmethod
    @safe_cache_call(default_return=None)
    def cache_report(report_type: str, params_hash: str, content: str, ttl: int = 86400) -> None:
        """
        缓存生成的报表 (HTML/PDF字符串)
        
        Args:
            report_type: 报表类型 (daily_summary, sector_deep, stock_detail)
            params_hash: 参数哈希
            content: 报表内容
            ttl: 过期时间 (默认24小时)
        """
        manager = PublicCache._get_manager()
        if not manager.has_region("reports"):
            return
        key = KeyBuilder.report(report_type, params_hash)
        manager.report().set(key, content, ttl=ttl)
    
    # ══════════════════════════════════════════════════════════════
    #                    Part 3: 管理接口 (Admin)
    # ══════════════════════════════════════════════════════════════
    
    @staticmethod
    def stats() -> dict:
        """获取所有缓存统计"""
        manager = PublicCache._get_manager()
        if not manager.is_initialized():
            return {}
        return manager.stats()
    
    @staticmethod
    def gc() -> dict:
        """触发 GC"""
        manager = PublicCache._get_manager()
        if not manager.is_initialized():
            return {}
        return manager.gc()
    
    @staticmethod
    def clear_api_cache() -> None:
        """清空 API 缓存"""
        manager = PublicCache._get_manager()
        if manager.has_region("api_response"):
            manager.api().clear()
    
    @staticmethod
    def clear_report_cache() -> None:
        """清空报表缓存"""
        manager = PublicCache._get_manager()
        if manager.has_region("reports"):
            manager.report().clear()
    
    @staticmethod
    def reload_stock_data() -> None:
        """重新加载股票数据"""
        manager = PublicCache._get_manager()
        if manager.has_region("stock_market"):
            manager.stock().reload()


# ══════════════════════════════════════════════════════════════
#                     导出全局单例
# ══════════════════════════════════════════════════════════════

cache = PublicCache()
