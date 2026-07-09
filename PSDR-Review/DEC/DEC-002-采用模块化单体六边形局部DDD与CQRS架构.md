# DEC-002: 采用模块化单体、六边形架构、局部 DDD 与 CQRS 查询侧

**日期**: 2026-07-08
**状态**: [IMPLEMENTED / EXITED]
**类型**: Infra / Backend / Architecture / Refactor
**层级**: Backend + frontend-client
**关联**: SUG-003, SUG-004, RES-001, PRB-001, PRB-002, PRB-003, RES-004, RES-005, RES-006, RES-007, RES-008, RES-009, RES-010, RES-011, RES-012, RES-013, RES-014, RES-015, RES-016, RES-017, RES-018, RES-019, RES-020, RES-021, RES-022, RES-023, RES-024, RES-025

---

## 决策

签发决定：`stock_analysis_app/backend` 后续架构重构采用 **模块化单体 + 六边形架构 + 局部 DDD + CQRS 查询侧**。

本决定正式取代“按 Java 三层 controller/service/dao 思路继续扩展后端”的默认方向。后续新增后端功能和阶段性重构，应优先按业务上下文组织到 `contexts/`，并遵守 `api / application / domain / infrastructure` 的边界。

---

## 决策解释

本项目后端同时包含两类不同复杂度的业务：

1. 规则密集、状态密集的身份和运维能力：用户、会话、权限、token、配置、审计、缓存管理。
2. 读密集、计算密集的数据分析能力：股票排行、板块趋势、热度、策略查询、报表。

完整 DDD 对第一类有价值，但对第二类容易引入不必要的样板和性能约束。因此本项目采用局部 DDD，只在有真实业务规则和状态不变量的上下文中使用领域模型；对于分析查询，采用 CQRS 查询侧和 read model，允许直接使用优化 SQL、Pandas、Numpy 和缓存。

该方案保持单体部署，避免微服务拆分带来的部署、事务、观测和数据一致性成本。

---

## 采用内容

### 1. 模块化单体

后端按业务上下文拆分，而不是按技术层横向拆分。

目标上下文：

- `identity`：用户、认证、授权、角色、权限、会话、token。
- `market_data`：股票、板块、日线数据、导入、基础数据完整性。
- `analysis`：排行、趋势、信号、策略、分析查询。
- `board_heat`：外部板块、热度、同步、挖掘结果。
- `operations`：系统配置、缓存管理、操作日志、审计、后台运维。

### 2. 六边形架构

每个上下文内部采用以下层次：

```text
context/
  api/
  application/
  domain/
  infrastructure/
```

依赖方向：

```text
api -> application -> domain
infrastructure -> application ports + domain
domain -> Python stdlib / shared value types
```

禁止反向依赖：

- `domain` 不依赖 FastAPI。
- `domain` 不依赖 SQLAlchemy。
- `domain` 不依赖缓存、JWT、HTTP、文件系统和外部 API。
- `application` 不抛 FastAPI 的 `HTTPException`。
- `api` 不写核心业务规则。

### 3. 局部 DDD

DDD 仅用于规则密集区域。

优先使用 DDD 的对象：

- `User`
- `Role`
- `Permission`
- `DeviceSession`
- `LoginPolicy`
- `SessionPolicy`
- `TokenVersion`
- `AccountStatus`
- `SystemConfig`
- `OperationLog`

不强制 DDD 的区域：

- 股票排行查询。
- 板块趋势查询。
- 热度列表查询。
- 分析结果读取。
- 报表导出。

### 4. CQRS 查询侧

读写职责分离：

- command 负责状态变化和业务规则。
- query 负责读取、聚合、计算和展示。

查询侧允许：

- 直接使用 read repository。
- 返回 DTO/read model。
- 使用优化 SQL。
- 使用 Numpy/Pandas。
- 使用缓存和预计算结果。

查询侧禁止：

- 写入业务状态。
- 隐式修改用户、会话、配置或缓存策略。
- 为了形式化 DDD 强制构造聚合根。

### 5. 迁移治理基线

本决策同时签发以下治理约束，防止迁移期出现新旧结构双轨漂移：

