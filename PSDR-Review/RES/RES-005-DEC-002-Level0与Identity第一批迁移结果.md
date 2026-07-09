# RES-005: DEC-002 Level 0 与 Identity 第一批迁移结果

**日期**: 2026-07-08
**状态**: [PARTIAL]
**类型**: Infra / Backend / Architecture / Migration
**层级**: Backend
**关联**: DEC-002, SUG-003, PRB-003, RES-004

---

## 执行摘要

本次开始把 DEC-002 和 SUG-003 从文档决策推进到代码落地。

已完成范围：

1. Level 0 架构骨架
   - 新增 `backend/app/contexts/`。
   - 新增 `identity / market_data / analysis / board_heat / operations` 五个上下文。
   - 每个上下文具备 `api / application / domain / infrastructure` 四层目录。
   - 新增上下文 README，说明迁移职责和边界。

2. shared 抽象
   - 新增 `backend/app/shared/`。
   - 提供 `errors`、`pagination`、`result`、`ports`、`time`、`unit_of_work` 等基础抽象。

3. 配置治理
   - `backend/app/database.py` 从被忽略的本地配置文件，调整为可版本化数据库连接模块。
   - `.gitignore` 不再忽略 `backend/app/database.py`，改为忽略 `backend/app/database.local.py`。
   - 私密连接信息继续通过 `backend/.env` 或环境变量注入。

4. Level 0 治理工件
   - 新增 `backend/app/contexts/API_CONTRACT_BASELINE.md`。
   - 新增 `backend/app/contexts/ORM_OWNERSHIP.md`。
   - 新增 `backend/app/contexts/COMPOSITION_ROOT.md`。
   - 新增 `backend/scripts/export_api_contract.py`，可导出当前 FastAPI 路由 contract。

5. 架构边界自动检查
   - 新增 `backend/tests/unit/test_architecture_boundaries.py`。
   - 默认单测会检查 `contexts/*/domain` 不依赖 FastAPI、SQLAlchemy、JWT、cache、router、service、ORM model。
   - 默认单测会检查每个上下文保留四层目录结构。

6. Identity 第一批迁移
   - 新增 `contexts/identity/application/ports.py`。
   - 新增 `contexts/identity/application/commands.py`。
   - 新增 `contexts/identity/application/use_cases.py`。
   - 新增 `contexts/identity/domain/value_objects.py` 与 `policies.py`。
   - 新增 `contexts/identity/infrastructure/password_hasher.py`。
   - 新增 `contexts/identity/infrastructure/jwt_tokens.py`。
   - 新增 `contexts/identity/infrastructure/session_key_store.py`。
   - 新增 `contexts/identity/infrastructure/repositories.py` 与 `policy_provider.py`。
   - 旧 `app.auth.password`、`app.auth.jwt_handler`、`app.auth.dependencies` 保持兼容入口，内部开始委托给 Identity context。
   - `routers/auth.py` 的 register/login/refresh/logout/logout-all/change-password/me/sessions 已委托给 Identity application use case/query。
   - `app.auth.dependencies.get_current_user()` 已委托给 `AuthenticateAccessTokenUseCase`，旧模块保留 FastAPI 兼容入口。

---

## 验证结果

默认单元测试：

```powershell
cd backend
uv run pytest
```

结果：

```text
19 passed
```

测试收集：

```text
tests/unit/test_architecture_boundaries.py: 2
tests/unit/test_auth_session_lifecycle.py: 10
tests/unit/test_session_key_store.py: 3
tests/unit/test_shared_primitives.py: 4
```

API contract 导出：

```powershell
uv run --extra analysis python scripts/export_api_contract.py
```

当前可导出路由数量：

```text
124
```

编译检查：

```powershell
uv run python -m py_compile ...
```

结果：通过。

---

## 未完成范围

本 RES 不代表 DEC-002 已全部完成。

仍未完成：

1. Identity 的 HTTP router 仍主要位于旧 `routers/auth.py`、`routers/user_mgmt.py`、`routers/session_mgmt.py`、`routers/role_mgmt.py`。
2. `routers/auth.py` 已变薄，但尚未整体搬到 `contexts/identity/api/router.py`。
3. `db_models.py` 仍是临时 ORM 聚合文件，尚未建立完整 repository adapter。
4. `main.py` 仍直接注册旧 router 并承载较多启动逻辑。
5. Operations、MarketData、Analysis、BoardHeat 只完成骨架和归属说明，尚未迁移真实业务代码。
6. 真实 PostgreSQL、真实服务、前端/Electron、重型分析查询尚未进入默认测试覆盖。

---

## 下一步

1. 继续 Level 1 Identity：迁移登录/刷新/登出 use case，并让旧 router 只做兼容壳。
2. 建立 Identity repository ports 与 SQLAlchemy adapter，逐步减少 router 对 `db_models.py` 的直接依赖。
3. 拆 `main.py` 的路由注册和启动生命周期装配函数。
4. 为 auth API 增加 TestClient 级别回归，覆盖 middleware/依赖注入链路。
