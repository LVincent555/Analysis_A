# RES-032: 后端缓存系统治理 Phase 4 历史缓存收口落地结果

**日期**: 2026-07-09
**状态**: [SOLVED]
**类型**: Infra / Backend / Cache / Architecture / Testing
**层级**: Backend
**关联**: SUG-006, RES-026, RES-027, RES-028, RES-029, PRB-001, SUG-001, DEC-002, RES-014

---

## 执行摘要

已完成 SUG-006 Phase 4 的低风险落地：将历史高性能缓存 `numpy_cache` 与 `HotSpotsCache` 收口为 UnifiedCache 的 logical region，让 Operations 管理面能在同一套 registry / stats / health / clear 机制下看到它们。

本次没有重写 Numpy 查询算法，没有替换现有 Analysis / MarketData 查询路径，也没有改变 API contract。目标是先把治理视图、启动登记、管理入口和测试基线对齐。

---

## 已完成改动

### 1. registry 登记历史缓存 logical region

修改：

```text
backend/app/core/caching/registry.py
```

新增：

```text
stock_market
hot_spots
```

含义：

1. `stock_market`：包装历史 `numpy_cache` 行情 read model。
2. `hot_spots`：包装历史 `HotSpotsCache` 14 天聚合热点榜缓存。

### 2. 启动时注册 logical region

修改：

```text
backend/app/core/caching/bootstrap.py
```

`init_default_cache_regions()` 现在会注册：

```text
sessions
session_keys
users
config
api_response
reports
stock_market
hot_spots
```

注册顺序与 `registry.default_region_names()` 保持一致。

### 3. VectorStore stats 增强

修改：

```text
backend/app/core/caching/store.py
```

`VectorStore.stats()` 现在优先读取 `numpy_cache.get_memory_stats()`，返回：

```text
initialized
total_mb
stocks_count
sectors_count
daily_records
sector_records
memory_stats
```

这让 `/api/cache/stats` 不再只能看到独立的 `numpy_cache` 摘要，也能在 `cache_regions.stock_market` 中看到同一 read model 的 logical region 状态。

### 4. 新增 HotSpotsStore

修改：

```text
backend/app/core/caching/store.py
backend/app/core/caching/manager.py
backend/app/core/caching/__init__.py
```

新增 `HotSpotsStore`，作为 `HotSpotsCache` 的薄 adapter：

1. `stats()` 透出 cached dates、TTL、max days、memory。
2. `get(date)` 返回指定日期完整热点榜数据。
3. `clear()` 调用 `HotSpotsCache.clear_cache()`。
4. `reload(days)` 清空后调用 `preload_recent_dates(days)`。
5. `delete(date)` 支持删除单个日期缓存。

### 5. Operations all_disposable 避免重复清理

修改：

```text
backend/app/contexts/operations/application/cache_management.py
```

`all_disposable` 现在按 registry 清理可丢弃且可清理的 region。若 `hot_spots` 已登记为 region，则通过 `region:hot_spots` 清理；若未来某环境没有登记，则保留旧的 `clear_hotspots_cache()` fallback。

### 6. 缓存 README 更新

修改：

```text
backend/app/core/caching/README.md
```

说明：

1. `stock_market` 是历史 Numpy 行情 read model 的 logical region。
2. `hot_spots` 是历史热点榜聚合缓存的 logical region。
3. 当前阶段只收口治理视图和管理入口，不重写底层高性能查询实现。

### 7. 单测补强

修改：

```text
backend/tests/unit/test_cache_core.py
backend/tests/unit/test_operations_cache_use_cases.py
```

新增/调整覆盖：

1. 默认启动注册与 registry 包含 `stock_market` / `hot_spots`。
2. `UnifiedCache.stats()` 覆盖 logical region。
3. `HotSpotsStore` 支持 stats/get/delete/clear/reload。
4. Operations stats 能展示 `stock_market` / `hot_spots` 的 region 视图。
5. `all_disposable` 不清理不可 clear 的 `stock_market`，但会清理 `hot_spots`。

---

## 验证结果

缓存核心专项：

```text
uv run pytest -q tests/unit/test_cache_core.py
```

结果：

```text
16 passed
```

Operations 缓存专项：

```text
uv run pytest -q tests/unit/test_operations_cache_use_cases.py
```

结果：

```text
10 passed
```

全量后端测试：

```text
uv run pytest -q --disable-warnings
```

结果：

```text
exited 0
```

测试收集：

```text
uv run pytest --collect-only -q
```

结果：

```text
128 tests collected
```

API contract：

```text
126 routes
```

---

## 是否满足验收

满足 Phase 4 当前验收：

1. Operations stats 能展示 `stock_market` 与 `hot_spots` logical region。
2. 原分析查询路径未重写，性能核心不受影响。
3. 原 API contract 未变化。
4. 历史缓存已经进入 registry、bootstrap、UnifiedCache stats 和管理清理规则。
5. 单测覆盖 logical region 注册和热点缓存 adapter 行为。

---

## 注意事项

1. `stock_market` 是只读 read model，`clearable=False`；需要通过 reload 刷新，不应由普通 region clear 清空。
2. `hot_spots` 已是 clearable logical region；`cache_type=hotspots` 旧入口仍可用，`cache_type=region:hot_spots` 也可用。
3. Analysis / MarketData 仍有部分 legacy adapter 直接注入 `numpy_cache`，本次没有强行改动这些高频查询路径。
4. 若后续要进一步收敛查询侧依赖，应在 Analysis / MarketData 各自 context 内新增更细的 cache port，而不是让 application 层直接依赖 `UnifiedCache`。

---

## 后续建议

SUG-006 的 Phase 0 至 Phase 4 已完成。后续只剩 Phase 5：多进程 / 多实例前置方案。

建议暂不实现 Redis；等出现以下触发条件再签发新 DEC：

1. `uvicorn --workers > 1`。
2. 多后端实例部署。
3. `/api/secure` session key、login nonce 或 secure nonce 需要跨进程共享。
