# -*- coding: utf-8 -*-
"""
存储引擎 (Storage Engines)

三种存储引擎:
1. ObjectStore: 内存字典 + Slots优化，适合业务对象
2. VectorStore: Numpy 封装，适合结构化数据分析
3. FileStore: DiskCache 封装，适合大文件/API响应
"""

import logging
import threading
from typing import Any, Callable, Dict, Optional, Union
from abc import ABC, abstractmethod

from .entry import CacheEntry
from .metrics import CacheMetrics
from .policy import CachePolicy


logger = logging.getLogger(__name__)


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
    
    def __init__(
        self,
        name: str,
        policy: CachePolicy,
        max_entries: int | None = None,
        eviction_policy: str = "lru",
    ):
        """
        Args:
            name: 分区名称
            policy: 缓存策略 (WriteBehind/CacheAside/WriteThrough)
            max_entries: 最大条目数，None 表示不限制
            eviction_policy: 淘汰策略，目前支持 lru
        """
        self._name = name
        self.policy = policy
        self.max_entries = max_entries
        self.eviction_policy = eviction_policy
        self.metrics = CacheMetrics()
        self.store: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
    
    @property
    def name(self) -> str:
        return self._name
    
    def get(self, key: str, loader: Optional[Callable[..., Any]] = None) -> Any:
        """
        读取缓存
        
        Args:
            key: 缓存键
            loader: 回源加载函数 (仅Cache-Aside使用)
        """
        def counted_loader() -> Any:
            try:
                return loader() if loader else None
            except Exception as exc:
                self.metrics.record_loader_error(exc)
                raise

        with self._lock:
            entry = self.store.get(key)
            was_hit = bool(entry and not entry.is_expired())
            try:
                value = self.policy.get(key, self.store, counted_loader if loader else None)
            except Exception as exc:
                self.metrics.record_operation_error(exc)
                raise

            if was_hit:
                self.metrics.record_hit()
            else:
                self.metrics.record_miss()
                self._evict_if_needed(protected_key=key)
            return value

    def set(self, key: str, value: Any, persister: Optional[Callable] = None, **kwargs) -> None:
        """
        写入缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            persister: 持久化函数 (仅Write-Through/Cache-Aside使用)
        """
        def counted_persister(persisted_value: Any) -> None:
            if not persister:
                return
            try:
                persister(persisted_value)
            except Exception as exc:
                self.metrics.record_persister_error(exc)
                raise

        with self._lock:
            try:
                self.policy.set(key, value, self.store, counted_persister if persister else None)
            except Exception as exc:
                self.metrics.record_operation_error(exc)
                raise
            self.metrics.record_set()
            self._evict_if_needed(protected_key=key)
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        with self._lock:
            deleted = self.policy.delete(key, self.store)
            if deleted:
                self.metrics.record_delete()
            return deleted
    
    def clear(self) -> None:
        """清空所有缓存"""
        with self._lock:
            cleared_count = len(self.store)
            self.store.clear()
            if cleared_count:
                self.metrics.record_delete(cleared_count)
    
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
            self.metrics.record_expired_cleanup(len(expired_keys))
            return len(expired_keys)

    def _evict_if_needed(self, protected_key: str | None = None) -> None:
        """Evict least-recently-used entries when the region exceeds its limit."""
        if self.max_entries is None or self.max_entries < 0:
            return

        while len(self.store) > self.max_entries:
            candidates = [(key, entry) for key, entry in self.store.items() if key != protected_key]
            if not candidates:
                break

            if self.eviction_policy != "lru":
                raise ValueError(f"Unsupported eviction policy: {self.eviction_policy}")

            evict_key, _ = min(candidates, key=lambda item: item[1].last_access)
            if not self.policy.delete(evict_key, self.store):
                del self.store[evict_key]
            self.metrics.record_eviction()
    
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
                "policy": self.policy.__class__.__name__,
                "ttl_seconds": self.policy.ttl,
                "max_entries": self.max_entries,
                "eviction_policy": self.eviction_policy if self.max_entries is not None else None,
                "total": total,
                "expired": expired,
                "dirty": dirty,
                "active": total - expired,
                "metrics": self.metrics.to_dict(),
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
    
    def get(self, key: str, loader: Optional[Callable[..., Any]] = None) -> Any:
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
        if hasattr(self.core, "get_memory_stats"):
            memory_stats = self.core.get_memory_stats()
            return {
                "name": self._name,
                "type": "vector",
                "policy": "ReadOnly NumpyCache",
                "initialized": memory_stats.get("initialized"),
                "total_mb": memory_stats.get("total_mb"),
                "stocks_count": memory_stats.get("stocks_count"),
                "sectors_count": memory_stats.get("sectors_count"),
                "daily_records": (memory_stats.get("daily_data") or {}).get("n_records"),
                "sector_records": (memory_stats.get("sector_data") or {}).get("n_records"),
                "memory_stats": memory_stats,
            }

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


