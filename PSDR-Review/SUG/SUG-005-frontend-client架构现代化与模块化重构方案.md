# SUG-005: frontend-client 架构现代化与模块化重构方案

**日期**: 2026-07-09
**状态**: [ACCEPTED]
**类型**: Infra / Frontend / Architecture / Refactor
**层级**: frontend-client
**关联**: PRB-002, SUG-002, SUG-004, DEC-004, RES-001, RES-002, RES-013

---

## 背景

`frontend-client` 当前已经从早期 React 页面逐步演进为 Electron 桌面客户端，承担了：

1. 登录认证、secure-login 信封加密、`/api/secure` 业务加密通道。
2. A 股分析、热点榜、行业/板块趋势、策略筛选、外部板块热度。
3. 管理后台、用户/角色/会话/日志/配置管理。
4. Electron 更新、本地 SQLite 缓存、设备 ID 与桌面运行能力。

现状可运行，但页面架构已经出现“大文件、手写路由、页面内自管请求状态、模块边界不清”的维护压力。

主要观察：

1. `src/App.js` 使用 `activeModule` + `switch` 手写页面路由。
2. `src/components/layout/Sidebar.js` 同时承担导航结构、权限显示、模块切换和大量 UI 细节，和 `App.js` 存在模块 ID 重复维护。
3. 多个页面/模块超过 20KB，最大页面 `IndustryDetailPage.js` 超过 57KB。
4. server state 主要由 `useEffect + useState` 管理，容易出现依赖遗漏、旧数据、重复请求和缓存策略分散。
5. `services/`、`hooks/`、`components/stock|industry|hotspots` 已有模块化雏形，但没有形成统一架构规则。
6. Electron main/preload、认证、业务 API、下载、缓存、页面 UI 的边界仍需要收敛。

---

## 目标

本 SUG 的目标不是一次性重写前端，而是给后续大改建立可执行的架构路线：

1. 保持 Electron 桌面客户端定位。
2. 让页面导航、数据请求、业务模块和共享组件有稳定边界。
3. 降低页面文件体积和单页复杂度。
4. 将请求状态、缓存、刷新、错误处理从页面组件中抽离。
5. 让后续安全存储、下载、更新、API 合约变化有明确适配层。

---

## 选项 A：保守整理现有 CRA + 手写路由

- **做法**：
  - 保留 Create React App。
  - 保留 `activeModule` 模型，但抽出 `moduleRegistry`，让 `App.js` 和 `Sidebar.js` 共用模块配置。
  - 分批拆大页面，将 API 请求搬到 `services/` 或 feature hooks。
  - 不引入新路由和 server state 库。
- **收益**：
  - 变更最小，短期风险最低。
  - 不影响 Electron 打包链路。
  - 适合只想缓解 `App.js`/`Sidebar.js` 重复维护的问题。
- **风险**：
  - 手写路由和页面状态管理的根问题仍在。
  - server state 仍靠每页自己处理，后续数据刷新、缓存和错误边界继续分散。
  - 大改时会不断补局部抽象，容易再次长成“半模块化”。
- **验证**：
  - 前端 production build 通过。
  - `App.js` 不再出现大型 `switch(activeModule)`。
  - `Sidebar.js` 不再硬编码全部页面结构。

## 选项 B：Electron + React SPA 现代化重构

- **做法**：
  - 保持 Electron + React SPA，不改为 Web SSR/全栈框架。
  - 构建工具从 CRA 迁移到 Vite 或 electron-vite。
  - 引入 React Router，使用 HashRouter 或 Electron 友好的路由策略替代 `activeModule`。
  - 引入 TanStack Query 管理 server state、缓存、刷新、错误和 loading。
  - UI/client state 使用 Context 或轻量 Zustand；仅保存导航、筛选、弹窗、局部偏好，不管理远端数据。
  - 按业务域拆成 `features/*`，共享能力放入 `shared/*`，布局和组合视图放入 `widgets/*`。
  - 建立统一 API 边界：`authClient`、`secureClient`、`downloadClient`、`electronBridge`。
- **收益**：
  - 保持桌面客户端定位，符合当前 FastAPI + Electron 架构。
  - 路由、菜单、权限、页面注册可由同一配置驱动。
  - server state 从页面组件中抽离，减少 Hook dependency 与旧数据问题。
  - 架构与后端模块化迁移方向相匹配，便于按 Identity / Operations / Analysis / MarketData / BoardHeat 映射 feature。
  - Vite/electron-vite 能改善开发启动和构建体验。
- **风险**：
  - 改动面较大，需要分阶段迁移。
  - React Router 与现有 `activeModule` 状态需要兼容过渡。
  - TanStack Query 引入后，需要统一 query key、缓存失效和错误处理规范。
  - CRA -> Vite/electron-vite 迁移要核对 Electron builder、静态资源路径、环境变量前缀和 preload 访问方式。
- **验证**：
  - 所有现有页面可从路由访问。
  - Electron 开发模式和 production build 均可启动。
  - 关键业务模块完成 query hook 迁移后，不再在页面中直接写 API 请求。
  - CSV 下载、secure-login、secureApi、自动更新路径不回退。

## 选项 C：迁移到 Next.js / Remix 等 Web 全栈框架

- **做法**：
  - 将前端整体迁移到带 SSR/data loading 能力的 Web 全栈框架。
  - Electron 只作为包装外壳，加载框架构建产物或本地服务。
- **收益**：
  - 框架约束强，路由、代码分割、数据加载有成熟约定。
  - 如果后续要公网 Web 化，可能更方便。
