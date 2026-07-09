# 后端统一缓存系统

本目录是项目级本机缓存平台，当前定位为单体后端内的进程内 + 本机磁盘缓存，不是分布式缓存系统。

## 运行时 region

| region | owner | store | policy | 说明 |
|------|------|------|------|------|
| `sessions` | identity | ObjectStore | WriteBehind | 会话心跳运行态，后台同步到数据库 |
| `session_keys` | identity/security | ObjectStore | WriteThrough | `/api/secure` 运行时会话密钥，按 `user_id:device_id` 存储 |
| `users` | identity | ObjectStore | CacheAside | 用户读缓存，默认 1 小时 TTL |
| `config` | operations | ObjectStore | WriteThrough | 系统配置缓存，启动预热，配置写入后刷新 |
| `api_response` | platform | FileStore | DiskCache TTL | API 响应磁盘缓存 |
| `reports` | platform | FileStore | DiskCache TTL | 报表文件磁盘缓存 |
| `stock_market` | market_data/analysis | VectorStore | ReadOnly NumpyCache | 历史 Numpy 行情 read model 的 logical region |
| `hot_spots` | analysis | HotSpotsStore | HotSpotsCache TTL | 历史热点榜聚合缓存的 logical region |

权威登记在 `registry.py`，实际注册入口在 `bootstrap.py`。

## 边界

1. `domain` 层不能依赖缓存。
2. `application` 层应通过 port 使用缓存，不直接操作 `UnifiedCache`。
3. `infrastructure` 层可以适配 `core.caching`。
4. `session_keys` 是运行态安全材料，不是普通可随意清理的性能缓存。
5. 多 worker / 多实例部署前，`session_keys` 与 replay nonce store 需要外部化。

## 历史缓存

`numpy_cache` 与 `HotSpotsCache` 当前仍作为历史高性能缓存保留，并已登记为 `stock_market` / `hot_spots` logical region。现阶段只收口治理视图与管理入口，不重写底层高性能查询实现。

## 实验运行态外部化

`shared/runtime_state_store.py` 提供实验型运行态 store：

| backend | 说明 |
|------|------|
| `memory` | 默认值，保持当前单进程内存行为 |
| `diskcache` | 实验功能，同一台机器多 worker 共享 `session_keys`、login nonce、secure nonce |

启用方式：

```text
EXPERIMENTAL_RUNTIME_STATE_BACKEND=diskcache
RUNTIME_STATE_DIR=.runtime_state
```

`diskcache` 只适合同机多 worker，不是跨机器分布式方案。多后端实例部署时仍应另行引入 Redis 等外部运行态 store，并签发新的 DEC。
