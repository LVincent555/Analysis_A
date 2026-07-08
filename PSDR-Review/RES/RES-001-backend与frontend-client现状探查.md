# RES-001: backend 与 frontend-client 现状探查

**日期**: 2026-07-07
**状态**: [SOLVED]
**类型**: Infra / Documentation / Audit
**层级**: 顶层
**关联**: DEC-001

---

## 执行摘要

本次按 `DEC-001` 确立的 PSDR 文档治理方式，对 `stock_analysis_app` 当前核心运行面做了一轮只读探查，重点范围为：

- `backend/`: FastAPI 后端、认证/加密、缓存、数据导入、业务服务、管理接口、策略模块。
- `frontend-client/`: Electron 桌面客户端、React 渲染层、加密 API 客户端、本地 SQLite 缓存、自动更新。

本次探查没有修改业务代码，没有运行会连接数据库或外部服务的测试。结论是：项目主体已经从早期 Web 分析应用演进为“FastAPI 后端 + Electron 桌面客户端 + 加密网关 + 多级缓存 + 外部板块/系统管理”的复合应用，功能面较完整，但配置治理、版本一致性、安全默认值、客户端旧代码残留和部署环境变量存在明显收敛空间。

---

## 探查范围

### backend

重点查看：

- `backend/app/main.py`
- `backend/app/config.py`
- `backend/app/database.py.example`
- `backend/app/middleware/auth_middleware.py`
- `backend/app/routers/`
- `backend/app/services/`
- `backend/app/core/`
- `backend/app/auth/`
- `backend/app/crypto/`
- `backend/app/db_models.py`
- `backend/scripts/import_data_robust.py`
- `backend/tests/`
- `backend/migrations/`

### frontend-client

重点查看：

- `frontend-client/package.json`
- `frontend-client/electron/main.js`
- `frontend-client/electron/preload.js`
- `frontend-client/electron/database.js`
- `frontend-client/src/App.js`
- `frontend-client/src/services/`
- `frontend-client/src/hooks/useAppState.js`
- `frontend-client/src/components/modules/`
- `frontend-client/src/pages/`

---

## 当前架构快照

### 后端定位

`backend` 是 FastAPI 应用，启动入口为 `backend/app/main.py`。应用生命周期大致为：

1. `run_startup_checks()` 执行数据导入和一致性检查。
2. `init_cache_system()` 注册统一缓存分区。
3. `cache.reload_configs()` 预热系统配置。
4. `preload_cache()` 加载 Numpy 缓存和热点榜缓存。
5. `start_syncer()` 启动数据库同步器，负责 Write-Behind 会话和审计日志同步。

后端默认安全策略为：

- 普通业务 API 强制通过 `/api/secure` 加密网关访问。
- `/api/auth/*` 作为登录、注册、刷新、登出的直连白名单。
- `FORCE_SECURE_API=true` 时，直接访问 `/api/*` 会被中间件拦截。

### 客户端定位

`frontend-client` 是 Electron 桌面客户端，入口为 `electron/main.js` 和 `src/App.js`。

客户端运行形态：

- 开发模式加载 `http://localhost:3000`。
- 生产模式加载 `build/index.html`。
- React 业务请求大多走 `apiClient -> secureApi -> /api/secure`。
- Electron 主进程提供设备 ID、本地 sql.js 缓存、窗口控制和自动更新 IPC。

### 数据流

当前主要数据链路：

```text
Excel / data 文件
  -> backend/scripts/import_data_robust.py
  -> PostgreSQL
  -> backend/app/core/startup.py 预加载 Numpy 缓存
  -> backend/app/services/* 业务分析
  -> /api/secure 加密网关
  -> frontend-client/src/services/api.js
  -> React 模块与管理页面
```

---

## 结果与证据

### 后端模块现状

