# -*- coding: utf-8 -*-
"""
Write-Through (同步直写) 策略

特性:
- 写操作同时更新内存和数据库
- 强一致性，数据不会丢失
- 写性能受DB I/O限制

适用场景:
- 用户修改密码
- 管理员修改权限配置
- 账户锁定/启用状态

代价: 写性能较低 (但这类操作频率通常很低)
"""

from typing import Any, Callable, Dict, Optional

from ..policy import CachePolicy
from ..entry import CacheEntry


class WriteThroughPolicy(CachePolicy):
    """
    Write-Through 同步直写策略
    
    写请求 → 更新内存 → 同步写DB → 返回 ✓
    """
    
    def __init__(self, ttl: int = 0):
        """
        Args:
            ttl: 默认存活时间 (秒)，0=永不过期
        """
        super().__init__(ttl)
    
    def get(
        self, 
        key: str, 
        store: Dict[str, CacheEntry], 
        loader: Optional[Callable[[], Any]] = None
    ) -> Any:
        """
        读取缓存
        
        支持回源加载 (类似 Cache-Aside)
        """
        entry = store.get(key)
        if entry:
            if entry.is_expired():
                del store[key]
            else:
                entry.touch()
                return entry.value
        
        # 未命中，尝试回源
        if loader:
            try:
                value = loader()
                if value is not None:
                    store[key] = CacheEntry(value, self.ttl)
                return value
            except Exception:
                return None
        
        return None
    
    def set(
        self, 
        key: str, 
        value: Any, 
        store: Dict[str, CacheEntry], 
        persister: Optional[Callable[[Any], None]] = None
    ) -> None:
        """
        写入缓存 (同步直写)
        
        逻辑:
        1. 更新内存
        2. 同步执行持久化 (如果提供)
        """
        # 1. 更新内存
        store[key] = CacheEntry(value, self.ttl)
        
        # 2. 同步持久化
        if persister:
            persister(value)
    
    def delete(
        self,
        key: str,
        store: Dict[str, CacheEntry]
    ) -> bool:
        """删除缓存"""
        if key in store:
            del store[key]
            return True
        return False
