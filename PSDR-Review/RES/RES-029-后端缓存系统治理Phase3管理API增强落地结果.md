# RES-029: 后端缓存系统治理 Phase 3 管理 API 增强落地结果

**日期**: 2026-07-09
**状态**: [SOLVED]
**类型**: Infra / Backend / Cache / Operations / Testing
**层级**: Backend
**关联**: SUG-006, RES-026, RES-027, RES-028, PRB-001, SUG-001, DEC-002, RES-014

---

## 执行摘要

已完成 SUG-006 Phase 3 的落地：增强 Operations 缓存管理 API，让后台不只看到粗略 stats，而是能看到 region registry、运行态 stats、健康分级、精确清理和目标化 reload。

本次不新增路由数量，不引入新依赖，不改变旧调用的默认行为：

1. `/api/cache/stats` 保留旧字段，并新增 `region_specs` 与 `cache_regions`。
2. `/api/cache/clear?cache_type=all` 保持旧语义，只清热点、API、报表缓存。
3. `/api/cache/reload` 默认仍等价于 reload all。

---

## 已完成改动

### 1. stats 返回 registry + runtime 组合视图

修改：

```text
backend/app/contexts/operations/application/cache_management.py
backend/app/contexts/operations/infrastructure/cache_management.py
backend/app/contexts/operations/application/ports.py
```

`GetCacheStatsUseCase` 现在返回：

```text
numpy_cache
hotspots_cache
unified_cache
region_specs
cache_regions
```

其中：

1. `region_specs` 来自 `core/caching/registry.py`。
2. `cache_regions` 将 registry 与 runtime stats 合并，标记每个 region 是否已在运行时注册。
3. 保留 `unified_cache` 原始 stats，避免旧管理面调用被破坏。

### 2. health 增加分级与 region 细节

`GetCacheHealthUseCase` 现在返回：

```text
status: healthy | degraded
warnings
region_count
regions
```

当前 degraded 条件：

1. registry 中登记的 region 未在 runtime 注册。
2. region metrics 中存在 loader/persister/operation error。
3. FileStore 出现 recovery。
4. ObjectStore 容量超过 90%。
5. Write-Behind dirty backlog 超过阈值。

路由层仍保留异常兜底；真正执行失败时 `/api/cache/health` 返回 `status=error`。

### 3. clear 支持 region 与 all_disposable

`ClearCacheUseCase` 新增支持：

```text
cache_type=region:<name>
cache_type=all_disposable
```

规则：

1. `region:<name>` 只能清理 registry 中 `clearable=True` 的 region。
2. `session_keys` 因 `clearable=False` 会被拒绝，避免误清安全运行态材料。
3. `all_disposable` 会清热点缓存，并按 registry 清理 `disposable=True 且 clearable=True` 的 UnifiedCache region。
4. 旧的 `api`、`report`、`hotspots`、`all` 行为保持兼容。
5. `region:` 参数无效时，路由返回 HTTP 400。

### 4. reload 支持目标化

`ReloadAllCacheUseCase` 现在支持：

```text
target=all
target=numpy
target=stock_market
target=hotspots
target=config
```

规则：

1. `target=all` 保持旧行为，调用 `preload_cache()`。
2. `target=numpy` / `stock_market` 重载 Numpy read model。
3. `target=hotspots` 清理热点缓存并重新预加载近期热点。
4. `target=config` 从数据库刷新 config region。
5. 未知 target 返回 HTTP 400。

### 5. 单测补强

修改：

```text
backend/tests/unit/test_operations_cache_use_cases.py
```

覆盖：

1. stats 是否返回 registry 与 runtime 组合视图。
2. `region:<name>` 可清理 clearable region。
3. `region:session_keys` 被拒绝。
4. `all_disposable` 按 registry 清理。
5. health 在 region metrics 有 error 时降级。
6. reload 支持 `numpy` / `hotspots` / `config`。
7. reload 拒绝未知 target。
8. 旧 reload / health / gc 行为仍可用。

---

## 验证结果

Operations 缓存专项：

```text
uv run pytest -q tests/unit/test_operations_cache_use_cases.py
```

结果：

```text
10 passed
```

缓存内核专项：

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
127 tests collected
```

API contract：

```text
126 routes
```

---

## 是否满足验收

满足 Phase 3 验收：

1. `/api/cache/stats` 已展示 registry 信息、region spec 与 runtime stats。
2. `/api/cache/health` 已区分 healthy / degraded / error。
3. region 级清理只允许 clearable region。
4. `session_keys` 等不可清理运行态材料不会被管理 API 误清。
5. reload 已支持按目标执行。
6. 后端全量测试通过，API contract 未变化。

---

## 注意事项

1. `all` 仍保持旧语义，只清热点、API、报表缓存；清理 registry 中所有可丢弃 region 需要显式使用 `all_disposable`。
2. `hotspots` 仍是历史 logical cache，没有正式登记进 `core/caching/registry.py`，本次通过 Operations adapter 继续纳入管理。
3. health 的 degraded 当前是保守运行态判断，不是业务不可用判断；例如 error metrics 或容量水位会提示 degraded，但不代表 API 已失败。
4. `target=hotspots` 当前会调用启动预热路径中的热点预加载逻辑，仍依赖 Numpy read model 已有可用日期。

---

## 后续建议

下一步可进入 SUG-006 Phase 4：历史缓存收口。

建议优先：

1. 将 `stock_market` 作为 logical region 纳入 registry。
2. 将 `hot_spots` 作为 logical region 纳入 registry 或 adapter spec。
3. 为 Analysis / MarketData 查询侧建立 cache port，减少直接 import 历史缓存单例。
