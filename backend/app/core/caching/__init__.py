# -*- coding: utf-8 -*-
"""
统一缓存系统 (Unified Cache System)

三层架构:
1. 内核层: CacheEntry, CachePolicy, ObjectStore, VectorStore, FileStore
2. 管理层: UnifiedCache (路由网关)
3. 门面层: PublicCache (业务接口)

使用方式:
    from app.core.caching import cache
    
    # 会话心跳
    cache.set_session_heartbeat(sid, status=1, ip="127.0.0.1")
    
    # 股票排行
    rank = cache.stock_rank("2024-01-15", top_n=100)
    
    # 热点分析 (自动缓存)
    hotspot = cache.hotspot_daily("2024-01-15", loader=lambda: analyze())
"""

from .facade import cache, PublicCache, KeyBuilder

__all__ = ["cache", "PublicCache", "KeyBuilder"]
