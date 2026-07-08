# RES-002: frontend-client 请求与状态一致性修复结果

**日期**: 2026-07-08
**状态**: [SOLVED]
**类型**: Infra / Frontend / API / UX / Bugfix
**层级**: Frontend-client
**关联**: PRB-002, SUG-002

---

## 执行摘要

本次执行 `SUG-002` 的选项 A：最小风险修复，范围限定在 `frontend-client` 的用户可见问题，不做请求层大重构。

已完成改动：

1. `src/pages/OperationLogs.js`
   - 日志 CSV 导出不再使用 `window.open()` 和 hardcoded `localhost:8000`。
   - 改为使用统一 `API_BASE_URL`、当前登录 token 和 `fetch + Blob` 下载。
   - 导出接口返回 401 时派发 `session-expired` 事件，复用应用内会话过期弹窗。
2. `src/pages/LoginPage.js`
   - 删除无效的 `fetch timeout` 字段。
   - 使用 `AbortController` 实现 5 秒服务器状态检测超时。
   - 组件卸载时中止未完成的检测请求，避免卸载后继续更新状态。
   - 移除未使用的 `SERVERS` import。
3. `src/services/secureApi.js`
   - 移除 401 会话过期路径中的浏览器 `alert()`。
   - 保留 `session-expired` 事件，由 `SessionExpiredDialog` 统一提示，避免双重弹窗。
4. `src/pages/IndustryDetailPage.js`
   - 对比数据加载改为 `useCallback`，依赖 `compareIndustries` 和 `selectedDate`。
   - 趋势 tab effect 补充 `selectedDate` 依赖。
   - 重新加载趋势/对比数据时先清理旧数据，降低切换日期后显示旧结果的风险。

## 结果与证据

验证命令：

```powershell
$env:Path = "C:\Users\22180\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin;" + $env:Path
$env:BUILD_PATH = "build-verify"
.\node_modules\.bin\react-scripts.cmd build
```

验证结果：

1. 前端 production build 成功。
2. 构建输出仍有历史 ESLint warning，但本次目标修复相关的 warning 已改善：
   - `LoginPage.js` 的 unused `SERVERS` import warning 已消失。
   - `IndustryDetailPage.js` 中与 `loadCompareData`、`selectedDate` 相关的 Hook dependency warning 已消失。
3. 临时构建目录 `frontend-client/build-verify` 已在验证后删除，没有覆盖仓库中的既有 `build/` 产物。

保留的非本次范围 warning 主要包括：

1. 多个历史文件存在 UTF-8 BOM。
2. 多个组件存在 unused import / unused variable。
3. `StockDetailPopup.js`、`SectorQueryModule.js`、`SectorTrendModule.js`、`StockRankingModule.js`、`UserManagement.js` 仍有 Hook dependency warning。

## 是否满足验收

- [x] 日志导出不再硬编码 `localhost:8000`。
- [x] 日志导出可携带当前登录 token。
- [x] 登录页服务器检测使用真实 5 秒超时机制。
- [x] 会话过期提示由应用弹窗统一承接，不再同时触发浏览器 `alert()`。
- [x] `IndustryDetailPage` 趋势/对比数据会响应 `selectedDate` 变化。
- [x] 前端 production build 通过。

**结论**：是。本次满足 `SUG-002` 选项 A 的阶段性验收。

---

## 遗留风险 / 后续行动

1. `PRB-002` 未完全关闭。`SUG-002` 选项 B/C 仍可作为后续治理项：
   - 统一下载 API 封装。
   - 清理或隔离废弃 `SectorModule`。
   - 修复 `apiClient.post/put` 丢 URL query 的潜伏问题。
   - 启动期登录态静默校验与后端会话语义对齐。
2. 如果后端启用 `FORCE_SECURE_API=true` 并禁止直连 `/api/admin/logs/export/csv`，当前 `fetch + Authorization` 下载仍可能需要后端提供 signed URL 或 secure 下载能力。
3. 本次只做构建验证，未启动完整 Electron 客户端手动点击验证；后续如进入发布前检查，建议补一次本地/远程服务器切换和 CSV 导出实测。
