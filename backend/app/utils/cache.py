"""
缓存管理
"""
import threading
from typing import Any, Dict, Optional
from functools import wraps


class CacheManager:
    """线程安全的缓存管理器"""
    
    def __init__(self):
        self._cache: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        with self._lock:
            return self._cache.get(key)
    
    def set(self, key: str, value: Any) -> None:
        """设置缓存"""
        with self._lock:
            self._cache[key] = value
    
    def clear(self, key: Optional[str] = None) -> None:
        """清除缓存"""
        with self._lock:
            if key:
                self._cache.pop(key, None)
            else:
                self._cache.clear()
    
    def has(self, key: str) -> bool:
        """检查缓存是否存在"""
        with self._lock:
            return key in self._cache
    
    def cache_result(self, key: str):
        """缓存装饰器"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 如果缓存存在，直接返回
                cached = self.get(key)
                if cached is not None:
                    return cached
                
                # 否则执行函数并缓存结果
                result = func(*args, **kwargs)
                self.set(key, result)
                return result
            return wrapper
        return decorator


# 全局缓存管理器实例
cache_manager = CacheManager()
