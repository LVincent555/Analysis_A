"""
核心功能包

保持旧入口兼容，同时避免导入 ``app.core`` 子模块时触发启动预热依赖。
"""

_EXPORTS = {
    "preload_cache": ".startup",
    "run_startup_checks": ".data_manager",
    "get_data_manager": ".data_manager",
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
