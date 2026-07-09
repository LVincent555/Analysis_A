# RES-028: 后端缓存系统治理 Phase 2 策略失败语义落地结果

**日期**: 2026-07-09
**状态**: [SOLVED]
**类型**: Infra / Backend / Cache / Reliability / Testing
**层级**: Backend
**关联**: SUG-006, RES-026, RES-027, PRB-001, SUG-001, DEC-002, RES-014

---

## 执行摘要

已完成 SUG-006 Phase 2 的低风险落地：修正缓存策略在持久化失败、回源失败、Write-Behind 同步失败时的语义。

本次仍不签发 DEC，不改变对外 API contract，不引入 Redis 或外部基础设施。改动范围限定在 `core/caching` 内核和缓存单测。

---

## 已完成改动

### 1. WriteThrough 改为持久化成功后写缓存

修改：

```text
backend/app/core/caching/policies/write_through.py
```

新语义：

1. 有 `persister` 时先执行持久化。
2. 持久化成功后再写入内存缓存。
3. 持久化失败时抛出异常，不污染缓存。

这修复了原先“缓存先变新、数据库写失败”的隐性一致性风险。

### 2. Cache-Aside 回源失败补日志

修改：

```text
backend/app/core/caching/policies/cache_aside.py
```

新语义：

1. loader 异常仍返回 `None`，保留原有容错行为。
2. 回源失败会写 warning 日志。
3. `ObjectStore` 的 loader wrapper 继续记录 `loader_errors` 和 `last_error`。

### 3. WriteBehind dirty key 改为显式确认

修改：

```text
backend/app/core/caching/policies/write_behind.py
```

新增：

```python
peek_dirty_keys()
ack_dirty_keys(keys)
requeue_dirty_keys(keys)
```

新语义：

1. `peek_dirty_keys()` 只读取 dirty 快照，不清空。
2. `ack_dirty_keys(keys)` 只在持久化成功后确认。
3. `requeue_dirty_keys(keys)` 可用于未来手动重排或批处理失败恢复。
4. `get_dirty_keys()` 保留为兼容旧调用名，但不再隐式清空 dirty。

### 4. DatabaseSyncer 成功后才 ack dirty

修改：

```text
backend/app/core/caching/syncer.py
```

新语义：

1. session 同步先 `peek_dirty_keys()`。
2. DB bulk update 返回成功后才清除 entry 的 dirty 标记并 `ack_dirty_keys()`。
3. DB 不可用或更新失败时保留 dirty key，等待下次重试。
4. 同步期间如果同一个 key 被新写入，只清理同步前捕获的同一个 entry，避免误清新 dirty。

### 5. 缓存失败语义单测补强

修改：

```text
backend/tests/unit/test_cache_core.py
```

新增覆盖：

1. `WriteThroughPolicy` persister 失败不会改写原缓存。
2. `WriteThroughPolicy` persister 成功后才写缓存。
3. `CacheAsidePolicy` loader 失败返回 `None` 且记录 metrics。
4. `WriteBehindPolicy` dirty key 支持 peek / ack / requeue。
5. `DatabaseSyncer` bulk update 失败保留 dirty key。
6. `DatabaseSyncer` bulk update 成功后 ack dirty key。

---

## 验证结果

缓存专项：

```text
uv run pytest -q tests/unit/test_cache_core.py
```

结果：

```text
15 passed
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
121 tests collected
```

API contract：

```text
126 routes
```

---

## 是否满足验收

满足 Phase 2 验收：

1. WriteThrough persister 失败不会写入缓存。
2. WriteThrough persister 成功才更新缓存。
3. Cache-Aside loader 失败有 metrics 和日志，仍保持容错返回。
4. WriteBehind dirty key 不再被同步器提前清空。
5. DatabaseSyncer 只在 DB 同步成功后 ack dirty key。
6. session sync 失败后 dirty key 保留，可等待下一轮重试。
7. 后端全量测试通过，API contract 未变化。

---

## 注意事项

1. `get_dirty_keys()` 的行为已从“读取并清空”调整为“只读取快照”。当前项目内仅同步器与测试使用该方法，已同步修正。
2. `_bulk_update_sessions()` 现在返回 `bool`，`False` 表示同步未确认成功。
3. Write-Behind 仍是进程内最终一致缓存；进程崩溃时未落库 dirty 数据仍可能丢失。该风险属于 Write-Behind 模式本身，未来若要跨进程/强可靠，需要外部队列或数据库 outbox。
4. 本次没有扩展 `/api/cache/stats` 管理面，也没有收口 `numpy_cache` / `HotSpotsCache`，这些仍归 SUG-006 后续阶段。

---

## 后续建议

下一步可继续 SUG-006 Phase 3：增强 Operations 缓存管理 API。

建议优先做：

1. `/api/cache/stats` 合并 registry 信息与 region metrics。
2. 增加 region 级清理能力，但禁止清理 `session_keys` 等安全运行态材料。
3. 增加缓存健康状态，展示 WriteBehind dirty 积压、FileStore recovery、Numpy/HotSpots 状态。
