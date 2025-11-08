"""
简单的TTL缓存类 - 供服务层使用
"""
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, Tuple
import threading


class TTLCache:
    """
    简单的TTL缓存
    默认30分钟过期
    """
    
    def __init__(self, default_ttl_seconds: int = 1800):
        """
        初始化TTL缓存
        
        Args:
            default_ttl_seconds: 默认过期时间（秒），默认1800秒=30分钟
        """
        self._cache: Dict[str, Tuple[Any, datetime]] = {}
        self._default_ttl = default_ttl_seconds
        self._lock = threading.Lock()
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值（自动检查过期）"""
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if datetime.now() < expiry:
                    return value
                else:
                    # 过期，删除
                    del self._cache[key]
            return None
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """
        设置缓存值
        
        Args:
            key: 键
            value: 值
            ttl_seconds: 过期时间（秒），不传则使用默认值
        """
        with self._lock:
            ttl = ttl_seconds if ttl_seconds is not None else self._default_ttl
            expiry = datetime.now() + timedelta(seconds=ttl)
            self._cache[key] = (value, expiry)
    
    def __contains__(self, key: str) -> bool:
        """支持 'key in cache' 语法"""
        return self.get(key) is not None
    
    def __getitem__(self, key: str) -> Any:
        """支持 cache[key] 语法"""
        value = self.get(key)
        if value is None:
            raise KeyError(key)
        return value
    
    def __setitem__(self, key: str, value: Any) -> None:
        """支持 cache[key] = value 语法"""
        self.set(key, value)
    
    def clear(self, pattern: Optional[str] = None) -> int:
        """
        清除缓存
        
        Args:
            pattern: 如果提供，只清除包含该字符串的key
            
        Returns:
            清除的key数量
        """
        with self._lock:
            if pattern:
                keys_to_delete = [k for k in self._cache.keys() if pattern in k]
                for k in keys_to_delete:
                    del self._cache[k]
                return len(keys_to_delete)
            else:
                count = len(self._cache)
                self._cache.clear()
                return count
    
    def cleanup_expired(self) -> int:
        """清理过期项"""
        with self._lock:
            now = datetime.now()
            keys_to_delete = [k for k, (v, exp) in self._cache.items() if now >= exp]
            for k in keys_to_delete:
                del self._cache[k]
            return len(keys_to_delete)
    
    def stats(self) -> Dict[str, int]:
        """获取缓存统计"""
        with self._lock:
            now = datetime.now()
            expired = sum(1 for _, exp in self._cache.values() if now >= exp)
            return {
                "total": len(self._cache),
                "expired": expired,
                "active": len(self._cache) - expired
            }
