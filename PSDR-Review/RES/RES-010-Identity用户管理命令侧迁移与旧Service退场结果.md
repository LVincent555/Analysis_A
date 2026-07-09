# RES-010: Identity 用户管理命令侧迁移与旧 Service 退场结果
**日期**: 2026-07-08
**状态**: [PARTIAL]
**类型**: Infra / Backend / Architecture / Migration
**层级**: Backend
**关联**: DEC-002, DEC-003, SUG-003, PRB-003, RES-009

---

## 执行摘要

本次继续推进 Identity Level 1 迁移，把用户管理命令侧迁入 Identity application，并删除已退场的旧三层 service 文件。

已完成范围：

1. 新增 `backend/app/contexts/identity/application/user_commands.py`。
   - `CreateAdminUserUseCase`
   - `UpdateAdminUserUseCase`
   - `DeleteAdminUserUseCase`
   - `ToggleAdminUserStatusUseCase`
   - `ResetAdminUserPasswordUseCase`
   - `UnlockAdminUserUseCase`
   - `BatchAdminUsersUseCase`
2. 扩展 Identity commands 与 ports。
   - 新增用户管理命令 DTO。
   - 新增 `IdentityUserCommandRepository`。
3. 扩展 SQLAlchemy adapter。
   - 新增 `SqlAlchemyIdentityUserCommandRepository`。
   - 承接用户创建、角色同步、软删除/硬删除、会话撤销、批量更新。
4. 调整 `backend/app/routers/user_mgmt.py`。
   - 用户管理全部端点已委托 Identity application。
   - router 不再依赖旧 `UserService`。
5. 删除旧 service 孤岛文件。
   - `backend/app/services/user_service.py`
   - `backend/app/services/role_service.py`
   - `backend/app/services/session_service.py`

---

## 修复问题

1. 修复旧 `UserService` mutation 后审计日志可能未提交的问题。
   - 新实现中业务变更与 `OperationLog` 在同一个 use case 中写入，并在同一事务提交。
2. 修复 reset-password 用户不存在时可能被通用异常包装成 500 的问题。
   - 新 use case 使用 `ErrorCode.NOT_FOUND`，router 映射为 404。
3. 更新用户传入非法 role 时，先校验再写 ORM 对象，避免失败路径留下脏对象。

---

## 行为合同

保持旧行为：

1. `super_admin/admin` 映射到兼容字段 `users.role="admin"`。
2. `user/readonly` 映射到兼容字段 `users.role="user"`。
3. roles 表中存在同名 active role 时，同步 `user_roles`。
4. 传统 `admin/user` 在 roles 表不存在时仍允许作为兼容角色。
5. 删除、禁用、重置密码、批量禁用/删除会撤销相关 session。
6. 删除/禁用/批量操作排除操作者自己的账号。

---

## 验证结果

默认单元测试：

```powershell
cd backend
uv run pytest
```

结果：

```text
49 passed, 180 warnings
```

新增测试：

```text
tests/unit/test_user_admin_command_use_cases.py: 9
```

覆盖点：

1. 创建用户会映射 `users.role`、同步 `user_roles`、写入审计日志。
2. 重复用户名返回 conflict。
3. 更新用户 role 会同步角色表并写审计日志。
4. 非法 role 不会把 ORM 对象改脏。
5. 软删除用户会撤销 session 并写审计日志。
6. 禁用自己会被拒绝。
7. 重置密码会更新 hash、递增 token_version、撤销 session、写审计日志。
8. 解锁不存在用户返回 NOT_FOUND。
9. 批量操作排除操作者自己并写审计日志。

API contract 路由数量：

```powershell
uv run --extra analysis python scripts/export_api_contract.py | uv run python -c "import json,sys; print(len(json.load(sys.stdin)))"
```

结果：

```text
124
```

旧 service 引用扫描：

```powershell
rg "UserService|RoleService|SessionService|services\.(user_service|role_service|session_service)" backend/app backend/tests
```

结果：无运行时代码引用。

架构守卫：

```text
tests/unit/test_architecture_boundaries.py 新增 application 层 import 边界检查
```

约束：`contexts/*/application` 不得导入 FastAPI、SQLAlchemy、JWT、`app.routers`、`app.services`、`app.db_models` 等框架或旧模块。

---

## 当前边界状态

已改善：

1. Identity 的 auth/session/role/user 管理核心行为已进入 application use cases。
2. 旧三层 `UserService`、`RoleService`、`SessionService` 已从运行时代码退场。
3. 管理侧 mutation 审计日志开始具备可测试的同事务写入保障。

仍未完成：

1. Identity HTTP adapter 仍主要位于旧 `backend/app/routers/*` 包中。
2. `main.py` 仍直接注册旧 router 路径。
3. `db_models.py` 仍是聚合 ORM 文件。
4. Operations、MarketData、Analysis、BoardHeat 仍主要是骨架或未迁移。
5. 真实 PostgreSQL、集成测试、前端联调测试尚未覆盖。

---

## 后续建议

1. 把 Identity router 物理迁入 `contexts/identity/api`，旧 `app/routers/*` 保留兼容导入壳。
2. 增加 application 层架构守卫，禁止 `contexts/*/application` 依赖 FastAPI、router、旧 service。
3. 开始 Operations 或 MarketData 的下一批迁移前，先整理 `main.py` composition root。
