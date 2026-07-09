# RES-030: DEC-004 frontend-client 架构骨架落地结果

**日期**: 2026-07-09
**状态**: [PARTIAL]
**类型**: Infra / Frontend / Architecture / Refactor / Testing
**层级**: Frontend
**关联**: DEC-004, SUG-005, PRB-002, SUG-002, SUG-004, RES-001, RES-002, RES-013

---

## 结果摘要

本次按 DEC-004 完成 frontend-client 架构现代化的首轮落地：保留 Electron + React SPA 路线，在 CRA 现状下先引入应用壳层、HashRouter、模块注册表和 TanStack Query Provider，为后续按 feature/domain 拆分业务模块建立入口。

当前不是一次性重写所有页面，而是先把原 `App.js` 中的导航、布局、模块 switch 分发和认证职责拆开，降低继续改造时的冲突面。

---

## 已完成改动

1. 新增应用层入口：
   - `frontend-client/src/app/providers.jsx`
   - `frontend-client/src/app/router.jsx`
   - `frontend-client/src/app/moduleRegistry.jsx`
   - `frontend-client/src/app/AppShell.jsx`

2. 新增共享 API 基础入口：
   - `frontend-client/src/shared/api/queryClient.js`

3. `frontend-client/src/index.js` 增加 `AppProviders`，统一挂载 `QueryClientProvider` 和 `HashRouter`。

4. `frontend-client/src/App.js` 收敛为认证生命周期组件：
   - 启动时恢复登录态与会话密钥。
   - 登录成功后进入 `AppShell`。
   - 统一处理登出、会话过期弹窗和加密器重置。

5. `moduleRegistry.jsx` 接管主功能模块定义：
   - 模块 id、path、label、icon、group 和 render 入口集中维护。
   - 支持 `/` 与 `/hot-spots` alias。
   - 保留 `ExtBoardHeat -> BoardAnalysisPage` 的局部页面流。

6. `router.jsx` 接管登录后的路由表：
   - 由 `moduleRegistry.jsx` 生成 `<Route>`。
   - alias 与 fallback redirect 集中在路由层处理。

7. `AppShell.jsx` 接管登录后的主布局：
   - Header / Drawer / Sidebar / ContentArea 统一装配。
   - 使用 React Router path 映射 active module。
   - 继续保留行业详情页的全屏返回流。

8. `Sidebar.js` 初步接入模块注册常量：
   - 查询、行业、系统管理分组的 active 判断改为引用注册表导出的 id 列表。
   - 暂未一次性改成完全配置驱动，避免在首轮重构中扩大风险。

9. 新增依赖：
   - `react-router-dom`
   - `@tanstack/react-query`

---

## 验证

使用 nvm 管理的 Node 环境执行：

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

1. `http://localhost:3000/` 可打开。
2. 登录页正常渲染。
3. 浏览器控制台未发现 React runtime error。

已知验证边界：

1. 本地后端 `localhost:8000` 未运行，因此本次没有验证真实登录后的业务接口请求。
2. 未使用真实账号验证登录后所有路由点击流。
3. 构建警告主要来自既有代码：BOM、未使用 import、Hook dependency 提示等，本次未顺手清理。

---

## 当前架构状态

新的前端顶层结构已经形成：

```text
src/
├── app/
│   ├── AppShell.jsx
│   ├── moduleRegistry.jsx
│   ├── providers.jsx
│   └── router.jsx
├── components/
├── contexts/
├── hooks/
├── pages/
├── services/
├── shared/
│   └── api/
│       └── queryClient.js
├── App.js
└── index.js
```

职责边界：

1. `index.js`: 只负责 React root 与全局 provider。
2. `App.js`: 只负责认证生命周期和登录态切换。
3. `AppShell.jsx`: 只负责登录后的主框架、导航和路由容器。
4. `router.jsx`: 只负责由模块注册表生成路由。
5. `moduleRegistry.jsx`: 只负责模块元数据和模块渲染映射。
6. `shared/api/queryClient.js`: 统一定义 TanStack Query 默认策略。
7. `Sidebar.js`: 暂为旧 UI 实现，逐步向配置驱动收敛。

---

## 遗留风险

1. Sidebar 仍是大组件，菜单结构和筛选控件还没有完全抽象。
2. 业务数据请求仍主要散落在组件内部，TanStack Query 只是先完成 Provider 落位。
3. `useAppState` 仍承担较多跨模块状态，后续应迁到 feature-local hooks 或 query/mutation hooks。
4. CRA 仍是当前构建工具，Vite / electron-vite 迁移尚未开始。
5. React Router 7 要求 Node >= 20，当前本机通过 `D:\ProgramLanguage\env\nvm` 的 Node v24 满足要求。
6. 构建警告数量较多，会掩盖后续新增 warning，应单独安排一次 lint 清理。

---

## 下一步建议

1. 将 Sidebar 的菜单项、分组、权限和 route 映射进一步改为配置驱动。
2. 按 `features/*` 拆第一批低风险页面，例如 `board-heat`、`admin`、`query`。
3. 以 `dates`、`hot-spots` 为样板建立 TanStack Query API hooks。
4. 给 module registry 增加最小单元测试，确保 id/path/alias 不漂移。
5. 等后端安全网关与接口契约稳定后，再迁移到 Vite 或 electron-vite。

---

## 结论

DEC-004 已进入实现阶段，首轮完成的是 Level 0 到 Level 1 的应用骨架重构。后续前端新增页面、路由和模块入口应优先进入 `src/app/moduleRegistry.jsx` 与对应 feature 目录，不再继续把主业务分发逻辑塞回 `App.js`。