- **风险**：
  - 当前项目核心是 Electron 桌面客户端 + FastAPI 后端，不需要 SSR。
  - 引入 Web server/SSR 概念会增加桌面打包复杂度。
  - 与现有 `/api/secure`、Electron preload、本地 SQLite 缓存、自动更新链路不天然贴合。
  - 大量迁移成本没有直接业务收益。
- **验证**：
  - Electron 离线加载、更新、API base URL、静态资源路径均需重测。

## 选项 D：暂不重构

- **做法**：维持现状，只在遇到 bug 时局部修补。
- **收益**：
  - 无短期迁移成本。
  - 不打断后端架构迁移节奏。
- **风险**：
  - 大页面继续膨胀。
  - 手写路由、手写请求状态和旧直连 API 问题会继续累积。
  - 后续接入更多后端模块和安全存储时，前端会成为新的瓶颈。
- **验证**：N/A

---

## 推荐

推荐采用 **选项 B：Electron + React SPA 现代化重构**，并分阶段推进。

**理由**：

1. 当前产品形态是桌面客户端，不适合为 SSR 或公网 Web 化提前付出 Next.js/Remix 复杂度。
2. 真正的问题不是 React 本身，而是缺少正式路由、server state 管理和 feature 边界。
3. React Router + TanStack Query + feature 分层可以解决当前最痛的维护问题，同时保留现有业务代码可渐进迁移。
4. Vite/electron-vite 适合作为 CRA 后继构建工具，但应在路由和模块边界稳定后再迁移，避免一次性变量过多。

---

## 建议目标目录

```text
frontend-client/src/
├── app/
│   ├── App.jsx
│   ├── AppShell.jsx
│   ├── providers.jsx
│   ├── router.jsx
│   └── moduleRegistry.js
├── shared/
│   ├── api/
│   │   ├── secureClient.js
│   │   ├── authClient.js
│   │   ├── downloadClient.js
│   │   └── queryClient.js
│   ├── electron/
│   │   └── electronBridge.js
│   ├── ui/
│   ├── charts/
│   ├── config/
│   └── lib/
├── features/
│   ├── auth/
│   ├── marketData/
│   ├── analysis/
│   ├── boardHeat/
│   ├── operations/
│   ├── identity/
│   └── settings/
└── widgets/
    ├── layout/
    ├── navigation/
    └── dashboard/
```

说明：

1. `app/` 只做应用装配、路由、providers 和壳层。
2. `shared/` 放跨 feature 的技术能力和 UI 原语。
3. `features/` 按后端上下文和业务域组织页面、API hooks、组件和模型。
4. `widgets/` 放跨 feature 的组合型界面，例如主布局、导航、仪表盘区块。

---

## 分阶段计划

### 阶段 0：基线冻结

1. 用 nvm 固定 Node 版本：当前为 `D:\ProgramLanguage\env\nvm` + Node `24.18.0`。
2. 前端 build 使用 `npm.cmd run build` 作为最低验证。
3. 记录现有 ESLint warnings，不在架构迁移中混入无关清理。

### 阶段 1：模块注册表

1. 新增 `app/moduleRegistry.js`。
2. `App.js` 和 `Sidebar.js` 共用同一份模块定义。
3. 消除 `activeModule` switch 与 Sidebar 菜单的重复定义。
4. 仍可暂时保留 `activeModule`，降低第一步风险。

### 阶段 2：正式路由

1. 引入 React Router。
2. Electron production 使用 HashRouter 或经验证可行的 BrowserRouter 静态路径策略。
3. 将 `activeModule` 迁移为 URL route。
4. 详情页、板块分析页、管理页使用路由参数和嵌套路由表达。

### 阶段 3：server state 收敛

1. 引入 TanStack Query。
2. 建立 `shared/api/queryClient.js`。
3. 每个 feature 提供 `queries.js` / `mutations.js` 或 `api/*.js`。
4. 页面不再直接管理远端数据 loading/error/cache。
5. query key 命名按 feature 归属统一。

### 阶段 4：feature 拆分大页面

优先拆：

1. `IndustryDetailPage.js`
2. `UserManagement.js`
3. `SectorTrendModule.js`
4. `ExtBoardSync.js`
5. `HotSpotsModule.js`
6. `NeedleUnder20Module.js`

拆分规则：

1. `Page` 只做布局和状态组合。
2. `panels/` 放 tab 或大区域。
3. `components/` 放纯展示组件。
4. `api/` 放请求和 query hooks。
5. `model/` 放转换、筛选、排序、格式化等纯逻辑。

### 阶段 5：构建工具迁移

1. 从 CRA 迁移到 Vite 或 electron-vite。
2. 校验 Electron dev/prod、静态资源路径、环境变量、auto update、electron-builder。
3. 保留 CRA 迁移前后构建结果对照。

### 阶段 6：Electron 安全存储与本地能力收敛

1. 将 token / refresh token / session key 从 renderer localStorage 迁移到 Electron main process。
2. 优先评估 Electron `safeStorage` 或 OS keychain。
3. renderer 通过 IPC 获取短期调用能力，不直接持有长期敏感 token。

---

## 前置条件 / 依赖

1. 后端 DEC-002 已完成主线收口，前端可按同样的上下文名称映射 feature。
2. SUG-004 的 secure-login 前端实现已存在，架构迁移必须保留该安全登录链路。
3. 迁移期间不应与大规模 UI 视觉重做混在同一批提交。
4. 每个阶段完成后写 RES，记录构建、手动验证和遗留风险。

---

## 参考

1. React 官方新项目建议：https://react.dev/learn/start-a-new-react-project
2. Vite 官方指南：https://vite.dev/guide/
3. React Router 官方文档：https://reactrouter.com/
4. TanStack Query React 文档：https://tanstack.com/query/latest/docs/framework/react/overview
