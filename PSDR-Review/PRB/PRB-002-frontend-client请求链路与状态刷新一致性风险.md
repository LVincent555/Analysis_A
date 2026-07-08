# PRB-002: frontend-client 请求链路与状态刷新一致性风险

**日期**: 2026-07-08
**状态**: [OPEN]
**类型**: Infra / Frontend / API / UX / Audit
**层级**: Frontend-client
**关联**: SUG-002, RES-001, RES-002

---

## 1. 现象

本次只读审查发现，`frontend-client` 的主架构已经形成了统一请求入口，但仍存在少量绕过统一入口、页面状态依赖不完整和用户提示重复的问题。主要事实如下：

1. 主业务请求基本走 `src/services/api.js -> src/services/secureApi.js -> /api/secure`，登录、刷新、登出走 `src/services/authService.js -> /api/auth/*`。
2. `src/pages/OperationLogs.js` 的 CSV 导出仍使用 `window.open()` 直连 `/api/admin/logs/export/csv`，并硬编码 `process.env.REACT_APP_API_URL || 'http://localhost:8000'`，没有使用当前 `API_BASE_URL`、认证 token 或 `/api/secure`。
3. `src/components/modules/SectorModule.js` 仍使用原生 `fetch('/api/sectors/...')`。该模块当前未在 `src/App.js` 主路由中挂载，但仍从 `src/components/modules/index.js` 导出，后续误用时会绕过统一安全网关。
4. `src/pages/LoginPage.js` 的服务器状态检查使用浏览器 `fetch()` 并传入 `timeout: 5000`，但标准 `fetch` 不支持该字段；遇到慢连接或挂起连接时，超时逻辑不会生效。
5. `src/services/secureApi.js` 在 401 refresh 失败后同时执行 `alert()` 和 `window.dispatchEvent(new CustomEvent('session-expired'))`；`src/App.js` 又通过 `SessionExpiredDialog` 处理该事件，用户可能看到重复会话过期提示。
6. `src/App.js` 启动时只根据 `authService.isLoggedIn()` 判断是否进入主界面，实际只检查本地 token 是否存在，未先校验 token 是否过期、被撤销或仍可刷新。
7. `src/pages/IndustryDetailPage.js` 的趋势 tab 请求使用 `selectedDate`，但对应 effect 依赖中缺少 `selectedDate`；用户在趋势页切换日期时，趋势图可能继续显示旧日期数据。
8. `src/pages/IndustryDetailPage.js` 的对比 tab 通过 `loadCompareData()` 间接使用 `selectedDate`，但触发 effect 依赖中也没有覆盖该日期变化，存在同类旧数据风险。
9. `src/services/api.js` 的 `post()`、`put()` 会丢弃 URL 中的 query string，只读取 `config.params`。当前搜索未发现已触发的 POST/PUT URL query 调用，但该行为对后续维护者不直观。
10. 生产构建验证可通过，但 ESLint 报告多处 unused import、BOM、Hook dependency warning，说明代码历史包袱和页面 effect 依赖管理仍需收敛。

## 2. 影响

严重度：中。当前没有发现打包级阻断，但部分问题会在远程服务、强制安全网关、日期切换和会话过期场景下表现为用户可见异常。

可能出现的用户可见问题：

1. 操作日志 CSV 导出在远程服务器、打包客户端或 `FORCE_SECURE_API=true` 场景下失败。
2. 登录页显示的服务器在线/离线状态不可靠，慢连接时可能长时间停留在检测中或积累多个未完成请求。
3. token 失效后，用户可能先看到浏览器 alert，再看到应用内会话过期弹窗。
4. 应用启动时可能短暂进入主界面，随后第一个业务请求失败再回到登录页，表现为“闪进后被踢出”。
5. 板块详情趋势/对比页在切换日期后可能显示旧数据，导致分析判断基于错误日期。
6. 旧 `SectorModule` 如果被重新挂载，可能在 secure 网关强制模式下无法访问后端。
7. 后续开发者如果把 query 写进 POST/PUT URL，参数会被静默丢弃，排查成本较高。

## 3. 初步假设

1. 项目从普通 REST 请求逐步演进到 `/api/secure` 加密网关，部分旧页面或下载场景没有同步迁移。
2. CSV 导出属于非 JSON 响应，当前 secure 网关主要面向 JSON API，导致前端保留了 `window.open` 直连方式。
3. 登录态恢复逻辑为了降低启动成本，只做了本地 token 存在性判断，没有设计启动期静默校验。
4. 页面组件较大，effect 内部函数捕获状态较多，后续新增 `selectedDate` 后没有完整更新依赖。
5. `apiClient` 以 axios 兼容接口为目标，但 POST/PUT 的 query 解析能力没有与 GET 保持一致。
6. Electron 客户端和 Web 开发模式共用一套前端代码，导致部分 API_BASE_URL、更新检查、下载行为存在历史兼容路径。

## 4. 下一步

需要进一步验证：

1. 在远程服务器配置下点击操作日志 CSV 导出，确认是否仍指向 `localhost:8000`。
2. 在 `FORCE_SECURE_API=true` 下验证日志导出是否被后端拦截或因未认证失败。
3. 在登录页模拟后端端口可连接但请求不返回，确认服务器状态检查是否挂起。
4. 使用过期 token 启动客户端，观察是否出现主界面短暂闪现和重复会话提示。
5. 在 `IndustryDetailPage` 趋势 tab 和对比 tab 切换 `selectedDate`，确认请求是否重新发出且数据日期正确。
6. 搜索并约束后续 POST/PUT 调用规范，避免 URL query 被静默丢弃。
7. 确认 `SectorModule` 是否仍有保留价值；若无，应从导出面移除或标记废弃。
