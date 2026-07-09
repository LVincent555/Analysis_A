# RES-015: Operations 审计缓冲迁移与字段映射修复结果

**日期**: 2026-07-08
**状态**: [SOLVED]
**类型**: Infra / Backend / Architecture / Migration / Bugfix / Testing
**层级**: Backend
**关联**: DEC-002, SUG-003, RES-011, RES-012, RES-014

---

## 结果摘要

已将旧 `app/core/audit.py` 的审计缓冲和同步回调迁入 `contexts.operations.infrastructure.audit_buffer`，旧 `core.audit` 退为兼容入口。同时修复旧同步回调仍按 `user_id / target / ip` 等旧字段写入 `OperationLog` 的字段漂移风险。

---

## 已完成改动

1. 新增 `contexts.operations.infrastructure.audit_buffer`：
   - `AuditLogEntry`
   - `AuditLogBuffer`
   - `create_audit_sync_callback`
   - `audit_log` 单例
2. `app/core/audit.py` 改为兼容入口，继续支持旧导入：

```python
from app.core.audit import audit_log, create_audit_sync_callback
```

3. 审计同步回调改为写入新 `OperationLog` 字段：
   - `log_type`
   - `action`
   - `operator_id`
   - `target_type`
   - `target_name`
   - `ip_address`
   - `detail`
   - `status`
   - `created_at`
4. `main.py` 无需改调用方式，仍通过同步器注册 audit callback。

---

## 测试与验证

后端单元测试：

```text
cd backend
uv run pytest
```

结果：

```text
77 passed, 212 warnings
```

API contract：

```text
126 routes
```

新增测试：

1. 审计缓冲超过上限时丢弃最旧记录。
2. 审计同步回调能按新 `OperationLog` 字段写库。

---

## 遗留项

1. 旧兼容 API `AuditLogBuffer.log(user_id, action, target, detail, ip)` 仍保留旧参数名；这是为了不破坏旧调用点。
2. `PolicyEngine` 仍待从旧 `app.services` 收敛为明确 port/adapter。
3. `admin.py` 中数据导入/删除属于跨上下文 command，仍需后续结合 MarketData / Analysis 迁移处理。

---

## 后续建议

DEC-002 Level 2 下一步处理 `PolicyEngine`，将配置策略读取从旧 `app.services` 中收束出来。
