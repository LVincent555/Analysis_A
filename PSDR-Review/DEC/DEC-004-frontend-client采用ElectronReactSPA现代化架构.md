# DEC-004: frontend-client 采用 Electron + React SPA 现代化架构

**日期**: 2026-07-09
**状态**: [ACTIVE]
**类型**: Infra / Frontend / Architecture / Refactor / Governance
**层级**: frontend-client
**关联**: SUG-005, SUG-002, SUG-004, PRB-002, DEC-002, RES-001, RES-002, RES-013

---

## 决策

采用 `SUG-005` 的 **选项 B：Electron + React SPA 现代化重构**。

`frontend-client` 后续架构默认遵循：

```text
Electron 桌面客户端
+ React SPA
+ React Router
+ TanStack Query
+ feature/domain 分层
+ shared API / Electron bridge 边界
+ 后续从 CRA 迁移到 Vite 或 electron-vite
```

不采用 Next.js / Remix 等 Web 全栈 SSR 框架作为当前前端主线。

---

## 架构定位

`frontend-client` 的定位是桌面客户端，而不是公网 Web 站点。

核心边界：

1. **后端**：FastAPI 提供业务 API、认证、secure gateway、数据分析和管理能力。
2. **Electron main/preload**：提供桌面能力、设备 ID、本地缓存、自动更新、未来安全存储。
3. **React renderer**：提供 UI、路由、业务交互、数据展示和用户工作流。
4. **API client 层**：隔离 auth、secure business API、下载、Electron IPC 和后续安全存储。

---

## 约定

### 1. 路由约定

1. 新页面不再直接新增 `activeModule` 分支作为长期方案。
2. 页面注册必须进入统一 `moduleRegistry` 或 router 配置。
3. 菜单、权限、路由路径、页面组件、图标和分组应由同一份配置驱动。
4. Electron production 优先采用 HashRouter；若使用 BrowserRouter，必须验证 `file://` 或 packaged build 下刷新和深链行为。

### 2. 数据请求约定

1. 业务 JSON API 必须通过统一 secure API client。
2. 登录/刷新必须保留 `SUG-004` 的 secure-login / secure-refresh 优先策略。
3. 文件下载必须通过统一 download client，不在页面中直接 `window.open` 业务下载地址。
4. 页面组件不直接调用 `axios` 或原生 `fetch` 访问业务 API。例外必须写在对应 SUG/DEC/RES 中。
5. POST/PUT 参数必须通过统一 client 处理，不允许依赖 URL query 静默拼接行为。

### 3. Server State 约定

1. 远端数据、loading、error、缓存、刷新和失效由 TanStack Query 管理。
2. Query key 以 feature 为根，例如：

```text
['analysis', 'hotSpots', params]
['marketData', 'stock', stockCode, selectedDate]
['identity', 'users', filters]
['operations', 'logs', filters]
```

3. 页面内 `useState` 只保存 UI state，例如筛选控件临时值、tab、弹窗开关、表格本地排序选择。
4. mutation 成功后必须明确 invalidate 或 update 对应 query。

### 4. Client State 约定

1. 小范围 UI 状态继续使用 React state。
2. 跨页面但非远端数据的状态可使用 Context 或轻量 Zustand。
3. 不引入 Redux 作为默认全局状态方案，除非后续出现复杂可回放状态、跨模块事务或大型协作状态需求，并单独写 DEC。

### 5. 目录约定

后续目标目录为：

```text
src/
├── app/
├── shared/
├── features/
└── widgets/
```

规则：

1. `app/`：应用装配、router、providers、AppShell。
2. `shared/`：跨 feature 的 API client、UI 原语、charts、Electron bridge、通用 lib。
3. `features/`：业务域内页面、组件、query hooks、转换逻辑。
4. `widgets/`：跨 feature 的组合视图和布局块。

feature 命名优先与后端上下文对齐：

1. `auth`
2. `identity`
3. `operations`
4. `analysis`
5. `marketData`
6. `boardHeat`
7. `settings`

### 6. 大页面拆分约定

单个页面文件原则上不应继续增长。

拆分优先级：

1. `IndustryDetailPage.js`
2. `UserManagement.js`
3. `SectorTrendModule.js`
4. `ExtBoardSync.js`
5. `HotSpotsModule.js`
6. `NeedleUnder20Module.js`

