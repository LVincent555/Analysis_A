# -*- coding: utf-8 -*-
"""
Cache-Aside (旁路缓存) 策略

特性:
- 读: 先查缓存 → 未命中 → 回源加载 → 写入缓存
- 写: 先写DB → 删除缓存 (Lazy Load)
- 保证"缓存存在即为热数据"

适用场景:
- 用户基础信息 (昵称、头像)
- 系统全局配置
- 股票基础信息列表

优点: 读多写少场景性能好，数据一致性较好
"""

from typing import Any, Callable, Dict, Optional

from ..policy import CachePolicy
from ..entry import CacheEntry


class CacheAsidePolicy(CachePolicy):
    """
    Cache-Aside 旁路缓存策略
    
    读请求 → 查内存 → 命中? → 返回 ✓
                  ↓ 未命中
             查DB → 写入内存 → 返回 ✓
    
    写请求 → 更新DB → 删除内存缓存
                  ↓
        下次读自动重新加载 (Lazy Load)
    """
    
    def __init__(self, ttl: int = 3600):
        """
        Args:
            ttl: 默认存活时间 (秒)，默认1小时
        """
        super().__init__(ttl)
    
    def get(
        self, 
        key: str, 
        store: Dict[str, CacheEntry], 
        loader: Optional[Callable[[], Any]] = None
    ) -> Any:
        """
        读取缓存 (支持自动回源)
        
        Args:
            key: 缓存键
            store: 底层存储
            loader: 回源加载函数，未命中时自动调用
        
        Returns:
            缓存值或回源值，都未命中返回 None
        """
        # 1. 查缓存
        entry = store.get(key)
        if entry:
            if entry.is_expired():
                # 过期则删除
                del store[key]
            else:
                entry.touch()
                return entry.value
        
        # 2. 未命中，尝试回源
        if loader:
            try:
                value = loader()
                if value is not None:
                    store[key] = CacheEntry(value, self.ttl)
                return value
            except Exception:
                # 回源失败，返回 None
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
        写入缓存 (Cache-Aside 模式)
        
        逻辑:
        1. 如果有 persister，先执行持久化
        2. 删除缓存 (下次读自动重新加载)
        
        注意: Cache-Aside 的写操作会删除缓存，而非更新
        """
        # 1. 先执行持久化
        if persister:
            persister(value)
        
        # 2. 删除缓存 (Lazy Load)
        if key in store:
            del store[key]
    
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
    
    def set_direct(
        self, 
        key: str, 
        value: Any, 
        store: Dict[str, CacheEntry],
        ttl: int = None
    ) -> None:
        """
        直接设置缓存 (不删除，直接更新)
        
        用于手动预热或回源后写入
        """
        actual_ttl = ttl if ttl is not None else self.ttl
        store[key] = CacheEntry(value, actual_ttl)
