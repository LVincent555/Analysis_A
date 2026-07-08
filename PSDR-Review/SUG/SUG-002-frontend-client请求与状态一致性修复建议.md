# SUG-002: frontend-client 请求与状态一致性修复建议

**日期**: 2026-07-08
**状态**: [OPEN]
**类型**: Infra / Frontend / API / UX / Refactor
**层级**: Frontend-client
**关联**: PRB-002, RES-002

---

## 选项 A：最小风险修复

- **做法**：
  - 将 `OperationLogs.js` 的导出地址改为使用统一 `API_BASE_URL`，并明确带上当前 token。
  - 如后端导出接口仍不支持 secure 网关，先保留直连下载，但修正 hardcoded localhost 和认证头缺失问题。
  - 用 `AbortController` 改造 `LoginPage.js` 的服务器状态检查，替代无效的 `timeout` 字段。
  - 移除 `secureApi.js` 中的 `alert()`，只派发 `session-expired`，由 `SessionExpiredDialog` 统一提示。
  - 为 `IndustryDetailPage.js` 趋势/对比数据加载补齐 `selectedDate` 依赖，并在切日期时清理旧 tab 数据或显示 loading。
- **收益**：
  - 改动集中在少数文件，适合快速修复用户可见问题。
  - 解决日志导出地址错误、登录页检测挂起、会话过期双提示、日期切换旧数据等明确缺陷。
  - 不要求立即重构 secure 网关或 Electron 架构。
- **风险**：
  - CSV 导出如果仍走直连接口，在 `FORCE_SECURE_API=true` 下可能还需要后端配合。
  - 启动期 token 校验仍未完整解决，过期 token 闪进主界面的体验可能继续存在。
- **验证**：
  - 运行前端 production build。
  - 手动验证本地/远程服务器切换后，日志导出不再指向错误地址。
  - 手动验证登录页服务器检测 5 秒左右可以进入 offline 状态。
  - 手动验证 token 过期后只出现一次会话过期弹窗。
  - 手动验证详情页切换日期后趋势/对比请求重新发出。

## 选项 B：请求层一致性整理

- **做法**：
  - 为所有业务页面建立“禁止直接 fetch/axios/window.open 调业务 API”的规则，例外仅限 auth、更新检查和明确的文件下载流程。
  - 将 `apiClient.post()`、`apiClient.put()` 的 URL query 解析行为与 `get()` 对齐，避免静默丢 query。
  - 为文件下载增加统一封装，例如 `downloadApi`，集中处理 base URL、认证头、文件名、错误提示和 secure/non-secure 差异。
  - 清理或隔离废弃模块 `SectorModule`，避免未来从 `index.js` 误挂载旧直连实现。
  - 整理 unused import 和 BOM，降低构建 warning 噪音。
- **收益**：
  - 统一前端请求边界，后续维护成本更低。
  - 可以把 CSV、未来报表下载、普通 JSON API 区分清楚。
  - 减少旧代码被误用的概率。
- **风险**：
  - 涉及调用面更广，容易与既有未提交改动混在一起。
  - 文件下载是否走 secure 网关需要和后端能力对齐。
- **验证**：
  - `rg "fetch\\(|axios\\.|window.open\\(" frontend-client/src` 只保留允许的白名单。
  - 运行前端 production build。
  - 覆盖 GET、POST with params、POST URL query、文件下载四类调用。

## 选项 C：登录态恢复完整化

- **做法**：
  - App 启动时增加静默 session 校验：优先尝试 refresh，失败则清本地认证信息并显示登录页。
  - `authService.refreshAccessToken()` 成功后补充更新 token 相关元信息，必要时同步用户信息。
  - 对启动期加载状态做明确 UX：校验中显示 loading，避免先进入主界面再被踢出。
  - 如果后端已支持会话撤销和 token_version，再把前端启动校验与后端会话状态打通。
- **收益**：
  - 改善过期 token 闪进主界面的体验。
  - 为后续多设备会话、管理员强制下线提供更一致的客户端行为。
- **风险**：
  - 依赖后端认证会话链路的实际能力；如果后端撤销语义不完整，前端只能改善体验，不能单独保证会话正确性。
  - 启动期会多一次网络请求，离线场景需要明确策略。
- **验证**：
  - 过期 access token + 有效 refresh token：启动后自动恢复。
  - 过期 access token + 无效 refresh token：启动后进入登录页。
  - 离线启动：行为符合预期提示，不误报为账号错误。

## 选项 D：暂不处理

- **做法**：维持现状，仅保留 PRB-002 记录。
- **收益**：无额外开发成本。
- **风险**：
  - 远程打包和强制 secure 场景下，日志导出和旧直连模块继续存在不确定性。
  - 日期切换旧数据问题可能影响分析判断。
  - 会话过期双提示继续影响使用体验。
- **验证**：N/A

---

## 推荐

推荐分两步执行：

1. 先采用选项 A，作为小范围 bugfix，优先修复日志导出、登录页超时、会话过期提示和日期切换旧数据。
2. 再采用选项 B，作为一次请求层整理，统一业务 API、下载 API 和旧模块边界。

选项 C 建议与后端认证会话后续修复并行评估，不必阻塞选项 A。

**理由**：

当前项目是个人项目，不需要一次性做成完整企业级前端治理。但这些问题已经接近真实使用路径，尤其是日志导出、日期切换旧数据和会话过期提示，适合先做小补丁。请求层整理可以随后慢慢收敛，避免一次改动过大。

---

## 前置条件 / 依赖

1. 明确操作日志 CSV 导出是否允许继续走非 secure 直连接口；如果不允许，需要后端提供 secure 下载能力或短期下载 token。
2. 明确是否保留 `SectorModule`。若仅为历史兼容，可在索引导出中移除或增加废弃注释。
3. 修复前保留当前未提交文档和后端改动状态，避免把前端 bugfix 与既有变更混到同一提交。
4. 如要完整处理启动期认证校验，需要先确认后端 refresh、logout、session revoke 的实际语义。
