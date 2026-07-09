# RES-009: Identity 用户管理查询侧迁移结果
**日期**: 2026-07-08
**状态**: [PARTIAL]
**类型**: Infra / Backend / Architecture / Migration
**层级**: Backend
**关联**: DEC-002, DEC-003, SUG-003, PRB-003, RES-008

---

## 执行摘要

本次继续推进 Identity Level 1 迁移，把用户管理的查询侧迁入 Identity application。

已完成范围：

1. 新增 `backend/app/contexts/identity/application/user_queries.py`。
   - `ListAdminUsersUseCase`
   - `GetAdminUserDetailUseCase`
2. 扩展 Identity queries 与 ports。
   - `ListAdminUsersQuery`
   - `GetAdminUserDetailQuery`
   - `IdentityUserQueryRepository`
3. 扩展 SQLAlchemy 查询适配器。
   - `SqlAlchemyIdentityUserQueryRepository`
   - 承接用户列表、软删排除、搜索、角色/状态筛选、排序、active sessions 计数、用户详情 sessions 查询。
4. 调整 `backend/app/routers/user_mgmt.py`。
   - `GET /api/admin/users` 已切换到 `ListAdminUsersUseCase`。
   - `GET /api/admin/users/{user_id}` 已切换到 `GetAdminUserDetailUseCase`。
   - 用户创建/更新/删除/禁用/重置密码/解锁/批量操作暂未迁移，仍保留旧 `UserService`。

---

## 行为合同

保持旧行为：

1. 用户列表返回 `total/page/page_size/items`。
2. 默认排除 `deleted_at` 非空用户。
3. 支持 `search`、`role`、`status`、`sort_by`、`sort_order`。
4. `active_sessions` 统计未撤销 session。
5. 用户详情返回用户基础信息和未撤销 sessions。
6. 用户详情 sessions 按 `last_active desc` 排序。

---

## 验证结果

默认单元测试：

```powershell
cd backend
uv run pytest
```

结果：

```text
39 passed, 132 warnings
```

新增测试：

```text
tests/unit/test_user_admin_query_use_cases.py: 3
```

覆盖点：

1. 用户列表排除软删用户并统计未撤销 session。
2. 用户详情只返回未撤销 sessions，并按最近活跃排序。
3. 用户不存在时返回 application-level `NOT_FOUND`。

API contract 路由数量：

```powershell
uv run --extra analysis python scripts/export_api_contract.py | uv run python -c "import json,sys; print(len(json.load(sys.stdin)))"
```

结果：

```text
124
```

---

## 当前边界状态

已改善：

1. `user_mgmt.py` 的查询侧不再依赖旧 `UserService`。
2. 用户查询逻辑进入 Identity application + infrastructure adapter。
3. 用户详情中的 session 读取与 RES-006 的 session 管理迁移方向保持一致。

仍未完成：

1. `user_mgmt.py` 命令侧仍依赖旧 `UserService`。
2. 旧 `UserService` 中 create/update/delete/reset/batch 的审计日志可能未提交问题仍待处理。
3. 用户命令侧仍承担 `users.role` 与 `user_roles` 同步逻辑，尚未按 DEC-003 迁入 Identity command use cases。
4. `user_mgmt.py` 仍位于旧 `app/routers` 包中，尚未搬到 `contexts/identity/api/router.py`。

---

## 后续建议

1. 下一批迁移 `user_mgmt.py` 命令侧，优先处理 create/update/delete/toggle/reset/unlock/batch。
2. 迁移时同步修复审计日志提交缺口。
3. 把用户命令侧的角色写入规则显式实现为 DEC-003 的兼容策略。
4. 最后删除或兼容壳化旧 `UserService`、`RoleService`、`SessionService`。