| 模块 | 当前状态 |
|------|----------|
| 路由层 | `backend/app/routers/` 下约 22 个路由文件，覆盖分析、股票、行业、板块、策略、认证、同步、缓存、系统管理、用户/角色/会话/日志管理。 |
| 服务层 | `backend/app/services/` 下约 35 个 Python 文件，包含热点分析、行业、股票、板块、信号、系统配置、用户、角色、会话、外部板块、策略检测。 |
| 缓存 | 同时存在 Numpy 缓存和统一缓存系统。统一缓存注册 `sessions`、`users`、`config`、`api_response`、`reports` 等分区。 |
| 认证 | JWT + bcrypt + 用户会话表 + 设备 ID；登录返回访问令牌、刷新令牌和加密会话密钥。 |
| 加密 | AES-256-GCM；业务请求经 `/api/secure` 解密后用 ASGITransport 转发到内部路由。 |
| 数据导入 | `import_data_robust.py` 支持幂等状态文件、MD5、事务、清理旧日期、去重、换手率修补。 |
| 数据模型 | 主要表包括 `stocks`、`daily_stock_data`、`sectors`、`daily_sector_data`、`users`、`user_sessions`、`operation_logs`、`system_configs`、`roles`。 |
| 迁移 | `backend/migrations/` 有外部板块热度、信号缓存、板块信号 V4 相关 SQL。 |

### 客户端模块现状

| 模块 | 当前状态 |
|------|----------|
| Electron 主进程 | 管理窗口、设备 ID、自动更新、本地数据库清理、IPC。 |
| 预加载脚本 | 通过 `contextBridge` 暴露安全 API，包括更新、缓存、设备 ID、窗口控制。 |
| 本地缓存 | `electron/database.js` 使用 sql.js 写入 `cache.db`，包含 API 缓存、股票信息、行业列表、同步状态、设备信息。 |
| React 主应用 | `src/App.js` 根据 `activeModule` 切换热点、查询、行业、板块、策略、系统管理等页面。 |
| API 层 | `src/services/api.js` 包装 axios 风格接口，实际走 `secureApi` 加密通道。 |
| 认证层 | `authService` 直连 `/api/auth/login|register|refresh|logout`，登录后解密并保存会话密钥。 |
| 功能模块 | `components/modules/` 约 36 个 JS 文件，覆盖热点、股票查询、行业趋势、行业加权、板块趋势、排名跳变、稳步上升、单针下二十、外部板块等。 |
| 管理页面 | `pages/` 约 13 个页面，包括用户、角色、会话、日志、系统配置、外部板块同步和热度。 |

### 路由覆盖面

后端路由覆盖的主要 API 前缀包括：

- `/api/dates`
- `/api/analyze/{period}`
- `/api/stock/*`
- `/api/industry/*`
- `/api/sectors/*`
- `/api/rank-jump`
- `/api/steady-rise`
- `/api/strategies/needle-under-20`
- `/api/board-heat/*`
- `/api/cache/*`
- `/api/auth/*`
- `/api/secure`
- `/api/sync/*`
- `/api/admin/*`

客户端已调用的主要 API 前缀与上述基本一致。

### 测试与验证面

发现的测试文件包括：

- `backend/tests/test_caching.py`
- `backend/tests/test_signal_calculator.py`
- `backend/tests/test_industry_detail.py`
- `backend/tests/test_industry_detail_phase34.py`
- `backend/tests/test_user_mgmt.py`
- `backend/tests/test_api_integration.py`
- 若干 `backend/test_*.py` 和 `backend/scripts/test_*.py` 探针脚本。

本次未执行测试，原因：

1. 多数后端测试或探针可能依赖本地/远程 PostgreSQL、真实数据文件或运行中的服务。
2. 当前任务目标是项目现状探查和 RES 固化，不是回归验证或修复。
3. 工作区已有用户改动，避免因测试生成缓存、日志或状态文件造成额外扰动。

---

## 主要发现

### 1. 项目版本标识存在分裂

观察到至少三处版本口径：

