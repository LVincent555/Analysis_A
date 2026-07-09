# RES-033: 后端缓存系统治理 Phase 5 实验运行态外部化落地结果

**日期**: 2026-07-09
**状态**: [SOLVED / EXPERIMENTAL]
**类型**: Infra / Backend / Cache / Security / Runtime / Testing
**层级**: Backend
**关联**: SUG-006, RES-026, RES-027, RES-028, RES-029, RES-032, PRB-001, SUG-001, DEC-002, RES-014

---

## 执行摘要

已完成 SUG-006 Phase 5 的实验功能落地：新增运行态安全材料外部化 adapter，使 `session_keys`、登录 nonce、secure nonce 可以选择使用同机共享的 `diskcache` 后端。

本功能默认关闭，默认仍为 `memory`，保持当前单进程行为不变。实验 `diskcache` 后端只适合同一台机器上的多 worker，不是跨机器分布式方案；真正多实例部署仍应另签 DEC 引入 Redis 等外部运行态服务。

---

## 已完成改动

### 1. 新增实验 RuntimeStateStore

新增：

```text
backend/app/shared/runtime_state_store.py
```

支持：

```text
EXPERIMENTAL_RUNTIME_STATE_BACKEND=memory
EXPERIMENTAL_RUNTIME_STATE_BACKEND=diskcache
```

能力：

1. `set/get/delete`
2. `delete_prefix`
3. `clear_namespace`
4. `mark_once(namespace, key, ttl)` 原子防重放

默认 `memory` 是进程内 store；实验 `diskcache` 是同机共享 store。

### 2. replay nonce 接入 runtime state

修改：

```text
backend/app/shared/replay_nonce_store.py
```

`login_nonce_store` 与 `secure_nonce_store` 现在通过 runtime state store 记录 nonce：

1. 默认 memory 行为保持不变。
2. `diskcache` 启用后，同机多个 worker 可共享 replay nonce。
3. login nonce 与 secure nonce 使用不同 namespace，互不污染。

### 3. session key store 接入实验外部后端

修改：

```text
backend/app/contexts/identity/infrastructure/session_key_store.py
```

新语义：

1. 默认 `memory` 时保持旧路径：`UnifiedCache.session_keys` + fallback。
2. `diskcache` 启用时，`session_key_store` 以 runtime state store 为准。
3. `remove(user_id)` 可按 `user_id:` prefix 清理该用户所有设备的 session key。
4. 外部后端启用时不读本进程 UnifiedCache，避免多 worker 下旧本地 key 残留。

### 4. 安全配置校验与示例环境变量

修改：

```text
backend/app/core/security_settings.py
backend/.env.example
backend/app/core/caching/README.md
```

新增示例：

```text
EXPERIMENTAL_RUNTIME_STATE_BACKEND=memory
RUNTIME_STATE_DIR=.runtime_state
```

`validate_runtime_security_config()` 会拒绝未知 backend。

### 5. 单测补强

新增：

```text
backend/tests/unit/test_runtime_state_store.py
```

覆盖：

1. `diskcache` runtime state 可跨 store 实例共享。
2. `mark_once` 跨 store 实例仍能阻止 replay。
3. session key store 在实验 `diskcache` 后端下可跨 store 实例读取。
4. login nonce / secure nonce namespace 隔离。
5. 未知 backend 会被拒绝。

---

## 验证结果

实验 runtime state 专项：

```text
uv run pytest -q tests/unit/test_runtime_state_store.py
```

结果：

```text
4 passed
```

安全 / session / 缓存相关专项：

```text
uv run pytest -q tests/unit/test_session_key_store.py tests/unit/test_security_level_1_5.py tests/unit/test_cache_core.py
```

结果：

```text
25 passed
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
132 tests collected
```

API contract：

```text
126 routes
```

---

## 是否满足验收

满足 Phase 5 当前实验验收：

1. secure-login replay nonce 可通过实验后端跨 worker 共享。
2. `/api/secure` session key 可通过实验后端跨 worker 共享。
3. 默认单进程模式不依赖 Redis，也不依赖 `diskcache` runtime state。
4. 未启用实验功能时，原有 API contract 与测试行为不变。

---

## 注意事项

1. `diskcache` 后端只适合同机多 worker，不适合跨机器多实例。
2. 当前未实现 Redis adapter；如果要多机器部署，应新签 DEC。
3. Numpy read model、API response cache、reports cache 没有迁移到 runtime state store。
4. config cache invalidation bus 仍未实现；多 worker 下配置热更新仍建议通过 reload 或后续引入 Redis/pubsub。

---

## 后续建议

SUG-006 的 Phase 0 至 Phase 5 已完成。下一步不建议继续扩缓存内核，除非出现真实部署触发条件：

1. `uvicorn --workers > 1` 需要长期开启。
2. 后端部署到多台机器。
3. 配置热更新需要跨 worker 自动失效。

届时建议新签 DEC，主题可以是：

```text
DEC-005: 后端运行态安全材料外部化到 Redis
```
