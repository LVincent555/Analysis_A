# -*- coding: utf-8 -*-
"""
缓存条目 (Cache Entry) - 使用 __slots__ + Generic 优化内存

内存对比:
- Dict: {"value": x, "expire_at": y, ...} → ~200-400 Bytes
- Slots: CacheEntry(...)                  → ~56-72 Bytes
- 节省 70%+ 内存
"""

import time
from typing import TypeVar, Generic

T = TypeVar('T')


class CacheEntry(Generic[T]):
    """
    缓存条目 - 极致内存优化
    
    特性:
    1. __slots__: 禁用 __dict__，节省 70%+ 内存
    2. Generic[T]: IDE 友好，类型提示
    3. version: 支持配置热加载检测
    
    Attributes:
        value: 缓存的值
        expire_at: 过期时间戳 (0=永不过期)
        last_access: 最后访问时间戳 (LRU淘汰用)
        is_dirty: 脏数据标记 (Write-Behind用)
        version: 数据版本号 (热加载用)
    """
    __slots__ = ('value', 'expire_at', 'last_access', 'is_dirty', 'version')
    
    value: T
    expire_at: float
    last_access: float
    is_dirty: bool
    version: int
    
    def __init__(self, value: T, ttl: int = 0, version: int = 1):
        """
        创建缓存条目
        
        Args:
            value: 缓存的值
            ttl: 存活时间 (秒)，0=永不过期
            version: 数据版本号
        """
        self.value = value
        now = time.time()
        self.expire_at = now + ttl if ttl > 0 else 0
        self.last_access = now
        self.is_dirty = False
        self.version = version
    
    def is_expired(self) -> bool:
        """检查是否过期"""
        return self.expire_at > 0 and time.time() > self.expire_at
    
    def touch(self) -> None:
        """更新访问时间 (LRU)"""
        self.last_access = time.time()
    
    def is_stale(self, current_version: int) -> bool:
        """检查版本是否落后 (用于热加载)"""
        return self.version < current_version
    
    def mark_dirty(self) -> None:
        """标记为脏数据"""
        self.is_dirty = True
    
    def clear_dirty(self) -> None:
        """清除脏标记"""
        self.is_dirty = False
    
    def remaining_ttl(self) -> float:
        """剩余存活时间 (秒)"""
        if self.expire_at == 0:
            return float('inf')
        remaining = self.expire_at - time.time()
        return max(0, remaining)
    
    def __repr__(self) -> str:
        expired = "expired" if self.is_expired() else f"ttl={self.remaining_ttl():.0f}s"
        dirty = " dirty" if self.is_dirty else ""
        return f"<CacheEntry v{self.version} {expired}{dirty}>"
