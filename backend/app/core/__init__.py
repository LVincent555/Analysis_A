"""
核心功能包
"""
from .startup import preload_cache
from .data_manager import run_startup_checks, get_data_manager

__all__ = ["preload_cache", "run_startup_checks", "get_data_manager"]