1. 默认后端测试入口为 `cd backend; uv run pytest`，默认只运行离线单元测试。
2. 每个迁移 Level 开始前冻结 API contract，至少记录路径、方法、状态码和主要 JSON key。
3. `main.py` 定位为 composition root，只做装配，不继续承载业务规则。
4. `db_models.py` 不作为第一步物理拆分；先建立 ORM ownership 表，再逐步迁移 repository adapter。
5. 数据库连接模块应版本化，私密连接信息只放 `.env`；Level 0 处理当前 `database.py` 被忽略的问题。
6. `core/security.py`、`auth_middleware.py`、`crypto/*`、`core/caching/*` 归为平台/共享能力，具体业务上下文只能通过 port/adapter 使用。
7. Level 0 后补充 import 边界自动检查，禁止 `domain` 依赖 FastAPI、SQLAlchemy、JWT、缓存和 router/schema。

---

## 当前实施状态快照

**快照日期**: 2026-07-08
**总体状态**: [IMPLEMENTED / EXITED]

对照本 DEC 的 Level 0 到 Level 5，当前架构迁移已经完成并退场。旧 router 与部分旧 service 仍作为兼容壳或 legacy adapter 被保留，但新增业务默认进入 `contexts/`，composition root 已直接装配 context router。

当前事实：

1. **Level 0 已完成**。
   - 已建立 `contexts/`、`shared/`、ORM ownership、composition root 记录、API contract 导出与 `uv` 测试基线。
   - `uv run pytest` 已作为默认单元测试入口。
2. **Level 1 基本完成**。
   - Identity 的认证、会话、用户管理、角色权限已迁入 `contexts.identity`。
   - 旧 `user_service.py`、`role_service.py`、`session_service.py` 已退场。
   - `routers/auth.py`、`routers/user_mgmt.py`、`routers/session_mgmt.py`、`routers/role_mgmt.py` 仍保留兼容壳。
3. **Level 1.5 已完成**。
   - 已补齐无 HTTPS 时的登录/刷新公钥信封、JWT/master key 强制真实密钥、secure gateway nonce 去重和内部 header HMAC 加固。
   - 该子轨涉及 backend 与 `frontend-client`，结果记录见 RES-013。
4. **Level 2 基本完成**。
   - 已完成 `log_mgmt`、`config_mgmt`、`cache_mgmt`、`core/audit.py` 与 `PolicyEngine` 收敛，分别记录在 RES-011、RES-012、RES-014、RES-015、RES-016。
   - 已修复 API contract 嵌套路由导出问题。
   - 已修复配置值校验、bool 字符串、非法值先落库、批量更新半成功等风险。
   - `admin.py` 中的数据导入/删除已在 Level 4 迁入 MarketData；`/admin/login-history` 已迁入 Identity。
5. **Level 3 已完成**。
   - `rank_jump` 与 `steady_rise` 已迁入 `contexts.analysis` 的 query DTO、port、use case、infrastructure adapter 与 API adapter，旧 router 退为兼容入口，结果见 RES-017。
   - `/api/dates`、`/api/analyze/{period}`、`/api/market/volatility-summary` 已迁入 `contexts.analysis`，结果见 RES-018。
   - `/api/stocks/raw-data`、`/api/stock/search`、`/api/stock/{stock_code}` 已迁入 `contexts.market_data`，结果见 RES-019。
   - `sector.py` 板块查询侧已迁入 `contexts.market_data`，结果见 RES-020。
   - `industry.py` 与 `industry_detail.py` 已迁入 `contexts.analysis`，结果见 RES-021。
   - `strategies.py` 单针下二十查询已迁入 `contexts.analysis`，结果见 RES-022。
   - `/api/hot-spots/full` 已迁入 `contexts.analysis`，结果见 RES-023。
6. **Level 4 已完成**。
   - BoardHeat 查询侧、外部板块同步/热度计算管理、客户端离线同步、数据导入/删除和登录历史已迁入对应上下文，结果见 RES-024。
7. **Level 5 已完成**。
   - `main.py` 已直接装配 context router，旧 router 退为兼容壳，结果见 RES-025。

当前验证：

```powershell
cd backend
uv run pytest
```

