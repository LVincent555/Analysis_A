# RES-007: Identity 角色权限查询侧迁移结果
**日期**: 2026-07-08
**状态**: [PARTIAL]
**类型**: Infra / Backend / Architecture / Migration
**层级**: Backend
**关联**: DEC-002, SUG-003, PRB-003, RES-006

---

## 执行摘要

本次继续推进 DEC-002 的 Identity Level 1 迁移，把角色权限管理的查询侧迁入 Identity 上下文，命令侧暂时保留旧 `RoleService`。

已完成范围：

1. 新增权限目录与匹配规则。
   - `backend/app/contexts/identity/domain/permissions.py`
   - 承接 `ALL_PERMISSIONS` 与 `*`、`prefix:*` 权限匹配规则。
2. 新增 RBAC 查询用例。
   - `backend/app/contexts/identity/application/rbac_queries.py`
   - 覆盖权限目录、角色列表、角色详情、用户权限列表、用户权限检查。
3. 扩展 application queries 与 ports。
   - `ListRolesQuery`
   - `GetRoleDetailQuery`
   - `GetUserPermissionsQuery`
   - `CheckUserPermissionQuery`
   - `IdentityRoleQueryRepository`
4. 扩展 SQLAlchemy 查询适配器。
   - `SqlAlchemyIdentityRoleQueryRepository`
   - 承接角色列表、角色详情、用户角色权限读取。
5. 调整 `backend/app/routers/role_mgmt.py`。
   - `/api/admin/roles/permissions` 已切换到 `GetPermissionsCatalogUseCase`。
   - `/api/admin/roles` 已切换到 `ListRolesUseCase`。
   - `/api/admin/roles/{role_id}` 已切换到 `GetRoleDetailUseCase`。
   - `/api/admin/roles/user/{user_id}/permissions` 已切换到 `GetUserPermissionsUseCase`。
   - `/api/admin/roles/user/{user_id}/check/{permission}` 已切换到 `CheckUserPermissionUseCase`。

---

## 验证结果

默认单元测试：

```powershell
cd backend
uv run pytest
```

结果：

```text
30 passed, 97 warnings
```

新增测试：

```text
tests/unit/test_rbac_query_use_cases.py: 5
```

覆盖点：

1. 权限目录包含 `*` 与角色管理权限。
2. 角色列表默认排除 inactive role，并返回 `user_count`。
3. 角色详情返回分配用户列表。
4. 兼容旧 `users.role == "admin"` 直接授予 `*`。
5. 用户角色权限支持 `query:*` 这类前缀通配符，并忽略 inactive role。

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

1. RBAC 查询逻辑不再依赖旧 `services.role_service.RoleService`。
2. 权限匹配规则从 service 静态方法迁入 Identity domain。
3. 查询侧以 CQRS 风格形成独立用例，便于后续替换读模型。

仍未完成：

1. 角色创建、更新、删除、分配、移除仍使用旧 `RoleService`。
2. `users.role` 与 `user_roles + permissions` 的双轨 RBAC 语义尚未签发最终兼容策略。
3. `RoleService` 内的命令侧审计、事务、系统角色约束尚未迁入 application command use cases。
4. `role_mgmt.py` 仍位于旧 `app/routers` 包中，尚未搬到 `contexts/identity/api/router.py`。

---

## 后续建议

1. 先写一份 RBAC 兼容小决定，明确迁移期 `users.role`、`user_roles`、`permissions` 的优先级。
2. 再迁角色命令侧，把 create/update/delete/assign/remove 拆成 application command use cases。
3. 同步补事务测试：成功 mutation 必须写入 `OperationLog`，失败 mutation 不能留下半提交。
4. 之后再迁 `user_mgmt.py` 查询侧，复用本次 RBAC query 与 RES-006 的 session query 能力。
