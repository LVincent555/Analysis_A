# RES-027: 后端缓存系统治理 Phase 1 容量与 Metrics 落地结果

**日期**: 2026-07-09
**状态**: [SOLVED]
**类型**: Infra / Backend / Cache / Architecture / Testing
**层级**: Backend
**关联**: SUG-006, RES-026, PRB-001, SUG-001, DEC-002, RES-014

---

## 执行摘要

已完成 SUG-006 Phase 1 的低风险落地：为缓存系统增加轻量 metrics，并为 `ObjectStore` 增加可选容量上限与 LRU 淘汰。默认 region 现在会使用 `registry.py` 中登记的 `max_entries` 建议值。

本次不改变对外 API contract，不改变缓存策略语义；`WriteThrough` / `WriteBehind` 的失败语义修正仍留在 Phase 2。

---

## 已完成改动

### 1. 新增 CacheMetrics

新增：

```text
backend/app/core/caching/metrics.py
```

当前记录：

```text
hits
misses
sets
deletes
evictions
expired_cleanups
loader_errors
persister_errors
operation_errors
recoveries
last_error
```

### 2. ObjectStore 增加容量边界

`ObjectStore` 新增参数：

```python
max_entries: int | None = None
eviction_policy: str = "lru"
```

行为：

1. `max_entries=None` 时保持原行为，不限制数量。
2. 超过 `max_entries` 时淘汰最近最少访问的 entry。
3. 新写入的 key 会被保护，避免刚写入即被淘汰。
4. 淘汰通过 policy delete 路径执行，尽量保持 dirty key 等策略状态同步。

### 3. ObjectStore stats 增强

`ObjectStore.stats()` 现在额外返回：

```text
policy
ttl_seconds
max_entries
eviction_policy
metrics
```

这让 Operations 缓存统计可以直接看到 region 的策略、容量和基础运行计数。

### 4. FileStore stats 增强

`FileStore` 新增：

1. `metrics`
2. `size_limit_gb`
3. `close()`

其中 `close()` 用于测试或生命周期需要时显式关闭 diskcache 句柄，避免 Windows 下临时目录清理变慢。

### 5. 默认 region 使用 registry 容量建议

`bootstrap.py` 现在从 `registry.default_region_specs_by_name()` 读取 `max_entries`：

```text
sessions      -> 10000
session_keys  -> 10000
users         -> 10000
config        -> 1000
```

`api_response` 与 `reports` 仍由 `FileStore` 的磁盘 size limit 控制。

### 6. 缓存单测补强

`backend/tests/unit/test_cache_core.py` 新增覆盖：

1. `ObjectStore` hit/miss/set metrics。
2. `ObjectStore` LRU 淘汰。
3. bootstrap 是否应用 registry 中的 `max_entries`。
4. `FileStore` set/hit/delete metrics。
5. 避免 Windows 下 pytest `tmp_path` 夹带慢清理，改为测试内显式临时目录与 `FileStore.close()`。

---

## 验证结果

缓存专项：

```text
uv run pytest -q tests/unit/test_cache_core.py tests/unit/test_operations_cache_use_cases.py tests/unit/test_session_key_store.py
```

结果：

```text
17 passed
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
116 tests collected
```

API contract：

```text
126 routes
```

---

## 是否满足验收

满足 Phase 1 当前验收：

1. `ObjectStore` 已具备可选 `max_entries`。
2. `ObjectStore` 超限会执行 LRU 淘汰。
3. `ObjectStore.stats()` 已展示 policy、ttl、max_entries 与 metrics。
4. `FileStore.stats()` 已展示 size limit 与 metrics。
5. 默认 region 已使用 registry 的容量建议。
6. 后端全量测试通过，API contract 未变化。

---

## 注意事项

1. Cache-Aside 的 `set()` 当前语义仍是“执行写入后删除缓存”，因此 `sets` 指标可能增加但 `total` 不增加，这是现有策略行为，不是本次引入的新问题。
2. `WriteThroughPolicy.set()` 仍是先写缓存再执行 persister；如果 persister 失败，缓存可能短暂污染。该问题已在 SUG-006 Phase 2 中列为待修。
3. `WriteBehindPolicy.get_dirty_keys()` 仍会取出并清空 dirty key；失败重试语义仍待 Phase 2 修正。
4. 当前 metrics 是进程内计数，进程重启后重置。

---

## 后续建议

下一步继续 SUG-006 Phase 2：修正策略失败语义。

优先顺序：

1. `WriteThroughPolicy` 改成 persister 成功后再写缓存。
2. `WriteBehindPolicy` 增加 `peek_dirty_keys / ack_dirty_keys / requeue_dirty_keys`。
3. `DatabaseSyncer` 在 DB commit 成功后 ack dirty key，失败则保留重试。