结果：

```text
106 tests collected; full test run exited 0
```

API contract：

```text
126 routes
```

---

## 不采用内容

本决策明确不采用以下方向：

1. 不采用完整教科书 DDD 全家桶。
2. 不采用 Java 式 controller/service/dao/dto/vo/mapper 横向目录继续扩展。
3. 不拆微服务。
4. 不为每张表建立 repository interface。
5. 不让 SQLAlchemy ORM model 同时承担 domain entity。
6. 不一次性重写全部后端。
7. 不在架构迁移中顺手改变对外 API 行为，除非另立 DEC。

---

## 分级重构实施计划

### Level 0：设计冻结与骨架落地 [已完成]

目标：让后续代码有明确落点。

行动：

1. 建立 `backend/app/contexts/` 和 `backend/app/shared/`。
2. 为 `identity / market_data / analysis / board_heat / operations` 建立空骨架。
3. 在每个上下文中建立 `api / application / domain / infrastructure`。
4. 写入上下文 README 或轻量说明，标明职责和禁止依赖。
5. 建立 API contract 基线，锁定当前路由、状态码和响应字段。
6. 建立 ORM ownership 表，先标注模型归属，不立即拆分 `db_models.py`。
7. 决定 `database.py` / `.env` / `database.py.example` 的配置治理策略。
8. 形成 `main.py` composition root 装配清单。
9. 建立 `uv` + pytest 默认测试入口，并将历史真实服务/真实数据测试排除出默认集合。
10. 不迁移大量代码，不改 API 行为。

验收：

- 后端仍可启动。
- 新功能可以明确归属上下文。
- 架构规则有文档入口。
- `cd backend; uv run pytest` 可通过。
- `PRB-003` 记录的双轨迁移风险已有控制项。

当前结果记录：RES-004、RES-005。

### Level 1：Identity 迁移 [基本完成]

目标：先迁移最有业务规则价值、风险也最高的认证会话链路。

行动：

1. 将登录、刷新、登出、改密、当前用户依赖迁入 `contexts/identity`。
2. 将 token 发行、token 校验、session key store 封装为 infrastructure adapter。
3. 将登录策略、会话策略、账号状态、token version 放入 domain/application。
4. 保持 `/api/auth/*` 对外路径兼容。
5. 旧 `backend/app/auth/` 可短期作为兼容壳。

验收：

- login/refresh/logout/logout-all/change-password 回归通过。
- 多设备登录、撤销会话、账号禁用、账号过期、强制下线回归通过。
- router 中不再承载核心认证规则。

当前结果记录：RES-006、RES-007、RES-008、RES-009、RES-010。

遗留边界：

- `app/auth/*` 仍保留兼容入口。
- `users.role` 与 `user_roles` 的授权源兼容期策略由 DEC-003 管理。

### Level 1.5：HTTP 环境安全加固 [已完成]

目标：在暂时没有 HTTPS 的前提下，补齐登录阶段、JWT 密钥、secure gateway 防重放和内部转发信任边界。

执行依据：SUG-004。

行动：

1. 禁止生产环境使用默认 `JWT_SECRET_KEY` 与 `MASTER_ENCRYPTION_KEY`；仅允许显式 `ALLOW_INSECURE_DEV_KEYS=true` 的开发模式兜底。
2. 保持 JWT 使用 HS256，但要求强随机 `JWT_SECRET_KEY`；后续如需要轮换再增加 `kid` 与 key ring。
3. 增加登录公钥信封：`/api/auth/secure-login` 使用服务端公钥 pin + RSA-OAEP + 一次性 AES-GCM key 加密登录 payload。
4. 登录响应中的 `token / refresh_token / session_key / user` 通过同一登录信封加密返回，响应使用独立 AES-GCM `iv`，不复用请求 `iv`。
5. 前端 `authService.login()` 优先调用 secure-login，公钥、`key_id` 与 fingerprint 固定在 Electron 客户端构建中。
6. 新增 `/api/auth/secure-refresh`，避免 refresh token 通过明文 refresh 请求暴露。
7. 旧 `/api/auth/login` 仅保留开发兼容；`REQUIRE_SECURE_LOGIN=true` 时拒绝明文登录。
8. `/api/secure` 增加按 `user_id + device_id + nonce` 的 5 分钟去重。
9. `AuthMiddleware` 不再信任外部裸传的 `x-secure-gateway: 1`，内部 ASGI 转发改用服务端私有 HMAC header。
10. 内部 HMAC 绑定 `method + path + timestamp + body_hash`，避免外部请求仅靠伪造 header 绕过 secure gateway。
11. 增加密钥生成脚本和 `.env.example` 示例。
12. 第二阶段再评估将 Electron token/session key 从 renderer `localStorage` 迁到 main process + safeStorage。

