"""
各种策略大模块
Strategies Collection Module

包含：
- common: 公共组件（可复用）
- needle_under_20: 单针下二十策略
"""

from .needle_under_20 import NeedleUnder20Strategy

__all__ = ['NeedleUnder20Strategy']
