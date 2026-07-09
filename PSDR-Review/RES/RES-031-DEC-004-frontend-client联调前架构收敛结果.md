# RES-031: DEC-004 frontend-client 联调前架构收敛结果

**日期**: 2026-07-09
**状态**: [PARTIAL / READY-FOR-INTEGRATION]
**类型**: Infra / Frontend / Architecture / Refactor / Testing
**层级**: Frontend
**关联**: DEC-004, SUG-005, PRB-002, SUG-002, SUG-004, RES-030

---

## 结果摘要

在 RES-030 的应用骨架基础上，本次继续完成了不依赖后端运行即可安全落地的前端架构收敛：

1. 将侧边栏导航元数据抽到 `src/app/navigationConfig.js`。
2. 建立 `src/features/analysis` 查询样板。
3. 将可用日期与最新热点主分析请求迁移到 TanStack Query。
4. 建立 `src/shared/api/secureClient.js` 作为后续 feature API 入口。
5. 建立 `src/shared/electron/electronBridge.js`，并先收口登录/认证链路里的 Electron 直连访问。

当前已经到达一个明确的联调前状态：前端可以编译、登录页可渲染、Web 环境无 Electron API 时不崩；下一步若继续确认登录后全路由、加密网关、分析数据和管理页面行为，需要后端服务、测试账号、数据样本与接口契约一起跑。

---

## 已完成改动

### 1. 导航配置收敛

新增：

```text
frontend-client/src/app/navigationConfig.js
```

完成：

1. 查询系统、行业趋势、策略入口、系统管理菜单改为配置驱动。
2. `Sidebar.js` 不再直接维护大部分菜单 id、label、icon 与 admin 分组结构。
3. 保留各模块筛选控件在 `Sidebar.js`，避免把局部 UI state 过早抽象成复杂配置。

### 2. Query 样板落地

新增：

```text
frontend-client/src/features/analysis/api/queries.js
frontend-client/src/features/analysis/index.js
frontend-client/src/shared/api/secureClient.js
```

完成：

1. `useAvailableDatesQuery` 接管 `/api/dates`。
2. `usePeriodAnalysisQuery` 接管 `/api/analyze/{period}`。
3. Query key 以 `['analysis', ...]` 为根，符合 DEC-004 约定。
4. `useAppState` 不再手写日期请求状态。
5. `HotSpotsModule` 不再手写主分析请求 loading/error/data。

### 3. 热点模块整理

完成：

1. `HotSpotsModule` 主数据请求迁移到 `usePeriodAnalysisQuery`。
2. 删除未被页面使用的 `top1000Industry` 请求与状态。
3. 移除该模块中未使用的 `apiClient`、`API_BASE_URL`、`TrendingUp`、`Calendar` import。

### 4. Electron 边界收敛

新增：

```text
frontend-client/src/shared/electron/electronBridge.js
```

完成：

1. `LoginPage` 通过 `electronBridge` 检测 Electron 环境与读取版本。
2. `authService` 通过 `electronBridge` 获取设备 ID 与平台名。
3. Web 环境下 `window.electronAPI` 不存在时保持安全降级。

---

## 验证

构建命令：

```powershell
$env:NVM_HOME='D:\ProgramLanguage\env\nvm'
$env:NVM_SYMLINK='D:\ProgramLanguage\env\nodejs'
$env:Path="$env:NVM_HOME;$env:NVM_SYMLINK;" + [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
$env:BUILD_PATH='build-verify'
& 'D:\ProgramLanguage\env\nodejs\npm.cmd' run build
```

结果：

```text
Compiled with warnings.
build exited 0
```

浏览器验证：

```text
http://localhost:3000/
登录页正常渲染
Web 模式 hasElectronAPI=false
控制台 error=[]
```

已清理临时 `build-verify` 目录。

---

## 剩余警告

当前 build warning 仍存在，但均不阻断：

1. 多个旧文件带 BOM。
2. 若干旧组件未使用 import。
3. 若干旧组件存在 `react-hooks/exhaustive-deps` 提示。

本次已消除：

1. `Sidebar.js` 的未使用图标 import warning。
2. `HotSpotsModule.js` 的未使用 `API_BASE_URL`、`TrendingUp`、`Calendar`、`top1000Industry` warning。
3. `useAppState.js` 的未使用 `setLoading` warning。

---

## 联调前状态

前端现在已经具备：

1. 路由入口与模块注册表。
2. 配置驱动导航样板。
3. TanStack Query Provider 与 analysis feature query 样板。
4. shared API client 入口。
5. Electron bridge 入口。
6. 登录页 Web 模式降级验证。

下一步需要后端联调才能确认：

1. secure-login / secure-refresh 与后端最新实现是否完全匹配。
2. 登录后 `/api/dates`、`/api/analyze/{period}` 经 `/api/secure` 的响应结构是否与 Query 迁移后的页面兼容。
3. `HotSpotsModule` 切换日期、周期、板块类型、topN、刷新时的缓存失效与 loading 体验。
4. 管理员路由、权限菜单、系统管理页面在真实角色下是否完整可达。
5. Electron packaged 环境下 `electronBridge`、设备 ID、版本读取是否正常。

---

## 结论

本次已经把前端从“可继续静态重构”推进到“需要带后端和账号跑真实工作流”的阶段。后续再继续迁移更多页面到 Query hooks，建议和后端联调一起做：每迁一个 feature，就同时验证接口契约、错误语义、权限行为和缓存失效策略。
