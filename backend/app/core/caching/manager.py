# -*- coding: utf-8 -*-
"""
统一缓存管理器 (Unified Cache Manager)

职责:
1. 注册并管理所有缓存分区 (内存 + 磁盘)
2. 提供语法糖快速访问常用分区
3. 协调全局 GC 操作

设计原则: 业务层只与 UnifiedCache 交互，无需关心底层存储引擎
"""

import gc
from typing import Dict, Union

from .store import ObjectStore, VectorStore, FileStore, CacheRegion


# 类型别名
CacheRegionType = Union[ObjectStore, VectorStore, FileStore]


class UnifiedCache:
    """
    统一缓存管理器 - 全局路由网关
    
    三层架构:
    - L1 内存层: ObjectStore (sessions, users, config)
    - L1 内存层: VectorStore (stock_market) 
    - L2 磁盘层: FileStore (api_response, reports)
    
    使用方式:
        UnifiedCache.register("sessions", ObjectStore(...))
        UnifiedCache.session().get(key)
    """
    
    _regions: Dict[str, CacheRegionType] = {}
    _initialized: bool = False
    
    @classmethod
    def register(cls, name: str, region: CacheRegionType) -> None:
        """
        注册缓存分区
        
        Args:
            name: 分区名称 (如 "sessions", "users", "stock_market")
            region: 存储引擎实例
        """
        cls._regions[name] = region
        cls._initialized = True
    
    @classmethod
    def unregister(cls, name: str) -> bool:
        """
        注销缓存分区
        
        Args:
            name: 分区名称
        
        Returns:
            是否成功注销
        """
        if name in cls._regions:
            del cls._regions[name]
            return True
        return False
    
    @classmethod
    def get_region(cls, name: str) -> CacheRegionType:
        """
        获取缓存分区
        
        Args:
            name: 分区名称
        
        Returns:
            存储引擎实例
        
        Raises:
            KeyError: 分区不存在
        """
        if name not in cls._regions:
            raise KeyError(f"Cache region '{name}' not registered")
        return cls._regions[name]
    
    @classmethod
    def has_region(cls, name: str) -> bool:
        """检查分区是否存在"""
        return name in cls._regions
    
    @classmethod
    def is_initialized(cls) -> bool:
        """检查是否已初始化"""
        return cls._initialized
    
    # ══════════════════════════════════════════════════════════════
    #                    语法糖：L1 内存层
    # ══════════════════════════════════════════════════════════════
    
    @classmethod
    def session(cls) -> ObjectStore:
        """访问会话分区 (内存)"""
        return cls.get_region("sessions")
    
    @classmethod
    def user(cls) -> ObjectStore:
        """访问用户分区 (内存)"""
        return cls.get_region("users")
    
    @classmethod
    def stock(cls) -> VectorStore:
        """访问股票数据分区 (内存/Numpy)"""
        return cls.get_region("stock_market")
    
    @classmethod
    def config(cls) -> ObjectStore:
        """访问配置分区 (内存)"""
        return cls.get_region("config")
    
    # ══════════════════════════════════════════════════════════════
    #                    语法糖：L2 磁盘层
    # ══════════════════════════════════════════════════════════════
    
    @classmethod
    def api(cls) -> FileStore:
        """访问 API 响应缓存 (磁盘)"""
        return cls.get_region("api_response")
    
    @classmethod
    def report(cls) -> FileStore:
        """访问报表文件缓存 (磁盘)"""
        return cls.get_region("reports")
    
    # ══════════════════════════════════════════════════════════════
    #                    全局操作
    # ══════════════════════════════════════════════════════════════
    
    @classmethod
    def stats(cls) -> dict:
        """
        获取所有分区统计
        
        Returns:
            {分区名: 统计信息}
        """
        return {name: region.stats() for name, region in cls._regions.items()}
    
    @classmethod
    def gc(cls) -> dict:
        """
        主动 GC：清理过期缓存
        
        Returns:
            {分区名: 清理数量}
        """
        result = {}
        for name, region in cls._regions.items():
            if isinstance(region, ObjectStore):
                result[name] = region.clear_expired()
            elif isinstance(region, FileStore):
                result[name] = "auto-eviction"  # DiskCache 自动 LRU
            else:
                result[name] = "skipped"
        
        # 触发 Python GC
        gc.collect()
        return result
    
    @classmethod
    def clear_all(cls) -> dict:
        """
        清空所有缓存 (管理员操作)
        
        注意: 会清空磁盘缓存，VectorStore 需要手动 reload
        """
        result = {}
        for name, region in cls._regions.items():
            if isinstance(region, ObjectStore):
                region.clear()
                result[name] = "cleared"
            elif isinstance(region, FileStore):
                region.clear()
                result[name] = "cleared"
            elif isinstance(region, VectorStore):
                result[name] = "skipped (call reload() manually)"
        return result
    
    @classmethod
    def region_names(cls) -> list:
        """获取所有注册的分区名称"""
        return list(cls._regions.keys())
