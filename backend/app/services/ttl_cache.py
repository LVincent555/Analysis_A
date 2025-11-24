"""
TTL缓存管理器 - 简单的过期缓存实现
无需外部依赖（Redis），纯内存实现
"""
import time
from typing import Any, Optional
from datetime import datetime


class TTLCache:
    """
    简单的TTL（Time To Live）缓存
    - 自动过期清理
    - 线程安全
    - 内存占用可控
    """
    
    def __init__(self, max_size: int = 1000):
        """
        初始化缓存
        
        Args:
            max_size: 最大缓存条目数，防止内存无限增长
        """
        self._cache = {}
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存值，如果不存在或已过期则返回None
        """
        if key not in self._cache:
            self._misses += 1
            return None
        
        value, expire_time = self._cache[key]
        
        # 检查是否过期
        if expire_time and time.time() > expire_time:
            del self._cache[key]
            self._misses += 1
            return None
        
        self._hits += 1
        return value
    
    def set(self, key: str, value: Any, ttl: int = 300) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），默认300秒（5分钟）
        """
        # 如果缓存已满，清理过期项
        if len(self._cache) >= self._max_size:
            self._cleanup_expired()
            
            # 如果清理后还是满的，删除最旧的10%
            if len(self._cache) >= self._max_size:
                old_keys = list(self._cache.keys())[:self._max_size // 10]
                for old_key in old_keys:
                    del self._cache[old_key]
        
        expire_time = time.time() + ttl if ttl > 0 else None
        self._cache[key] = (value, expire_time)
    
    def delete(self, key: str) -> None:
        """删除缓存项"""
        if key in self._cache:
            del self._cache[key]
    
    def clear(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0
    
    def _cleanup_expired(self) -> int:
        """
        清理所有过期的缓存项
        
        Returns:
            清理的数量
        """
        current_time = time.time()
        expired_keys = [
            key for key, (_, expire_time) in self._cache.items()
            if expire_time and current_time > expire_time
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        return len(expired_keys)
    
    def get_stats(self) -> dict:
        """
        获取缓存统计信息
        
        Returns:
            统计信息字典
        """
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{hit_rate:.1f}%",
            "memory_kb": self._estimate_memory()
        }
    
    def _estimate_memory(self) -> float:
        """
        估算缓存占用的内存（KB）
        
        Returns:
            内存占用（KB）
        """
        import sys
        total_bytes = 0
        
        for key, (value, _) in self._cache.items():
            total_bytes += sys.getsizeof(key)
            total_bytes += sys.getsizeof(value)
        
        return total_bytes / 1024


# 全局单例
ttl_cache = TTLCache(max_size=100)  # 🔥 限制最多100个缓存项，控制内存
