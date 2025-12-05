# -*- coding: utf-8 -*-
"""
存储引擎 (Storage Engines)

三种存储引擎:
1. ObjectStore: 内存字典 + Slots优化，适合业务对象
2. VectorStore: Numpy 封装，适合结构化数据分析
3. FileStore: DiskCache 封装，适合大文件/API响应
"""

import threading
from typing import Any, Callable, Dict, Optional, Union
from abc import ABC, abstractmethod

from .entry import CacheEntry
from .policy import CachePolicy


class CacheRegion(ABC):
    """
    缓存分区抽象基类
    
    所有存储引擎必须实现这些接口
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """分区名称"""
        pass
    
    @abstractmethod
    def get(self, key: str, loader: Optional[Callable] = None) -> Any:
        """读取缓存"""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, **kwargs) -> None:
        """写入缓存"""
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """删除缓存"""
        pass
    
    @abstractmethod
    def stats(self) -> dict:
        """统计信息"""
        pass


class ObjectStore(CacheRegion):
    """
    对象存储引擎 (L1 内存层)
    
    用于存储常规业务对象 (Session, User, Config)
    支持 TTL、策略切换、线程安全
    
    特性:
    - 底层结构: Dict[str, CacheEntry]
    - 内存效率: ~64 Bytes/条 (Slots优化)
    - 线程安全: RLock 保护
    """
    
    def __init__(self, name: str, policy: CachePolicy):
        """
        Args:
            name: 分区名称
            policy: 缓存策略 (WriteBehind/CacheAside/WriteThrough)
        """
        self._name = name
        self.policy = policy
        self.store: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
    
    @property
    def name(self) -> str:
        return self._name
    
    def get(self, key: str, loader: Callable = None) -> Any:
        """
        读取缓存
        
        Args:
            key: 缓存键
            loader: 回源加载函数 (仅Cache-Aside使用)
        """
        with self._lock:
            return self.policy.get(key, self.store, loader)
    
    def set(self, key: str, value: Any, persister: Callable = None, **kwargs) -> None:
        """
        写入缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            persister: 持久化函数 (仅Write-Through/Cache-Aside使用)
        """
        with self._lock:
            self.policy.set(key, value, self.store, persister)
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        with self._lock:
            return self.policy.delete(key, self.store)
    
    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            self.store.clear()
    
    def clear_expired(self) -> int:
        """
        清理过期条目
        
        Returns:
            清理的条目数量
        """
        with self._lock:
            expired_keys = [k for k, v in self.store.items() if v.is_expired()]
            for k in expired_keys:
                del self.store[k]
            return len(expired_keys)
    
    def keys(self) -> list:
        """获取所有键"""
        with self._lock:
            return list(self.store.keys())
    
    def values(self) -> list:
        """获取所有值"""
        with self._lock:
            return [entry.value for entry in self.store.values() if not entry.is_expired()]
    
    def items(self) -> list:
        """获取所有键值对"""
        with self._lock:
            return [(k, v.value) for k, v in self.store.items() if not v.is_expired()]
    
    def size(self) -> int:
        """当前条目数"""
        with self._lock:
            return len(self.store)
    
    def stats(self) -> dict:
        """统计信息"""
        with self._lock:
            total = len(self.store)
            expired = sum(1 for v in self.store.values() if v.is_expired())
            dirty = sum(1 for v in self.store.values() if v.is_dirty)
            return {
                "name": self._name,
                "type": "object",
                "total": total,
                "expired": expired,
                "dirty": dirty,
                "active": total - expired
            }


class VectorStore(CacheRegion):
    """
    向量存储引擎 (L1 内存层) - 封装 NumpyCacheMiddleware
    
    将旧的 Numpy 缓存降级为统一缓存系统中的"只读高密度分区"
    
    特性:
    - 底层结构: numpy.ndarray
    - 内存效率: ~80 Bytes/条 (无Python对象开销)
    - 只读操作: 通过 query() 方法做复杂查询
    """
    
    def __init__(self, numpy_middleware, name: str = "stock_market"):
        """
        Args:
            numpy_middleware: 原有的 NumpyCacheMiddleware 实例
            name: 分区名称
        """
        self.core = numpy_middleware
        self._name = name
    
    @property
    def name(self) -> str:
        return self._name
    
    def get(self, key: str, loader: Callable = None) -> Any:
        """
        VectorStore 不支持单Key查询
        请使用 query() 方法
        """
        raise NotImplementedError("VectorStore uses query() instead of get()")
    
    def set(self, key: str, value: Any, **kwargs) -> None:
        """VectorStore 是只读的"""
        raise NotImplementedError("VectorStore is read-only")
    
    def delete(self, key: str) -> bool:
        """VectorStore 是只读的"""
        raise NotImplementedError("VectorStore is read-only")
    
    def query(self, method_name: str, *args, **kwargs) -> Any:
        """
        透传调用到底层 NumpyCacheMiddleware
        
        示例:
            vector_store.query("get_top_n_by_rank", date, 100)
            vector_store.query("get_stock_by_code", "600000")
        """
        if hasattr(self.core, method_name):
            return getattr(self.core, method_name)(*args, **kwargs)
        raise AttributeError(f"Method {method_name} not found in NumpyCacheMiddleware")
    
    def reload(self) -> None:
        """重新加载数据 (数据更新时调用)"""
        if hasattr(self.core, 'load_from_db'):
            self.core.load_from_db()
        elif hasattr(self.core, 'reload'):
            self.core.reload()
    
    def stats(self) -> dict:
        """统计信息"""
        memory_mb = "N/A"
        rows = "N/A"
        
        if hasattr(self.core, 'get_memory_usage'):
            memory_mb = self.core.get_memory_usage()
        
        if hasattr(self.core, 'data') and self.core.data is not None:
            rows = len(self.core.data)
        
        return {
            "name": self._name,
            "type": "vector",
            "memory_mb": memory_mb,
            "rows": rows
        }


class FileStore(CacheRegion):
    """
    文件存储引擎 (L2 磁盘层) - 封装 DiskCache
    
    用于:
    - API响应缓存 (JSON序列化结果)
    - 生成的报表/PDF
    - AI生成的分析报告 (大段文本)
    - >10KB 的非结构化数据
    
    特性:
    - 底层结构: diskcache.Cache (SQLite)
    - 内存效率: 零内存占用
    - LRU淘汰: 自动管理磁盘占用
    - 线程安全: 内置原子操作
    """
    
    def __init__(self, name: str, cache_dir: str, size_limit_gb: float = 0.5):
        """
        Args:
            name: 分区名称
            cache_dir: 缓存目录路径
            size_limit_gb: 磁盘占用上限 (GB)
        """
        self._name = name
        self.cache_dir = cache_dir
        self.size_limit_gb = size_limit_gb
        self.core = None  # 延迟初始化
    
    def _ensure_initialized(self):
        """确保 DiskCache 已初始化"""
        if self.core is None:
            try:
                from diskcache import Cache
                import os
                
                # 确保目录存在
                os.makedirs(self.cache_dir, exist_ok=True)
                
                self.core = Cache(
                    directory=self.cache_dir,
                    size_limit=int(self.size_limit_gb * 1024 * 1024 * 1024),
                    eviction_policy='least-recently-used',
                    tag_index=False  # 关闭标签索引节省性能
                )
            except ImportError:
                raise ImportError("diskcache is required for FileStore. Install with: pip install diskcache")
    
    @property
    def name(self) -> str:
        return self._name
    
    def get(self, key: str, loader: Optional[Callable] = None) -> Any:
        """
        读取缓存 (支持 Cache-Aside 模式)
        
        Args:
            key: 缓存键
            loader: 未命中时的加载函数
        """
        self._ensure_initialized()
        
        val = self.core.get(key)
        
        # 未命中，尝试回源
        if val is None and loader:
            try:
                val = loader()
                if val is not None:
                    # 默认缓存 5 分钟
                    self.core.set(key, val, expire=300)
            except Exception:
                pass  # 容错：加载失败返回 None
        
        return val
    
    def set(self, key: str, value: Any, ttl: int = 0, **kwargs) -> None:
        """
        写入缓存
        
        Args:
            key: 缓存键
            value: 缓存值 (可序列化对象)
            ttl: 过期时间 (秒)，0=使用默认24小时
        """
        self._ensure_initialized()
        expire = ttl if ttl > 0 else 86400  # 默认24小时
        self.core.set(key, value, expire=expire)
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        self._ensure_initialized()
        return self.core.delete(key)
    
    def clear(self) -> None:
        """清空整个分区"""
        self._ensure_initialized()
        self.core.clear()
    
    def stats(self) -> dict:
        """统计信息"""
        self._ensure_initialized()
        return {
            "name": self._name,
            "type": "disk",
            "size_mb": round(self.core.volume() / (1024 * 1024), 2),
            "count": len(self.core),
            "directory": self.cache_dir
        }