拆分后结构建议：

```text
features/industry/
├── pages/
├── panels/
├── components/
├── api/
├── model/
└── index.js
```

### 7. Electron 边界约定

1. React renderer 不直接假设 Electron API 一定存在。
2. `window.electronAPI` 访问必须通过 `shared/electron/electronBridge.js` 统一封装。
3. 自动更新、本地缓存、设备 ID、未来安全存储均归 Electron bridge 管理。
4. token / refresh token / session key 短期保留 localStorage 兼容；长期迁移到 Electron main process 安全存储需独立 SUG/DEC/RES。

### 8. 构建工具约定

1. 当前继续允许 CRA 构建。
2. 架构迁移稳定后，迁移到 Vite 或 electron-vite。
3. 迁移构建工具不得与页面大拆分混在同一阶段。
4. 迁移必须验证：
   - `npm.cmd run build`
   - Electron dev 启动
   - Electron packaged build
   - 静态资源路径
   - 环境变量
   - auto update

### 9. 文档与决策约定

1. 新增全局框架、路由、状态管理、构建工具、Electron 安全存储等跨切面变化，必须先写 SUG，再写 DEC。
2. 单个 feature 内部拆分，如果不改变全局约定，可只写 RES。
3. 每个阶段结束必须写 RES，记录：
   - 修改范围
   - 构建结果
   - 手动验证路径
   - 遗留风险
4. 与后端 API contract 相关的前端改动必须引用对应后端 RES 或 DEC。

---

## 范围

**做**：

- 建立前端架构长期约定。
- 分阶段引入 module registry、React Router、TanStack Query、feature 分层。
- 为 CRA -> Vite/electron-vite 迁移预留路线。
- 继续保留并保护 secure-login / secureApi / Electron 更新等现有关键链路。

**不做**：

- 不在本 DEC 中立即执行代码重构。
- 不将项目迁移为 Next.js / Remix。
- 不同时重做 UI 视觉设计。
- 不在本 DEC 中完成 Electron main process 安全存储迁移。
- 不要求一次性拆完所有历史大页面。

---

## 迁移阶段

### Level 0：前端基线

1. 固定 Node / npm 环境。
2. 明确 build 命令和现有 warning 基线。
3. 不混入历史 warning 清理。

### Level 1：module registry

1. 抽出模块注册表。
2. `App.js` 和 `Sidebar.js` 共享模块定义。
3. 保留现有页面行为。

### Level 2：React Router

1. 引入正式路由。
2. 将 `activeModule` 逐步迁移为 URL。
3. 详情页和管理页使用 route params / nested routes。

### Level 3：TanStack Query

1. 建立 query client 和 feature query hooks。
2. 先迁移高频查询页面，再迁移管理类页面。
3. 页面不再手写远端数据 loading/error/cache。

### Level 4：feature 拆分

1. 按后端上下文映射前端 feature。
2. 拆分大页面。
3. 清理旧 hooks/services 的半使用状态。

### Level 5：Vite / electron-vite

1. 独立迁移构建工具。
2. 完成 Electron dev/prod/build 验证。

### Level 6：Electron 安全存储

1. token / refresh token / session key 迁到 main process。
2. renderer 只通过 bridge 请求能力。

---

## 负责人 / 截止时间

- **负责人**：项目维护者 / Codex 协作执行
- **截止时间**：TBD，按阶段 RES 收口

---

## 验收标准

本 DEC 生效的验收标准：

1. `SUG-005` 与本 `DEC-004` 已创建并进入 `PSDR-Review/META/INDEX.md`。
2. 后续前端全局架构修改均引用本 DEC。
3. 任一阶段执行完成后写对应 RES。

阶段性工程验收标准：

1. 前端 production build 通过。
2. Electron dev/prod 路径不破坏。
3. secure-login / secure-refresh / secureApi 不回退。
4. 新增页面不再绕过统一 API client。
5. 路由、菜单、权限和页面注册不再多处硬编码。
6. 已迁移 feature 的 server state 由 TanStack Query 管理。

---

## 参考

1. React 官方新项目建议：https://react.dev/learn/start-a-new-react-project
2. Vite 官方指南：https://vite.dev/guide/
3. React Router 官方文档：https://reactrouter.com/
4. TanStack Query React 文档：https://tanstack.com/query/latest/docs/framework/react/overview
