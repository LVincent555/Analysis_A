"""
API路由包

这里保留旧的聚合导出，但采用懒加载，避免导入某个路由子模块时预加载全部
分析依赖。
"""

_EXPORTS = {
    "analysis_router": ".analysis",
    "stock_router": ".stock",
    "industry_router": ".industry",
    "rank_jump_router": ".rank_jump",
    "steady_rise_router": ".steady_rise",
    "sector_router": ".sector",
}

__all__ = list(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from importlib import import_module

    module = import_module(_EXPORTS[name], __name__)
    value = getattr(module, "router")
    globals()[name] = value
    return value