- `frontend-client/package.json`: `0.6.2`
- `backend/app/config.py`: `0.4.9`
- 根 README 中仍提到 `v0.5.0`

影响：发布、自动更新、接口兼容和文档追溯会出现口径不一。

### 2. 安全默认值需要收敛

后端存在开发兜底值：

- JWT 默认 secret。
- 主加密密钥未设置时使用开发默认密钥。
- CORS 配置中包含 `*`。

影响：如果生产环境未显式覆盖环境变量，安全边界会被削弱。

### 3. Docker 环境变量与应用读取名不一致

`docker-compose.yml` 给后端传递的是 `DATABASE_HOST`、`DATABASE_NAME`、`DATABASE_PASSWORD` 等；`database.py.example` 读取的是 `DB_HOST`、`DB_NAME`、`DB_PASSWORD`。

影响：容器环境中应用可能没有读取到 Compose 提供的数据库配置，转而使用默认值。

### 4. 客户端仍有旧直连 API 代码残留

大多数业务请求已走 `apiClient` 加密通道，但 `frontend-client/src/components/modules/SectorModule.js` 仍直接使用 `fetch('/api/sectors/...')`。

影响：在 `FORCE_SECURE_API=true` 时，该模块直接访问 `/api/*` 会被后端拒绝。虽然 `components/modules/index.js` 标注该模块已整合到 `SectorTrendModule`、保留用于兼容，但只要被重新挂载就会触发问题。

### 5. 生产服务器地址硬编码在客户端配置中

`frontend-client/src/constants/config.js` 写死了本地地址和远程服务器地址，并通过 `localStorage` 选择。

影响：发布到不同服务器、切换域名、HTTPS 化或灰度环境时需要改代码或依赖本地存储覆盖。

### 6. frontend-client 目录包含生成物和依赖目录

当前目录中存在：

- `node_modules/`
- `build/`
- `dist/`
- 多个构建日志文件。

影响：本地体积大，扫描噪音高；若忽略规则不严，容易污染提交或误判差异。

### 7. 启动路径强依赖数据库和数据导入

`lifespan` 启动阶段会执行数据导入、一致性检查、Numpy 缓存加载。数据库连接失败或数据为空时应用会启动失败。

影响：本地开发、测试、API 文档查看和轻量调试成本较高；缺少明确的“无数据/跳过导入”开发模式开关。

### 8. 文档历史与代码现状仍未完全对齐

旧 `docs/` 已按 DEC-001 标记封存，但代码中的版本、部署脚本、README 描述和 Electron 客户端现状仍存在历史口径。

影响：后续维护者容易按照旧 Web 版或旧版本文档操作。

---

## 是否满足验收

- [x] 已重点探查 `backend/`。
- [x] 已重点探查 `frontend-client/`。
- [x] 已识别后端启动链路、路由面、服务层、缓存、安全和数据导入现状。
- [x] 已识别客户端 Electron 主进程、React 模块、API 层、本地缓存和管理页面现状。
- [x] 已记录主要风险和后续建议。
- [x] 未扰动业务代码。

**结论**：是。本次现状探查满足“记录当前项目状态”的目标，可作为后续 PRB/SUG/DEC 的基线材料。

---

## 遗留风险 / 后续行动

建议后续按 PSDR 流程分别拆成 PRB：

1. 新建 `PRB`: 版本号和发布口径分裂。
2. 新建 `PRB`: 生产安全默认值与密钥配置治理。
3. 新建 `PRB`: Docker Compose 环境变量与应用配置不一致。
4. 新建 `PRB`: 客户端旧直连 API 残留与加密网关强制策略冲突。
5. 新建 `PRB`: 客户端服务器地址硬编码与多环境发布问题。
6. 新建 `PRB`: 后端启动强依赖数据库/数据导入导致开发测试不便。
7. 新建 `SUG`: 为 `frontend-client` 和 `backend` 制定统一启动、测试、发布检查清单。

本 RES 不直接修复上述问题，只作为项目现状基线与后续治理入口。