验收：

- HTTP 抓包看不到明文用户名、密码、token、refresh token、session key。
- 未设置真实密钥时，非开发模式后端启动失败。
- 重放同一个 secure-login 或 `/api/secure` 请求失败。
- 外部请求伪造 `x-secure-gateway: 1` 不能绕过 secure gateway。
- 公钥 fingerprint 不匹配时，前端拒绝发送 secure-login。
- `uv run pytest` 通过，并新增后端安全单元测试；前端 secure-login 模块已通过构建与公钥 fingerprint 校验，独立前端单测列为后续补充。
- API contract 因新增 `/api/auth/secure-login` 与 `/api/auth/secure-refresh` 增至 126 routes，已写入 RES-013。

结果记录：RES-013。

### Level 2：Operations 迁移 [基本完成]

目标：把后台管理、配置、日志、缓存和审计从业务查询中分离。

行动：

1. 迁移缓存管理、系统配置、操作日志、审计。
2. 将 admin 权限依赖收束到 api/application 边界。
3. 梳理配置读取链路，避免策略、缓存和 DB 互相穿透。
4. 保持管理接口路径兼容。

验收：

- 普通用户不能调用管理接口。
- 配置变更、日志查询、缓存清理回归通过。
- Operations 不直接污染 Identity、Analysis 的内部实现。

当前结果记录：RES-011、RES-012、RES-014、RES-015、RES-016。

已完成：

- 操作日志查询、详情、统计、导出、清理迁入 `contexts.operations`。
- 系统配置查询、策略读取、密码校验、更新、批量更新、重置迁入 `contexts.operations`。
- 缓存统计、清理、重载、健康检查和 GC 迁入 `contexts.operations`。
- 审计缓冲和同步回调迁入 `contexts.operations.infrastructure.audit_buffer`，旧 `core.audit` 退为兼容入口。
- 策略提供器迁入 `contexts.operations.infrastructure.policy_engine`，旧 `services.policy_engine` 退为兼容入口。
- `LogService`、`ConfigService` 已降级为兼容门面。
- `cache_mgmt.py` 已降级为兼容入口。

遗留：

- `admin.py` 中的数据导入/删除已在 Level 4 迁入 MarketData；`/admin/login-history` 已迁入 Identity。

### Level 3：MarketData 与 Analysis 查询侧迁移 [已完成]

目标：把读密集分析接口整理成 CQRS 查询侧，不强套完整 DDD。

行动：

1. 将股票、板块、行业、策略、排行、趋势接口归入对应上下文。
2. 建立 query service 和 read repository。
3. 保留现有高性能 Numpy/Pandas/缓存方案。
4. 将写入类动作与查询类动作分开。
5. 对重型查询补充结果一致性测试。

验收：

- 主要分析接口迁移前后返回结构兼容。
- 查询侧没有业务写入副作用。
- 读模型和缓存 key 可追踪。

当前结果记录：RES-017、RES-018、RES-019、RES-020、RES-021、RES-022、RES-023。

已完成：

- `rank_jump` 与 `steady_rise` 查询入口已迁入 `contexts.analysis`。
- `/api/dates`、`/api/analyze/{period}`、`/api/market/volatility-summary` 已迁入 `contexts.analysis`。
- `/api/stocks/raw-data`、`/api/stock/search`、`/api/stock/{stock_code}` 已迁入 `contexts.market_data`。
- `sector.py` 板块查询侧已迁入 `contexts.market_data`。
- `industry.py` 与 `industry_detail.py` 已迁入 `contexts.analysis`。
- `strategies.py` 单针下二十查询已迁入 `contexts.analysis`。
- `/api/hot-spots/full` 已迁入 `contexts.analysis`。
- 旧 `routers/rank_jump.py`、`routers/steady_rise.py`、`routers/analysis.py`、`routers/stock.py`、`routers/sector.py`、`routers/industry.py`、`routers/industry_detail.py` 与 `routers/strategies.py` 已退为兼容入口或保留局部兼容入口。
- API contract 保持 126 routes。

