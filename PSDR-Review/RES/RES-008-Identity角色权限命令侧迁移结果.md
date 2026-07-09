# RES-008: Identity 角色权限命令侧迁移结果
**日期**: 2026-07-08
**状态**: [PARTIAL]
**类型**: Infra / Backend / Architecture / Migration
**层级**: Backend
**关联**: DEC-002, DEC-003, SUG-003, PRB-003, RES-007

---

## 执行摘要

本次在 RES-007 的 RBAC 查询侧迁移基础上，继续把角色权限管理的命令侧迁入 Identity application。

已完成范围：

1. 新增 `backend/app/contexts/identity/application/rbac_commands.py`。
   - `CreateRoleUseCase`
   - `UpdateRoleUseCase`
   - `DeleteRoleUseCase`
   - `AssignRoleToUserUseCase`
   - `RemoveRoleFromUserUseCase`
2. 扩展 Identity commands。
   - `CreateRoleCommand`
   - `UpdateRoleCommand`
   - `DeleteRoleCommand`
   - `AssignRoleToUserCommand`
   - `RemoveRoleFromUserCommand`
3. 扩展 Identity role repository port 与 SQLAlchemy adapter。
   - 创建角色、更新权限、删除角色、分配/移除用户角色。
   - 查询用户、角色、重复分配关系。
4. 扩展审计日志 port。
   - `IdentityAuditLogRepository.record()` 支持 `old_value` 与 `new_value`。
   - 角色 create/update/delete/assign/remove 成功后写入 `OperationLog`。
5. 调整 `backend/app/routers/role_mgmt.py`。
   - 角色读写端点均已委托给 Identity application。
   - `role_mgmt.py` 不再直接依赖旧 `services.role_service.RoleService`。

---

## 行为合同

保持旧行为：

1. 重复创建角色名称返回 validation error。
2. 系统预设角色不可删除。
3. 系统预设角色权限不可修改。
4. 已分配用户的角色不可删除。
5. 重复 assign 角色保持幂等成功。
6. remove role 不额外要求关系必须存在，保持旧删除语义。

遵循 DEC-003：

1. 分配/移除 `user_roles` 不隐式同步 `users.role`。
2. `users.role == "admin"` 仍作为迁移期 admin gate 与 `*` 权限兼容入口。

---

## 验证结果

默认单元测试：

```powershell
cd backend
uv run pytest
```

结果：

```text
36 passed, 121 warnings
```

新增测试：

```text
tests/unit/test_rbac_command_use_cases.py: 6
```

覆盖点：

1. 创建角色会持久化 role 并写入 `OperationLog`。
2. 重复角色名称会被拒绝。
3. 系统角色权限修改会被拒绝且不写审计日志。
4. 已分配用户的角色不可删除。
5. 角色分配幂等，且不会同步 `users.role`。
6. 移除角色关系会删除 `user_roles` 并写入审计日志。

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

1. `role_mgmt.py` 已从旧 service 编排转为 Identity HTTP adapter。
2. RBAC 查询规则、命令规则、审计日志写入都有 application use case 承接。
3. 角色命令侧事务提交集中到 repository adapter，审计日志和业务变更同事务提交。

仍未完成：

1. `services/role_service.py` 文件仍存在，需后续确认无其它引用后删除或改兼容壳。
2. `user_mgmt.py` 仍依赖旧 `UserService`，且仍存在审计日志可能未提交、404 被包成 500 等问题。
3. `users.role` 与 `user_roles` 的最终收敛尚未实施，仅通过 DEC-003 明确了迁移期策略。
4. `role_mgmt.py` 仍位于旧 `app/routers` 包中，尚未搬到 `contexts/identity/api/router.py`。

---

## 后续建议

1. 下一批迁移 `user_mgmt.py` 查询侧，优先处理用户列表、详情、状态筛选与 active sessions。
2. 同步修复 `UserService` 审计日志提交缺口。
3. 在用户命令侧迁移时实现 DEC-003 中 `users.role` 写入边界。
4. 最后清理旧 `RoleService` 与 `SessionService` 残留引用。
