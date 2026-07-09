# RES-012: Operations 配置管理迁移与配置值校验修复结果

**日期**: 2026-07-08
**状态**: [PARTIAL]
**类型**: Infra / Backend / Architecture / Migration / Bugfix / Testing
**层级**: Backend
**关联**: DEC-002, DEC-003, SUG-003, PRB-003, RES-011

---

## 执行摘要

本次在 RES-011 的 Operations 日志迁移之后，继续迁移系统配置管理模块。

已完成：

1. 将 `/api/admin/config` 从旧 router/service 迁入 `contexts.operations.api.config_router`。
2. 将配置读取、策略查询、密码校验迁入 Operations query-side use cases。
3. 将配置更新、批量更新、重置默认值迁入 Operations command-side use cases。
4. 将配置值类型规则集中到 `contexts.operations.domain.config`。
5. 将旧 `ConfigService` 降级为兼容门面，避免旧 import 路径立刻失效。

---

## 改动范围

新增文件：

1. `backend/app/contexts/operations/domain/config.py`
2. `backend/app/contexts/operations/application/config_queries.py`
3. `backend/app/contexts/operations/application/config_commands.py`
4. `backend/app/contexts/operations/infrastructure/config_cache.py`
5. `backend/app/contexts/operations/api/config_router.py`
6. `backend/tests/unit/test_operations_config_use_cases.py`

调整文件：

1. `backend/app/contexts/operations/application/ports.py`
2. `backend/app/contexts/operations/application/queries.py`
3. `backend/app/contexts/operations/application/commands.py`
4. `backend/app/contexts/operations/infrastructure/repositories.py`
5. `backend/app/main.py`
6. `backend/app/routers/config_mgmt.py`
7. `backend/app/services/config_service.py`

---

## 修复问题

1. 修复 bool 字符串写入风险。
   - 旧逻辑中字符串 `"false"` 会因为 truthy 被序列化成 `"true"`。
   - 新逻辑通过 `parse_config_value()` 统一识别 `true/false/1/0/yes/no/on/off/y/n`。
2. 修复非法 int/json 可能先落库再报错的风险。
   - 新命令用例先校验、归一化，再写 ORM 对象。
3. 修复批量更新半成功风险。
   - 新批量更新先全量校验。
   - 任一项非法时返回 `success=False`，不写入任何配置，也不刷新缓存。
4. 修复默认值 reset 的类型歧义。
   - 默认值先按配置类型解析，再进入更新流程。
5. 统一配置更新审计。
   - `config_update` 由 Operations infrastructure 写入 `OperationLog`。

---

## 行为合同

保持不变：

1. `/api/admin/config` 路径、method 与主要 JSON 字段保持不变。
2. `categories/configs/policy/password/policy/login/policy/session/validate-password` 等端点保留。
3. `ConfigService` 保留兼容类名和主要方法。
4. 配置更新后仍会刷新 UnifiedCache 的 config 区域。

有意修正：

1. 未知 category 返回应用层校验错误，不再静默返回空结果。
2. 非法配置值返回校验错误，且不写库。
3. 批量更新失败时不再保留部分成功结果。

---

## 验证结果

默认单元测试：

```powershell
cd backend
uv run pytest
```

结果：

```text
65 passed, 193 warnings
```

新增测试：

```text
tests/unit/test_operations_config_use_cases.py: 6
```

覆盖点：

1. `"false"` 字符串会被写成布尔 false。
2. 非法 int 在写库前被拒绝。
3. 批量更新遇到非法项时不会半成功。
4. 批量合法更新只刷新一次配置缓存。
5. reset 使用 typed default。
6. 配置查询、密码策略和密码校验读取 DB 值与默认值。

API contract：

```powershell
uv run --extra analysis python scripts/export_api_contract.py | uv run python -c "import json,sys; print(len(json.load(sys.stdin)))"
```

结果：

```text
124
```

配置路由已指向：

```text
app.contexts.operations.api.config_router
```

---

## 当前边界状态

已改善：

1. Operations context 已承接日志管理与配置管理两个管理类模块。
2. 配置 query/command use case 不依赖 FastAPI、SQLAlchemy、ORM、legacy service。
3. 配置值类型规则从 service 私有静态方法迁入 domain。
4. 配置缓存刷新从 application 剥离到 infrastructure adapter。

仍未完成：

1. `cache_mgmt.py` 仍直接依赖缓存全局对象。
2. `core/audit.py` 审计同步回调仍需迁入 Operations infrastructure。
3. `PolicyEngine` 仍位于旧 `app.services`，后续可迁为 Operations/Identity 间的 policy port adapter。
4. `db_models.py` 尚未按 context ownership 拆分。

---

## 后续建议

1. 下一步优先迁移 `cache_mgmt.py`，并修复非法 `cache_type` 返回成功、同步 reload 阻塞事件循环、缓存操作缺少审计的问题。
2. 随后处理 `core/audit.py` 字段映射风险，避免同步审计写入旧字段。
3. 再评估是否把 `PolicyEngine` 从 `app.services` 迁成 Operations/Identity 之间的明确端口。
