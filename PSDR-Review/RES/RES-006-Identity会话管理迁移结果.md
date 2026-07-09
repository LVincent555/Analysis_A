# RES-006: Identity 会话管理迁移结果
**日期**: 2026-07-08
**状态**: [PARTIAL]
**类型**: Infra / Backend / Architecture / Migration
**层级**: Backend
**关联**: DEC-002, SUG-003, PRB-003, RES-005

---

## 执行摘要

本次继续推进 DEC-002 的 Level 1 Identity 迁移，把管理员会话管理从旧三层 `SessionService` 调整为 Identity 上下文内的六边形切片。

已完成范围：

1. `backend/app/routers/session_mgmt.py` 改为 HTTP adapter。
   - 保留 `/api/admin/sessions` 路由前缀与既有端点。
   - 路由不再直接调用 `app.services.session_service.SessionService`。
   - FastAPI、HTTPException、Depends 等框架细节仍停留在 router 适配层。
2. 新增 `backend/app/contexts/identity/application/session_admin.py`。
   - 承接管理员会话列表、详情、统计、单会话撤销、用户全会话撤销、过期清理。
   - 会话展示状态计算进入 application 层，后续可再抽成领域策略。
3. 扩展 Identity application DTO 与 ports。
   - `commands.py` 新增撤销与清理命令。
   - `queries.py` 新增管理员会话列表与详情查询。
   - `ports.py` 扩展会话查询、统计、清理、审计日志端口。
4. 扩展 SQLAlchemy infrastructure adapter。
   - `repositories.py` 增加 admin session 查询、统计、批量撤销、清理过期会话能力。
   - 新增 `SqlAlchemyIdentityAuditLogRepository`，让 Identity 通过端口写入 `OperationLog`。
5. 迁移会话管理 API schema。
   - `contexts/identity/api/schemas.py` 承接 session 管理相关请求/响应模型。
6. 修正一个旧行为缺口。
   - `/api/admin/sessions/user/{user_id}/revoke-all` 的 `exclude_current=True` 现在会读取当前认证会话并真正排除当前会话。
   - 旧路由中 `current_session_id` 位置只是占位 `pass`，因此无法实际排除。

---

## 验证结果

默认单元测试：

```powershell
cd backend
uv run pytest
```

结果：

```text
25 passed, 75 warnings
```

新增测试：

```text
tests/unit/test_session_admin_use_cases.py: 6
```

覆盖点：

1. 管理员会话列表返回 `total/page/page_size/items` 兼容结构。
2. 会话详情不存在时返回 application-level `NOT_FOUND`。
3. 单会话撤销会标记 `is_revoked` 并写入 `OperationLog`。
4. `exclude_current=True` 会保留当前会话并撤销其它会话。
5. `exclude_current=True` 在无法识别当前会话时拒绝执行，避免误踢当前会话。
6. 过期清理只删除超过保留天数的旧会话。

API contract 路由数量：

```powershell
uv run --extra analysis python scripts/export_api_contract.py | uv run python -c "import json,sys; print(len(json.load(sys.stdin)))"
```

结果：

```text
124
```

格式检查：

```powershell
git diff --check -- .gitignore PSDR-Review backend\pyproject.toml backend\uv.lock backend\app backend\tests backend\scripts
```

结果：无 whitespace error；当前仓库仍有若干 LF/CRLF 提示。

---

## 当前边界状态

已改善：

1. `session_mgmt` 路由不再依赖旧 `services/session_service.py`。
2. Identity application 对会话管理拥有明确用例入口。
3. SQLAlchemy、OperationLog 等基础设施依赖集中在 infrastructure adapter。
4. `exclude_current` 从占位逻辑变成可测试行为。

仍未完成：

1. `session_mgmt.py` 仍位于旧 `app/routers` 包中，尚未搬到 `contexts/identity/api/router.py`。
2. `services/session_service.py` 文件仍保留，需后续确认是否还有外部调用，再决定删除或改为兼容壳。
3. `user_mgmt.py`、`role_mgmt.py` 仍直接依赖旧 `UserService`、`RoleService`。
4. `db_models.py` 仍是聚合 ORM 文件，Identity ORM ownership 尚未拆分。
5. `main.py` 仍直接注册旧 router，composition root 还未整理。

---

## 后续建议

下一批建议优先迁移 RBAC 查询侧：

1. 先迁 `role_mgmt.py` 的 permissions、角色列表、角色详情、用户权限查询、权限检查。
2. 再迁 `user_mgmt.py` 的用户列表、详情、状态筛选和 active sessions 查询。
3. 命令侧迁移前先决定 `users.role` 与 `user_roles + permissions` 的兼容策略，避免 RBAC 双轨继续扩大。
4. 同步修复旧 `UserService` mutation 后审计日志可能未提交的问题。
