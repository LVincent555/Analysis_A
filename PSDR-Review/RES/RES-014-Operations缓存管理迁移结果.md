# RES-014: Operations 缓存管理迁移结果

**日期**: 2026-07-08
**状态**: [SOLVED]
**类型**: Infra / Backend / Architecture / Migration / Testing
**层级**: Backend
**关联**: DEC-002, SUG-003, RES-011, RES-012, RES-013

---

## 结果摘要

已将旧 `backend/app/routers/cache_mgmt.py` 的缓存管理实现迁入 `contexts.operations`，旧文件退为兼容入口。对外 API 路径保持 `/api/cache/*` 不变，API contract 路由数量保持 126。

---

## 已完成改动

1. 新增 `contexts.operations.application.cache_management`：
   - `GetCacheStatsUseCase`
   - `ClearCacheUseCase`
   - `ReloadAllCacheUseCase`
   - `GetCacheHealthUseCase`
   - `TriggerCacheGarbageCollectionUseCase`
2. `contexts.operations.application.ports` 新增 `CacheManagementPort`。
3. `contexts.operations.application.commands` 新增 `ClearCacheCommand`。
4. 新增 `contexts.operations.infrastructure.cache_management.PlatformCacheManagementAdapter`：
   - 适配 `numpy_cache`
   - 适配 `HotSpotsCache`
   - 适配 `unified_cache`
   - 适配 `preload_cache`
5. 新增 `contexts.operations.api.cache_router`，承载 `/api/cache/*` HTTP 适配。
6. 旧 `backend/app/routers/cache_mgmt.py` 改为兼容入口：

```python
from ..contexts.operations.api.cache_router import router
```

---

## API 兼容性

保留以下路径：

```text
GET  /api/cache/stats
POST /api/cache/clear
POST /api/cache/reload
GET  /api/cache/health
POST /api/cache/gc
```

API contract：

```text
126 routes
```

`/api/cache/*` endpoint 已切换到：

```text
app.contexts.operations.api.cache_router.*
```

---

## 测试与验证

后端单元测试：

```text
cd backend
uv run pytest
```

结果：

```text
75 passed, 208 warnings
```

新增测试：

1. 缓存统计结果结构归一化。
2. `cache_type=all` 会清理 hotspots/api/report。
3. 未知 `cache_type` 保持旧行为：返回 success 且 cleared 为空。
4. reload、health、gc 通过 `CacheManagementPort` 调用。

---

## 遗留项

1. `core/audit.py` 审计同步回调仍待迁移和字段映射核对。
2. `PolicyEngine` 仍待从旧 `app.services` 收敛为明确 port/adapter。
3. `admin.py` 中数据导入/删除属于跨上下文 command，仍需后续结合 MarketData / Analysis 迁移处理。

---

## 后续建议

DEC-002 Level 2 下一步处理 `core/audit.py`，随后收敛 `PolicyEngine`。
