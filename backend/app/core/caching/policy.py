# -*- coding: utf-8 -*-
"""
缓存策略接口 (Cache Policy Interface)

提供三种缓存模式:
1. Write-Behind: 写内存 → 后台批量写DB (高频写入)
2. Write-Through: 写内存 + 同步写DB (强一致性)
3. Cache-Aside: 读穿透、写删缓存 (读多写少)
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional

from .entry import CacheEntry


class CachePolicy(ABC):
    """
    缓存策略抽象基类
    
    子类实现:
    - WriteBehindPolicy: 异步回写
    - WriteThroughPolicy: 同步直写
    - CacheAsidePolicy: 旁路缓存
    """
    
    def __init__(self, ttl: int = 0):
        """
        Args:
            ttl: 默认存活时间 (秒)，0=永不过期
        """
        self.ttl = ttl
    
    @abstractmethod
    def get(
        self, 
        key: str, 
        store: Dict[str, CacheEntry], 
        loader: Optional[Callable[[], Any]] = None
    ) -> Any:
        """
        读取缓存
        
        Args:
            key: 缓存键
            store: 底层存储字典
            loader: 回源加载函数 (仅Cache-Aside使用)
        
        Returns:
            缓存值，未命中返回 None
        """
        pass
    
    @abstractmethod
    def set(
        self, 
        key: str, 
        value: Any, 
        store: Dict[str, CacheEntry], 
        persister: Optional[Callable[[Any], None]] = None
    ) -> None:
        """
        写入缓存
        
        Args:
            key: 缓存键
            value: 缓存值
            store: 底层存储字典
            persister: 持久化函数 (仅Write-Through使用)
        """
        pass
    
    @abstractmethod
    def delete(
        self,
        key: str,
        store: Dict[str, CacheEntry]
    ) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
            store: 底层存储字典
        
        Returns:
            是否删除成功
        """
        pass
    
    def on_write(self, key: str, entry: CacheEntry) -> None:
        """
        写入后的钩子 (可选实现)
        
        用于 Write-Behind 模式标记脏数据
        """
        pass
