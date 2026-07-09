"""
业务逻辑服务包 - 数据库版

保持旧的 ``from app.services import Xxx`` 兼容，同时避免导入任意
``app.services.*`` 子模块时预加载分析栈依赖。
"""

_EXPORTS = {
    "DBDataLoader": ".db_data_loader",
    "AnalysisServiceDB": ".analysis_service_db",
    "StockServiceDB": ".stock_service_db",
    "IndustryServiceDB": ".industry_service_db",
    "RankJumpServiceDB": ".rank_jump_service_db",
    "SteadyRiseServiceDB": ".steady_rise_service_db",
}

__all__ = list(_EXPORTS)


def __getattr__(name):
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    from importlib import import_module

    module = import_module(_EXPORTS[name], __name__)
    value = getattr(module, name)
    globals()[name] = value
    return value