遗留：

- `HotSpotsCache`、策略算法与部分 SignalCalculator 依赖仍作为 legacy service 由 infrastructure adapter 包装，算法本体不在本 Level 重写。

### Level 4：BoardHeat 与同步导入迁移 [已完成]

目标：把外部数据源和同步逻辑封装到 adapter。

行动：

1. 迁移外部板块同步、热度计算和热度查询。
2. 将 Akshare、pywencai、文件导入等外部依赖放入 infrastructure。
3. 应用层只编排同步和查询用例。

验收：

- 外部同步失败可以定位到 adapter。
- 热度查询不依赖同步实现细节。
- BoardHeat 与 Analysis 的边界清楚。

当前结果记录：RES-024。

已完成：

- `board_heat.py` 查询侧迁入 `contexts.board_heat`。
- `ext_board_mgmt.py` 外部板块同步、热度计算、自动映射、同步历史和运维统计迁入 `contexts.board_heat`。
- `sync.py` 客户端离线同步迁入 `contexts.market_data`。
- `admin.py` 数据文件、导入、删除和已导入日期迁入 `contexts.market_data`。
- `/admin/login-history` 迁入 `contexts.identity`。
- API contract 保持 126 routes。

遗留：

- `core/data_manager.py` 仍作为启动检查兼容入口调用历史导入脚本。
- `scripts/import_*`、`scripts/sync_ext_boards.py`、`scripts/task_board_heat.py` 保留 CLI 兼容入口。

### Level 5：旧结构退场 [已完成]

目标：结束迁移期，降低双结构维护成本。

行动：

1. 删除或改造成兼容壳的旧 `routers/`、`services/`、`auth/` 文件。
2. 拆分或重组 `db_models.py`，至少建立 ORM model 聚合入口。
3. 删除无引用代码。
4. 补齐最终 RES。

验收：

- 新增后端功能默认进入 `contexts/`。
- 旧横向目录不再承载新增业务。
- 架构迁移有完整 RES 记录。

当前结果记录：RES-025。

已完成：

- `main.py` 直接装配 `contexts/*/api` router。
- 已迁移业务的旧 `app.routers.*` 文件退为兼容壳。
- legacy service 与脚本作为 infrastructure adapter 的被包装实现保留。
- `app.routers.secure` 作为平台安全网关边界保留，后续平台化需另立 DEC。
- `db_models.py` 暂不物理拆分，后续 ORM 文件拆分需单独处理 metadata/import 稳定性。

---

## 退场规则

本 DEC 是架构设计决策，不作为无限期任务单。

当 Level 0 到 Level 5 完成，并产生对应 RES 后，本架构决策流程退场：

1. 不再继续围绕“是否采用该架构”重复决策。
2. 后续新增能力按本 DEC 的架构原则直接落地。
3. 若某个上下文需要偏离本架构，必须另立 PRB/SUG/DEC。
4. 若后续出现更大范围架构变化，例如拆微服务、替换 ORM、引入任务总线，也必须另立 DEC。

---

## 负责人 / 截止时间

- **负责人**: 项目维护者
- **截止时间**: 分级执行，不设单一硬截止；每个 Level 独立验收并写 RES

---

## 验收标准

1. `SUG-003` 已记录具体方案和推荐理由。
2. `DEC-002` 已签发采用目标架构。
3. `PSDR-Review/META/INDEX.md` 已登记本决策。
4. 后续新增后端功能默认遵守 `contexts/` 模块化单体结构。
5. 架构迁移按 Level 0 到 Level 5 分级推进，完成后写 RES 并退场。
6. `RES-004` 已记录 `uv` 测试基线，作为 Level 0 的测试入口依据。
