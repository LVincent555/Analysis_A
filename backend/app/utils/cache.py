"""
缓存管理 - 支持TTL的线程安全缓存
"""
import threading
from typing import Any, Dict, Optional, Tuple
from functools import wraps
from datetime import datetime, timedelta


class CacheManager:
    """线程安全的缓存管理器（支持TTL）"""
    
    def __init__(self):
        # 存储格式: {key: (value, expiry_time)}
        self._cache: Dict[str, Tuple[Any, Optional[datetime]]] = {}
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存（自动过期检查）"""
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                # 检查是否过期
                if expiry is None or datetime.now() < expiry:
                    return value
                else:
                    # 已过期，删除缓存
                    del self._cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """
        设置缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl_seconds: 过期时间（秒），None表示永不过期
        """
        with self._lock:
            expiry = None
            if ttl_seconds is not None:
                expiry = datetime.now() + timedelta(seconds=ttl_seconds)
            self._cache[key] = (value, expiry)
    
    def clear(self, key: Optional[str] = None, pattern: Optional[str] = None) -> int:
        """
        清除缓存
        
        Args:
            key: 清除指定key
            pattern: 清除包含该字符串的所有key
            
        Returns:
            清除的key数量
        """
        with self._lock:
            if key:
                if key in self._cache:
                    del self._cache[key]
                    return 1
                return 0
            elif pattern:
                # 清除匹配模式的所有key
                keys_to_delete = [k for k in self._cache.keys() if pattern in k]
                for k in keys_to_delete:
                    del self._cache[k]
                return len(keys_to_delete)
            else:
                count = len(self._cache)
                self._cache.clear()
                return count
    
    def has(self, key: str) -> bool:
        """检查缓存是否存在且未过期"""
        return self.get(key) is not None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self._lock:
            total = len(self._cache)
            expired = 0
            for key, (value, expiry) in self._cache.items():
                if expiry and datetime.now() >= expiry:
                    expired += 1
            
            return {
                "total_keys": total,
                "expired_keys": expired,
                "active_keys": total - expired,
                "cache_size_bytes": sum(
                    len(str(k)) + len(str(v)) for k, (v, _) in self._cache.items()
                )
            }
    
    def cleanup_expired(self) -> int:
        """清理所有过期的缓存项"""
        with self._lock:
            keys_to_delete = []
            for key, (value, expiry) in self._cache.items():
                if expiry and datetime.now() >= expiry:
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                del self._cache[key]
            
            return len(keys_to_delete)
    
    def cache_result(self, key: str, ttl_seconds: Optional[int] = None):
        """
        缓存装饰器
        
        Args:
            key: 缓存键
            ttl_seconds: 过期时间（秒）
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 如果缓存存在且未过期，直接返回
                cached = self.get(key)
                if cached is not None:
                    return cached
                
                # 否则执行函数并缓存结果
                result = func(*args, **kwargs)
                self.set(key, result, ttl_seconds)
                return result
            return wrapper
        return decorator


# 全局缓存管理器实例
cache_manager = CacheManager()
