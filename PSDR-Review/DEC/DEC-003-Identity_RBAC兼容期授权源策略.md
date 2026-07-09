# DEC-003: Identity RBAC 兼容期授权源策略
**日期**: 2026-07-08
**状态**: [ACTIVE]
**类型**: Infra / Backend / Architecture / Security
**层级**: Backend
**关联**: DEC-002, SUG-003, PRB-003, RES-007

---

## 背景

当前后端同时存在两套 RBAC 信息源：

1. `users.role`
   - 旧系统粗粒度角色字段。
   - 当前 admin API gate 仍主要通过 `current_user.role == "admin"` 判断。
2. `roles` / `user_roles` / `Role.permissions`
   - v1.1.0 引入的角色权限表。
   - 支持 `*`、`prefix:*`、具体 permission。

如果迁移时继续隐式混用，会导致“分配了 admin role 但不能访问 admin API”或“`users.role=admin` 无需 user_roles 就拥有 `*`”这类行为难以解释。

---

## 决策

迁移期采用双轨兼容，但明确优先级：

1. `users.role` 保留为粗粒度兼容字段。
   - `users.role == "admin"` 继续作为 admin API 访问 gate。
   - `users.role == "admin"` 在权限查询中继续返回 `["*"]`。
2. `user_roles + Role.permissions` 作为细粒度业务权限来源。
   - 非 admin 用户的权限从 active roles 合并得到。
   - `*` 与 `prefix:*` 通配规则由 Identity domain 统一判断。
3. 角色分配/移除命令不隐式同步 `users.role`。
   - 保持旧 `RoleService.assign_role_to_user()` 的行为合同。
   - 避免迁移期间通过分配 role 突然改变 admin API gate。
4. 用户管理命令仍负责维护 `users.role` 兼容字段。
   - 后续迁移 `user_mgmt.py` 时再显式收敛 `super_admin/admin/user/readonly` 与兼容字段映射。

---

## 后果

好处：

1. 不破坏现有 admin API 授权入口。
2. 查询侧权限语义可先稳定迁移到 Identity。
3. 命令侧迁移可以保持旧行为，不夹带授权语义大变更。

代价：

1. 兼容期仍存在 `users.role` 与 `user_roles` 双轨。
2. “分配 admin role 是否获得 admin API 访问权”在当前阶段答案仍是“不自动获得”。
3. 后续必须安排一次独立的 RBAC 收敛迁移。

---

## 实施计划

1. 已完成：RBAC 查询侧迁入 Identity application 与 domain。
2. 下一步：角色命令侧迁入 Identity application command use cases，但保持本 DEC 的兼容策略。
3. 再下一步：用户管理迁移时明确 `users.role` 的写入边界。
4. 最终阶段：决定是否废弃 `users.role`，或将其降级为 derived/cache 字段。
