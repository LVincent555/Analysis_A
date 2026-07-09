# RES-026: 后端缓存系统治理 Phase 0 落地结果

**日期**: 2026-07-09
**状态**: [SOLVED]
**类型**: Infra / Backend / Cache / Architecture / Testing
**层级**: Backend
**关联**: SUG-006, PRB-001, SUG-001, DEC-002, RES-014

---

## 执行摘要

已按 SUG-006 的 Phase 0 完成后端缓存系统轻量治理落地。本次不签发 DEC，不改变缓存运行策略和对外 API 行为，只做注册清单、启动装配、文档说明和测试基线回收。

本次目标是先让缓存系统“看得懂、测得到、启动装配不散落”，为后续 ObjectStore 容量、metrics、策略失败语义和历史缓存收口做准备。

---

## 已完成改动

### 1. 新增缓存 region 登记

新增：

```text
backend/app/core/caching/registry.py
```

登记当前默认 region：

```text
sessions
session_keys
users
config
api_response
reports
```

每个 region 记录：

1. owner
2. store_type
3. policy
4. ttl_seconds
5. max_entries 建议值
6. consistency
7. disposable / clearable
8. description

### 2. 抽出缓存启动注册

新增：

```text
backend/app/core/caching/bootstrap.py
```

将原先 `main.py::init_cache_system()` 中散落的 region 注册逻辑抽到：

```python
init_default_cache_regions(base_dir)
```

`main.py` 现在只负责调用 bootstrap 并记录启动日志，不再直接维护每个 region 的 store/policy 细节。

### 3. 补充缓存 README

新增：

```text
backend/app/core/caching/README.md
```

记录当前缓存定位：

1. 项目级本机缓存平台。
2. 不是分布式缓存。
3. `session_keys` 是运行态安全材料，不是普通可随意清理的性能缓存。
4. `numpy_cache` 与 `HotSpotsCache` 暂作为历史高性能缓存保留，由 Operations adapter 统一观测。

### 4. 缓存内核测试进入默认 unit 基线

新增：

```text
backend/tests/unit/test_cache_core.py
```

覆盖：

1. `CacheEntry` TTL / dirty / version / slots。
2. `WriteBehindPolicy` dirty key 行为。
3. `CacheAsidePolicy` loader 与失效。
4. `ObjectStore` 基础读写、stats、过期。
5. 默认缓存 bootstrap 与 registry 一致。
6. `PublicCache` 当前 `config=WriteThroughPolicy` 行为。
7. 用户 Cache-Aside 行为。
8. `FileStore` 基础读写删除与 stats。
9. `KeyBuilder` 与 `safe_cache_call`。

删除旧测试：

```text
backend/tests/test_caching.py
```

该旧测试不在默认 `uv run pytest` 基线里，且其中 `config` 仍按旧 `CacheAsidePolicy` 注册，已经与当前真实启动事实不一致。本次将其核心覆盖迁入 `tests/unit` 并修正为 `WriteThroughPolicy`。

---

## 验证结果

缓存专项：

```text
uv run pytest -q tests/unit/test_cache_core.py tests/unit/test_operations_cache_use_cases.py tests/unit/test_session_key_store.py
```

结果：

```text
16 passed
```

默认 region 初始化：

```text
['sessions', 'session_keys', 'users', 'config', 'api_response', 'reports']
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
uv run pytest --collect-only
```

结果：

```text
115 tests collected
```

API contract：

```text
126 routes
```

---

## 是否满足验收

满足 Phase 0 验收：

1. 缓存内核测试已经进入默认 `tests/unit` 基线。
2. 旧的漂移测试已删除，当前测试事实与真实启动策略一致。
3. `main.py` 不再直接维护 region 细节。
4. `registry.py` 与 `README.md` 已记录当前 region 与边界。
5. API contract 未变化。

---

## 遗留项

本次仅完成 SUG-006 Phase 0，以下内容仍未实施：

1. `ObjectStore` 的 `max_entries` 与 LRU。
2. hit/miss/set/delete/error metrics。
3. `WriteThroughPolicy` persister 失败语义修正。
4. `WriteBehindPolicy` dirty key ack/requeue。
5. `/api/cache/stats` 展示 region spec 与 metrics。
6. `stock_market` / `hot_spots` logical region 收口。
7. 多 worker / 多实例前的 Redis 或外部运行态 store 评估。

---

## 后续建议

下一步建议继续 SUG-006 Phase 1：先给 `ObjectStore` 增加容量边界和基础 metrics。该阶段仍可保持小步执行，不需要签发 DEC；如果后续要引入 Redis 或改变部署假设，再另立 DEC。
