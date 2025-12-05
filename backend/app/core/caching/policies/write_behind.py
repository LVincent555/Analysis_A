# -*- coding: utf-8 -*-
"""
Write-Behind (异步回写) 策略

特性:
- 写操作只更新内存，立即返回
- 后台线程批量同步到数据库
- 最高写性能，最终一致性

适用场景:
- 会话心跳、最后活跃时间
- 页面访问统计
- 在线状态更新

风险: 进程崩溃丢失未落库数据 (业务可接受)
"""

import threading
from typing import Any, Callable, Dict, Optional, Set

from ..policy import CachePolicy
from ..entry import CacheEntry


class WriteBehindPolicy(CachePolicy):
    """
    Write-Behind 异步回写策略
    
    写请求 → 更新内存 → 立即返回 ✓
                    ↓
              标记 is_dirty
                    ↓
        后台线程(10秒) → 批量写DB
    """
    
    def __init__(self, ttl: int = 1800, sync_interval: int = 10):
        """
        Args:
            ttl: 默认存活时间 (秒)，默认30分钟
            sync_interval: 同步间隔 (秒)，默认10秒
        """
        super().__init__(ttl)
        self.sync_interval = sync_interval
        self.dirty_keys: Set[str] = set()
        self._lock = threading.Lock()
    
    def get(
        self, 
        key: str, 
        store: Dict[str, CacheEntry], 
        loader: Optional[Callable[[], Any]] = None
    ) -> Any:
        """
        读取缓存
        
        Write-Behind 模式不主动回源，只返回内存中的值
        """
        entry = store.get(key)
        if entry:
            if entry.is_expired():
                # 过期则删除
                del store[key]
                with self._lock:
                    self.dirty_keys.discard(key)
                return None
            entry.touch()
            return entry.value
        return None
    
    def set(
        self, 
        key: str, 
        value: Any, 
        store: Dict[str, CacheEntry], 
        persister: Optional[Callable[[Any], None]] = None
    ) -> None:
        """
        写入缓存
        
        只更新内存，标记脏数据，不执行 persister
        """
        entry = CacheEntry(value, self.ttl)
        entry.mark_dirty()
        store[key] = entry
        
        with self._lock:
            self.dirty_keys.add(key)
    
    def delete(
        self,
        key: str,
        store: Dict[str, CacheEntry]
    ) -> bool:
        """删除缓存"""
        if key in store:
            del store[key]
            with self._lock:
                self.dirty_keys.discard(key)
            return True
        return False
    
    def on_write(self, key: str, entry: CacheEntry) -> None:
        """标记脏数据"""
        entry.mark_dirty()
        with self._lock:
            self.dirty_keys.add(key)
    
    def get_dirty_keys(self) -> Set[str]:
        """
        获取并清空脏数据键集合 (Syncer调用)
        
        Returns:
            脏数据键的副本
        """
        with self._lock:
            keys = self.dirty_keys.copy()
            self.dirty_keys.clear()
            return keys
    
    def has_dirty(self) -> bool:
        """是否有脏数据"""
        with self._lock:
            return len(self.dirty_keys) > 0
