# RES-011: Operations 日志管理迁移与 API 契约导出修复结果

**日期**: 2026-07-08
**状态**: [PARTIAL]
**类型**: Infra / Backend / Architecture / Migration / Testing
**层级**: Backend
**关联**: DEC-002, DEC-003, SUG-003, PRB-003, RES-010

---

## 执行摘要

本次继续推进 DEC-002 后端架构迁移，完成两个关键事项：

1. 修复 `backend/scripts/export_api_contract.py` 只展开一层 `include_router` 的问题。
   - 支持递归展开 FastAPI 0.139 中的 `_IncludedRouter.original_router.routes`。
   - 允许 `contexts/*/api/router.py` 这种上下文聚合路由形式继续保持 API contract 可观测。
2. 将操作日志管理从旧三层 router/service 迁入 Operations context。
   - `app.contexts.operations.domain` 承接日志类型与动作词汇。
   - `app.contexts.operations.application` 承接日志查询侧 use case、清理命令与端口。
   - `app.contexts.operations.infrastructure` 承接 SQLAlchemy 查询/命令 adapter。
   - `app.contexts.operations.api.log_router` 承接 `/api/admin/logs` HTTP adapter。

---

## 改动范围

新增文件：

1. `backend/app/contexts/operations/domain/logs.py`
2. `backend/app/contexts/operations/application/ports.py`
3. `backend/app/contexts/operations/application/queries.py`
4. `backend/app/contexts/operations/application/commands.py`
5. `backend/app/contexts/operations/application/log_queries.py`
6. `backend/app/contexts/operations/application/log_commands.py`
7. `backend/app/contexts/operations/infrastructure/repositories.py`
8. `backend/app/contexts/operations/api/log_router.py`
9. `backend/tests/unit/test_api_contract_export.py`
10. `backend/tests/unit/test_operations_log_use_cases.py`

调整文件：

1. `backend/scripts/export_api_contract.py`
2. `backend/app/main.py`
3. `backend/app/routers/log_mgmt.py`
4. `backend/app/services/log_service.py`

---

## 行为合同

保持不变：

1. `/api/admin/logs` 路径、HTTP method 与主要 JSON 字段保持不变。
2. 日志列表、统计、用户活动、详情、CSV 导出、清理旧日志仍保留原功能。
3. `backend/app/routers/log_mgmt.py` 保留兼容导入，避免旧 import 路径立即失效。
4. `LogService` 保留兼容门面，旧调用会转调 Operations use case。

有意修正：

1. `start_date/end_date` 非 `YYYY-MM-DD` 时返回应用层校验错误，不再静默忽略筛选条件。
2. `page/page_size/days/limit` 增加边界约束。
3. `cleanup_old_logs(days<=0)` 不再允许执行，避免负天数导致异常范围删除。
4. API contract 导出支持嵌套路由，避免迁移到上下文聚合路由后误报路由数量下降。

---

## 验证结果

默认单元测试：

```powershell
cd backend
uv run pytest
```

结果：

```text
59 passed, 180 warnings
```

新增/覆盖测试：

```text
tests/unit/test_api_contract_export.py: 1
tests/unit/test_operations_log_use_cases.py: 9
```

覆盖点：

1. API contract 导出递归展开嵌套 `include_router`。
2. 日志列表过滤、分页、日期范围、搜索与标签格式化。
3. 日志详情 JSON 字段解析。
4. 日志不存在返回应用层 NOT_FOUND。
5. 日志统计聚合。
6. 用户活动同时覆盖 operator 与 target user。
7. CSV 导出维持旧字段。
8. 旧日志清理只删除过期记录。
9. 清理天数非法时拒绝执行。

API contract：

```powershell
uv run --extra analysis python scripts/export_api_contract.py | uv run python -c "import json,sys; print(len(json.load(sys.stdin)))"
```

结果：

```text
124
```

日志路由已指向：

```text
app.contexts.operations.api.log_router
```

---

## 当前边界状态

已改善：

1. Operations context 不再只是空骨架，已承接第一个完整 CQRS 查询侧模块。
2. `contexts/operations/application` 未依赖 FastAPI、SQLAlchemy、ORM、legacy service，符合架构守卫。
3. `main.py` 对日志管理已直接注册 context API adapter。
4. API contract 工具已适配模块化上下文聚合路由。

仍未完成：

1. `config_mgmt.py` 仍在旧 router/service 结构中。
2. `cache_mgmt.py` 仍直接依赖全局缓存对象和同步重载逻辑。
3. `core/audit.py` 中审计同步回调仍需迁入 Operations infrastructure 并核对字段映射。
4. `db_models.py` 仍是聚合 ORM 文件，尚未按 context ownership 拆分。
5. PostgreSQL 集成测试、真实 FastAPI TestClient 权限测试尚未建立。

---

## 后续建议

1. 迁移 `config_mgmt.py` 前先修配置值类型校验、bool 字符串序列化、批量更新事务边界。
2. 迁移 `cache_mgmt.py` 时引入 `CacheManagementPort`，避免 API 层直连 `numpy_cache`、`HotSpotsCache`、`core.caching.cache`。
3. 修复 `core/audit.py:create_audit_sync_callback()` 对 `OperationLog` 字段的旧映射风险。
4. 每迁移一个 context API adapter 后继续跑 API contract count，保持 124 或明确记录破坏性变更 DEC。
