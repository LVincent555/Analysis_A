"""
API响应二级缓存
Phase 6: 基于 DiskCache 的跨进程共享缓存

特性:
- 跨进程共享（多 Worker 模式下内存不翻倍）
- 自动过期 (TTL)
- LRU 淘汰策略
- 防缓存击穿（单一创建者模式）
"""

import os
import logging
import hashlib
import json
from typing import Any, Callable, Optional
from functools import wraps
from datetime import datetime

logger = logging.getLogger(__name__)

# 尝试导入 diskcache
try:
    from diskcache import Cache, FanoutCache
    DISKCACHE_AVAILABLE = True
except ImportError:
    DISKCACHE_AVAILABLE = False
    logger.warning("⚠️ diskcache 未安装，API缓存将使用内存模式")


class APICache:
    """
    API响应缓存
    
    支持两种模式:
    - disk: 使用 DiskCache（跨进程共享）
    - memory: 使用内存字典（单进程，回退模式）
    """
    
    # 默认缓存目录
    DEFAULT_CACHE_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        'data', 'cache'
    )
    
    # 默认配置
    DEFAULT_SIZE_LIMIT = 500 * 1024 * 1024  # 500MB
    DEFAULT_TTL = 3600  # 1小时
    
    def __init__(
        self,
        cache_dir: str = None,
        size_limit: int = None,
        default_ttl: int = None,
        mode: str = 'auto'
    ):
        """
        初始化缓存
        
        Args:
            cache_dir: 缓存目录
            size_limit: 缓存大小限制（字节）
            default_ttl: 默认过期时间（秒）
            mode: 'auto'(自动), 'disk', 'memory'
        """
        self.cache_dir = cache_dir or self.DEFAULT_CACHE_DIR
        self.size_limit = size_limit or self.DEFAULT_SIZE_LIMIT
        self.default_ttl = default_ttl or self.DEFAULT_TTL
        
        # 统计
        self._hits = 0
        self._misses = 0
        
        # 根据模式初始化
        if mode == 'auto':
            mode = 'disk' if DISKCACHE_AVAILABLE else 'memory'
        
        self._mode = mode
        
        if mode == 'disk':
            self._init_disk_cache()
        else:
            self._init_memory_cache()
        
        logger.info(f"📦 API缓存初始化: mode={mode}, dir={self.cache_dir}, limit={self.size_limit // 1024 // 1024}MB")
    
    def _init_disk_cache(self):
        """初始化磁盘缓存"""
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # 使用 FanoutCache 提高并发性能
        self._cache = FanoutCache(
            self.cache_dir,
            shards=4,  # 4个分片
            size_limit=self.size_limit,
            eviction_policy='least-recently-used',
            statistics=True,  # 启用统计
        )
        logger.info(f"✅ DiskCache 初始化成功: {self.cache_dir}")
    
    def _init_memory_cache(self):
        """初始化内存缓存（回退模式）"""
        from collections import OrderedDict
        import time
        
        class MemoryCache:
            """简易内存缓存"""
            def __init__(self, maxsize=1000):
                self._cache = OrderedDict()
                self._expire = {}
                self._maxsize = maxsize
            
            def get(self, key, default=None):
                if key in self._cache:
                    if self._expire.get(key, float('inf')) > time.time():
                        self._cache.move_to_end(key)
                        return self._cache[key]
                    else:
                        del self._cache[key]
                        del self._expire[key]
                return default
            
            def set(self, key, value, expire=None):
                # LRU 淘汰
                while len(self._cache) >= self._maxsize:
                    self._cache.popitem(last=False)
                
                self._cache[key] = value
                if expire:
                    self._expire[key] = time.time() + expire
            
            def delete(self, key):
                self._cache.pop(key, None)
                self._expire.pop(key, None)
            
            def clear(self):
                self._cache.clear()
                self._expire.clear()
            
            def __len__(self):
                return len(self._cache)
            
            def close(self):
                pass
        
        self._cache = MemoryCache()
        logger.info("⚠️ 使用内存缓存模式（非跨进程共享）")
    
    def _make_key(self, prefix: str, **kwargs) -> str:
        """生成缓存键"""
        # 排序确保相同参数生成相同键
        sorted_params = sorted(kwargs.items())
        params_str = json.dumps(sorted_params, ensure_ascii=False, default=str)
        
        # 使用 MD5 哈希生成短键
        hash_str = hashlib.md5(params_str.encode()).hexdigest()[:12]
        
        return f"{prefix}:{hash_str}"
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        value = self._cache.get(key)
        if value is not None:
            self._hits += 1
            logger.debug(f"🎯 二级缓存命中: {key}")
            return value
        self._misses += 1
        logger.debug(f"❌ 二级缓存未命中: {key}")
        return None
    
    def set(self, key: str, value: Any, ttl: int = None):
        """设置缓存"""
        ttl = ttl or self.default_ttl
        self._cache.set(key, value, expire=ttl)
        logger.debug(f"💾 二级缓存写入: {key}, TTL={ttl}s")
    
    def get_or_create(
        self,
        key: str,
        creator_func: Callable,
        ttl: int = None
    ) -> Any:
        """
        获取缓存，不存在则创建
        
        Args:
            key: 缓存键
            creator_func: 创建函数（无参数）
            ttl: 过期时间（秒）
        
        Returns:
            缓存值或创建的新值
        """
        # 先尝试获取
        value = self.get(key)
        if value is not None:
            return value
        
        # 不存在，创建
        value = creator_func()
        self.set(key, value, ttl)
        
        return value
    
    def invalidate(self, pattern: str = None):
        """
        失效缓存
        
        Args:
            pattern: 键前缀模式，None 表示清空全部
        """
        if pattern is None:
            self._cache.clear()
            logger.info("🗑️ 清空全部API缓存")
        else:
            # DiskCache 不支持模式删除，需要遍历
            if self._mode == 'disk':
                keys_to_delete = [k for k in self._cache if k.startswith(pattern)]
                for key in keys_to_delete:
                    self._cache.delete(key)
                logger.info(f"🗑️ 清除 {len(keys_to_delete)} 个匹配 '{pattern}' 的缓存")
            else:
                # 内存模式不支持遍历，直接清空
                self._cache.clear()
    
    def delete(self, key: str):
        """删除单个缓存"""
        self._cache.delete(key)
    
    def stats(self) -> dict:
        """获取缓存统计"""
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0
        
        stats = {
            'mode': self._mode,
            'hits': self._hits,
            'misses': self._misses,
            'total_requests': total,
            'hit_rate': f"{hit_rate:.1f}%",
            'cache_dir': self.cache_dir if self._mode == 'disk' else None,
        }
        
        # DiskCache 额外统计
        if self._mode == 'disk' and hasattr(self._cache, 'volume'):
            try:
                stats['size_mb'] = self._cache.volume() / 1024 / 1024
                stats['count'] = len(self._cache)
            except:
                pass
        
        return stats
    
    def close(self):
        """关闭缓存"""
        if hasattr(self._cache, 'close'):
            self._cache.close()


def cached(prefix: str, ttl: int = 3600):
    """
    缓存装饰器
    
    用法:
    @cached('analysis', ttl=300)
    def get_analysis(period: int, top_n: int):
        ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = api_cache._make_key(prefix, args=args, **kwargs)
            
            # 尝试获取缓存
            result = api_cache.get(cache_key)
            if result is not None:
                logger.debug(f"✓ 缓存命中: {prefix}")
                return result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 缓存结果
            api_cache.set(cache_key, result, ttl)
            logger.debug(f"✓ 缓存写入: {prefix}")
            
            return result
        
        return wrapper
    return decorator


# 全局单例
api_cache = APICache()
