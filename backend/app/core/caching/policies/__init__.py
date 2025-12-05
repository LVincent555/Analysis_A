# -*- coding: utf-8 -*-
"""
缓存策略实现
"""

from .write_behind import WriteBehindPolicy
from .cache_aside import CacheAsidePolicy
from .write_through import WriteThroughPolicy

__all__ = ["WriteBehindPolicy", "CacheAsidePolicy", "WriteThroughPolicy"]