class HotSpotsStore(CacheRegion):
    """Logical region adapter for the legacy HotSpotsCache class."""

    def __init__(self, hot_spots_cache, name: str = "hot_spots"):
        self.core = hot_spots_cache
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def get(self, key: str, loader: Optional[Callable[..., Any]] = None) -> Any:
        """Return full hot-spots data for a YYYYMMDD date key."""
        return self.core.get_full_data(key)

    def set(self, key: str, value: Any, **kwargs) -> None:
        raise NotImplementedError("HotSpotsStore is managed by HotSpotsCache")

    def delete(self, key: str) -> bool:
        cache = getattr(self.core, "_cache", None)
        if isinstance(cache, dict) and key in cache:
            del cache[key]
            return True
        return False

    def clear(self) -> None:
        self.core.clear_cache()

    def reload(self, days: int = 3) -> None:
        self.core.clear_cache()
        self.core.preload_recent_dates(days=days)

    def stats(self) -> dict:
        hot_spots_stats = self.core.get_cache_stats()
        return {
            "name": self._name,
            "type": "logical_hotspots",
            "policy": "HotSpotsCache TTL",
            "ttl_seconds": getattr(self.core, "_ttl", None),
            "max_entries": getattr(self.core, "_max_days", None),
            "cached_dates": hot_spots_stats.get("cached_dates", []),
            "total_dates": hot_spots_stats.get("total_dates", 0),
            "memory_kb": hot_spots_stats.get("memory_usage_kb", 0),
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
        self.metrics = CacheMetrics()
    
    def _ensure_initialized(self):
        """确保 DiskCache 已初始化"""
        if self.core is None:
            try:
                from diskcache import Cache
                import os
                import shutil
                
                # 确保目录存在
                os.makedirs(self.cache_dir, exist_ok=True)
                
                try:
                    self.core = Cache(
                        directory=self.cache_dir,
                        size_limit=int(self.size_limit_gb * 1024 * 1024 * 1024),
                        eviction_policy='least-recently-used',
                        tag_index=False  # 关闭标签索引节省性能
                    )
                except Exception as exc:
                    if not self._is_corruption_error(exc):
                        raise
                    logger.warning(
                        "Disk cache corrupted during init (%s): %s; rebuilding...",
                        self.cache_dir,
                        exc,
                    )
                    shutil.rmtree(self.cache_dir, ignore_errors=True)
                    os.makedirs(self.cache_dir, exist_ok=True)
                    self.metrics.record_recovery()
                    self.core = Cache(
                        directory=self.cache_dir,
                        size_limit=int(self.size_limit_gb * 1024 * 1024 * 1024),
                        eviction_policy='least-recently-used',
                        tag_index=False
                    )
            except ImportError:
                raise ImportError("diskcache is required for FileStore. Install with: pip install diskcache")

    def _is_corruption_error(self, exc: Exception) -> bool:
        """判断是否为 SQLite 缓存损坏错误。"""
        msg = str(exc).lower()
        markers = [
            "database disk image is malformed",
            "file is not a database",
            "malformed database schema",
        ]
        return any(m in msg for m in markers)

    def _rebuild_cache(self) -> None:
        """重建损坏的磁盘缓存目录。"""
        import os
        import shutil

        if self.core is not None:
            try:
                self.core.close()
            except Exception:
                pass
            finally:
                self.core = None

        shutil.rmtree(self.cache_dir, ignore_errors=True)
        os.makedirs(self.cache_dir, exist_ok=True)
        self._ensure_initialized()

    def _with_recovery(self, fn: Callable[[], Any], op_name: str) -> Any:
        """执行缓存操作，遇到 SQLite 损坏时自动重建并重试一次。"""
        try:
            return fn()
        except Exception as exc:
            if not self._is_corruption_error(exc):
                self.metrics.record_operation_error(exc)
                raise
            logger.warning(
                "Disk cache corrupted on %s (%s): %s; rebuilding...",
                op_name,
                self.cache_dir,
                exc,
            )
            self._rebuild_cache()
            self.metrics.record_recovery()
            return fn()

    def _require_core(self):
        if self.core is None:
            raise RuntimeError("Disk cache not initialized")
        return self.core
    
    @property
    def name(self) -> str:
        return self._name
    
    def get(self, key: str, loader: Optional[Callable[..., Any]] = None) -> Any:
        """
        读取缓存 (支持 Cache-Aside 模式)
        
        Args:
            key: 缓存键
            loader: 未命中时的加载函数
        """
        self._ensure_initialized()
        val = self._with_recovery(lambda: self._require_core().get(key), "get")
        if val is None:
            self.metrics.record_miss()
        else:
            self.metrics.record_hit()
        
        # 未命中，尝试回源
        if val is None and loader:
            try:
                val = loader()
                if val is not None:
                    # 默认缓存 5 分钟
                    self._with_recovery(lambda: self._require_core().set(key, val, expire=300), "set")
                    self.metrics.record_set()
            except Exception as exc:
                self.metrics.record_loader_error(exc)
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
        self._with_recovery(lambda: self._require_core().set(key, value, expire=expire), "set")
        self.metrics.record_set()
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        self._ensure_initialized()
        deleted = self._with_recovery(lambda: self._require_core().delete(key), "delete")
        if deleted:
            self.metrics.record_delete()
        return deleted
    
    def clear(self) -> None:
        """清空整个分区"""
        self._ensure_initialized()
        self._with_recovery(lambda: self._require_core().clear(), "clear")

    def close(self) -> None:
        """Close the underlying disk cache handle."""
        if self.core is not None:
            self.core.close()
            self.core = None
    
    def stats(self) -> dict:
        """统计信息"""
        self._ensure_initialized()
        size_mb = self._with_recovery(
            lambda: round(self._require_core().volume() / (1024 * 1024), 2),
            "stats.volume",
        )
        count_raw = self._with_recovery(lambda: self._require_core().__len__(), "stats.len")
        count = count_raw if isinstance(count_raw, int) else 0
        return {
            "name": self._name,
            "type": "disk",
            "size_mb": size_mb,
            "count": count,
            "directory": self.cache_dir,
            "size_limit_gb": self.size_limit_gb,
            "metrics": self.metrics.to_dict(),
        }
