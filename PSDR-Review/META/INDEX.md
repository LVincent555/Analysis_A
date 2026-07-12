# DPRS 文档索引

> **说明**：本索引管理 `PSDR-Review` 中的 PRB/SUG/DEC/RES 文档。
> 状态、类型、关联如未确定，请填 `TBD`。临时文件与外部归档不列入本索引。

---

## 项目结构概览

```text
PSDR-Review/
├── META/                  # 规范、技能、索引
├── DEC/                   # 决策记录
├── PRB/                   # 问题记录
├── SUG/                   # 方案建议
└── RES/                   # 结果/复盘
```

---

## DEC（决策记录）

| 编号 | 标题 | 路径 | 状态 | 类型 | 标签 | 关联 |
|------|------|------|------|------|------|------|
| DEC-001 | 文档迁移与 PSDR 流程统一 | `../DEC/DEC-001-文档迁移与PSDR流程统一.md` | [ACTIVE] | Infra / Documentation / Governance | 文档治理, 归档, 流程 | 无 |
| DEC-002 | 采用模块化单体、六边形架构、局部 DDD 与 CQRS 架构 | `../DEC/DEC-002-采用模块化单体六边形局部DDD与CQRS架构.md` | [IMPLEMENTED / EXITED] | Infra / Backend / Architecture / Refactor | 后端架构, 模块化单体, 六边形架构, DDD, CQRS | SUG-003, SUG-004, PRB-003, RES-001, RES-004, RES-005, RES-006, RES-007, RES-008, RES-009, RES-010, RES-011, RES-012, RES-013, RES-014, RES-015, RES-016, RES-017, RES-018, RES-019, RES-020, RES-021, RES-022, RES-023, RES-024, RES-025, RES-034 |
| DEC-003 | Identity RBAC 兼容期授权源策略 | `../DEC/DEC-003-Identity_RBAC兼容期授权源策略.md` | [ACTIVE] | Infra / Backend / Architecture / Security | Identity, RBAC, users.role, user_roles | DEC-002, SUG-003, PRB-003, RES-007 |
| DEC-004 | frontend-client 采用 Electron + React SPA 现代化架构 | `../DEC/DEC-004-frontend-client采用ElectronReactSPA现代化架构.md` | [ACTIVE] | Infra / Frontend / Architecture / Refactor / Governance | 前端架构, Electron, React Router, TanStack Query, Vite, feature 分层 | SUG-005, SUG-002, SUG-004, PRB-002, DEC-002, RES-001, RES-002, RES-013, RES-030, RES-031, RES-034 |

---

## PRB（问题记录）

| 编号 | 标题 | 路径 | 状态 | 类型 | 标签 | 关联 |
|------|------|------|------|------|------|------|
| PRB-001 | 后端认证会话与缓存职责混用风险 | `../PRB/PRB-001-后端认证会话与缓存职责混用风险.md` | [OPEN] | Infra / Backend / Auth / Cache / Audit | 认证, 会话, 缓存, 加密网关 | SUG-001, SUG-003, RES-001, RES-003 |
| PRB-002 | frontend-client 请求链路与状态刷新一致性风险 | `../PRB/PRB-002-frontend-client请求链路与状态刷新一致性风险.md` | [OPEN] | Infra / Frontend / API / UX / Audit | 前端, 请求链路, 登录态, 日期刷新 | SUG-002, SUG-003, RES-001, RES-002, RES-030, RES-031, RES-034 |
| PRB-003 | 后端架构迁移双轨与依赖漂移风险 | `../PRB/PRB-003-后端架构迁移双轨与依赖漂移风险.md` | [OPEN] | Infra / Backend / Architecture / Migration / Risk | 后端架构, 双轨迁移, API 合约, 测试基线 | SUG-003, DEC-002, RES-004 |

---

## SUG（方案建议）

| 编号 | 标题 | 路径 | 状态 | 类型 | 标签 | 关联 |
|------|------|------|------|------|------|------|
| SUG-001 | 后端认证会话与缓存修复建议 | `../SUG/SUG-001-后端认证会话与缓存修复建议.md` | [OPEN] | Infra / Backend / Auth / Cache / Refactor | 认证, 会话, 缓存, 修复建议 | PRB-001, RES-003 |
| SUG-002 | frontend-client 请求与状态一致性修复建议 | `../SUG/SUG-002-frontend-client请求与状态一致性修复建议.md` | [OPEN] | Infra / Frontend / API / UX / Refactor | 前端, 请求层, 下载, 登录态, 状态刷新 | PRB-002, RES-002 |
| SUG-003 | 后端模块化单体与六边形架构重构方案 | `../SUG/SUG-003-后端模块化单体与六边形架构重构方案.md` | [IMPLEMENTED / EXITED] | Infra / Backend / Architecture / Refactor | 后端架构, 模块化单体, 六边形架构, DDD, CQRS | RES-001, PRB-001, PRB-002, PRB-003, DEC-002, DEC-003, SUG-004, RES-004, RES-005, RES-006, RES-007, RES-008, RES-009, RES-010, RES-011, RES-012, RES-013, RES-014, RES-015, RES-016, RES-017, RES-018, RES-019, RES-020, RES-021, RES-022, RES-023, RES-024, RES-025 |
| SUG-004 | HTTP 环境登录加密与安全网关加固方案 | `../SUG/SUG-004-HTTP环境登录加密与安全网关加固方案.md` | [ACCEPTED / IMPLEMENTED] | Infra / Backend / Frontend / Security / Architecture | HTTP, secure-login, secure-refresh, JWT, nonce, gateway, Electron | DEC-002, DEC-003, SUG-001, RES-003, RES-005, RES-012, RES-013, RES-034 |
| SUG-005 | frontend-client 架构现代化与模块化重构方案 | `../SUG/SUG-005-frontend-client架构现代化与模块化重构方案.md` | [ACCEPTED] | Infra / Frontend / Architecture / Refactor | 前端架构, Electron, React Router, TanStack Query, Vite, feature 分层 | PRB-002, SUG-002, SUG-004, DEC-004, RES-001, RES-002, RES-013, RES-030, RES-031, RES-034 |
| SUG-006 | 后端缓存系统治理与演进方案 | `../SUG/SUG-006-后端缓存系统治理与演进方案.md` | [IMPLEMENTED / EXPERIMENTAL-PHASE5] | Infra / Backend / Cache / Architecture / Refactor | 后端缓存, UnifiedCache, ObjectStore, FileStore, NumpyCache, 缓存治理 | PRB-001, SUG-001, SUG-003, DEC-002, RES-003, RES-014, RES-016, RES-023, RES-024, RES-026, RES-027, RES-028, RES-029, RES-032, RES-033, RES-034 |
| SUG-007 | 中文自然键查询接口 POST 化与加密网关路径治理方案 | `../SUG/SUG-007-中文自然键查询接口POST化与加密网关路径治理方案.md` | [PROPOSED] | Infra / Backend / Frontend / API / Security / Refactor | 中文 path, 自然键, POST query, secure gateway, path canonicalize | SUG-004, SUG-005, DEC-002, DEC-004, RES-013, RES-034 |

---

## RES（结果/复盘）

| 编号 | 标题 | 路径 | 状态 | 类型 | 标签 | 关联 |
|------|------|------|------|------|------|------|
| RES-001 | backend 与 frontend-client 现状探查 | `../RES/RES-001-backend与frontend-client现状探查.md` | [SOLVED] | Infra / Documentation / Audit | 现状盘点, 后端, 客户端 | DEC-001, SUG-003, DEC-002 |
| RES-002 | frontend-client 请求与状态一致性修复结果 | `../RES/RES-002-frontend-client请求与状态一致性修复结果.md` | [SOLVED] | Infra / Frontend / API / UX / Bugfix | 前端, 请求层, 下载, 登录态, 状态刷新 | PRB-002, SUG-002 |
| RES-003 | 后端认证会话与缓存修复结果 | `../RES/RES-003-后端认证会话与缓存修复结果.md` | [SOLVED] | Infra / Backend / Auth / Cache / Bugfix | 认证, 会话, 缓存, 登录有效期 | PRB-001, SUG-001 |
| RES-004 | 后端 uv 测试基线落地结果 | `../RES/RES-004-后端uv测试基线落地结果.md` | [SOLVED] | Infra / Backend / Testing / Baseline | uv, pytest, 单元测试, 架构迁移基线 | PRB-003, SUG-003, DEC-002 |
| RES-005 | DEC-002 Level 0 与 Identity 第一批迁移结果 | `../RES/RES-005-DEC-002-Level0与Identity第一批迁移结果.md` | [PARTIAL] | Infra / Backend / Architecture / Migration | Level 0, Identity, shared, contexts, import boundary | DEC-002, SUG-003, PRB-003, RES-004 |
| RES-006 | Identity 会话管理迁移结果 | `../RES/RES-006-Identity会话管理迁移结果.md` | [PARTIAL] | Infra / Backend / Architecture / Migration | Identity, session management, CQRS, audit log | DEC-002, SUG-003, PRB-003, RES-005 |
| RES-007 | Identity 角色权限查询侧迁移结果 | `../RES/RES-007-Identity角色权限查询侧迁移结果.md` | [PARTIAL] | Infra / Backend / Architecture / Migration | Identity, RBAC, CQRS, permissions | DEC-002, SUG-003, PRB-003, RES-006 |
| RES-008 | Identity 角色权限命令侧迁移结果 | `../RES/RES-008-Identity角色权限命令侧迁移结果.md` | [PARTIAL] | Infra / Backend / Architecture / Migration | Identity, RBAC, command use case, audit log | DEC-002, DEC-003, SUG-003, PRB-003, RES-007 |
| RES-009 | Identity 用户管理查询侧迁移结果 | `../RES/RES-009-Identity用户管理查询侧迁移结果.md` | [PARTIAL] | Infra / Backend / Architecture / Migration | Identity, user management, CQRS, query side | DEC-002, DEC-003, SUG-003, PRB-003, RES-008 |
| RES-010 | Identity 用户管理命令侧迁移与旧 Service 退场结果 | `../RES/RES-010-Identity用户管理命令侧迁移与旧Service退场结果.md` | [PARTIAL] | Infra / Backend / Architecture / Migration | Identity, user management, command use case, service retirement | DEC-002, DEC-003, SUG-003, PRB-003, RES-009 |
| RES-011 | Operations 日志管理迁移与 API 契约导出修复结果 | `../RES/RES-011-Operations日志管理迁移与API契约导出修复结果.md` | [PARTIAL] | Infra / Backend / Architecture / Migration / Testing | Operations, operation logs, CQRS, API contract | DEC-002, DEC-003, SUG-003, PRB-003, RES-010 |
| RES-012 | Operations 配置管理迁移与配置值校验修复结果 | `../RES/RES-012-Operations配置管理迁移与配置值校验修复结果.md` | [PARTIAL] | Infra / Backend / Architecture / Migration / Bugfix / Testing | Operations, system config, validation, cache reload | DEC-002, DEC-003, SUG-003, PRB-003, RES-011 |
| RES-013 | DEC-002 Level 1.5 HTTP 环境安全加固结果 | `../RES/RES-013-DEC-002-Level1.5-HTTP环境安全加固结果.md` | [SOLVED] | Infra / Backend / Frontend / Security / Architecture / Testing | secure-login, secure-refresh, JWT, nonce, gateway, Electron | DEC-002, SUG-004, SUG-003, RES-012 |
| RES-014 | Operations 缓存管理迁移结果 | `../RES/RES-014-Operations缓存管理迁移结果.md` | [SOLVED] | Infra / Backend / Architecture / Migration / Testing | Operations, cache, CQRS, compatibility | DEC-002, SUG-003, RES-011, RES-012, RES-013 |
| RES-015 | Operations 审计缓冲迁移与字段映射修复结果 | `../RES/RES-015-Operations审计缓冲迁移与字段映射修复结果.md` | [SOLVED] | Infra / Backend / Architecture / Migration / Bugfix / Testing | Operations, audit, write-behind, compatibility | DEC-002, SUG-003, RES-011, RES-012, RES-014 |
| RES-016 | Operations 策略提供器收敛结果 | `../RES/RES-016-Operations策略提供器收敛结果.md` | [SOLVED] | Infra / Backend / Architecture / Migration / Testing | Operations, policy, config cache, compatibility | DEC-002, SUG-003, RES-012, RES-015 |
| RES-017 | Analysis 排行趋势查询侧首批迁移结果 | `../RES/RES-017-Analysis排行趋势查询侧首批迁移结果.md` | [PARTIAL] | Infra / Backend / Architecture / Migration / Testing | Analysis, CQRS, rank_jump, steady_rise, compatibility | DEC-002, SUG-003, RES-016 |
| RES-018 | Analysis 基础查询侧迁移结果 | `../RES/RES-018-Analysis基础查询侧迁移结果.md` | [PARTIAL] | Infra / Backend / Architecture / Migration / Testing | Analysis, CQRS, dates, analyze_period, volatility, compatibility | DEC-002, SUG-003, RES-017 |
| RES-019 | MarketData 股票查询侧迁移结果 | `../RES/RES-019-MarketData股票查询侧迁移结果.md` | [PARTIAL] | Infra / Backend / Architecture / Migration / Testing | MarketData, stock, CQRS, read adapter, compatibility | DEC-002, SUG-003, RES-018 |
| RES-020 | MarketData 板块查询侧迁移结果 | `../RES/RES-020-MarketData板块查询侧迁移结果.md` | [PARTIAL] | Infra / Backend / Architecture / Migration / Testing | MarketData, sector, CQRS, read adapter, route-order | DEC-002, SUG-003, RES-019 |
| RES-021 | Analysis 行业查询侧迁移结果 | `../RES/RES-021-Analysis行业查询侧迁移结果.md` | [PARTIAL] | Infra / Backend / Architecture / Migration / Testing | Analysis, industry, CQRS, signal, compatibility | DEC-002, SUG-003, RES-020 |
| RES-022 | Analysis 策略查询侧迁移结果 | `../RES/RES-022-Analysis策略查询侧迁移结果.md` | [PARTIAL] | Infra / Backend / Architecture / Migration / Testing | Analysis, strategies, needle-under-20, CQRS, compatibility | DEC-002, SUG-003, RES-021 |
| RES-023 | Analysis 热点榜查询侧迁移结果 | `../RES/RES-023-Analysis热点榜查询侧迁移结果.md` | [SOLVED] | Infra / Backend / Architecture / Migration / Testing | Analysis, hot-spots, CQRS, cache, compatibility | DEC-002, SUG-003, RES-022 |
| RES-024 | BoardHeat 与同步导入迁移结果 | `../RES/RES-024-BoardHeat与同步导入迁移结果.md` | [SOLVED] | Infra / Backend / Architecture / Migration / Testing | BoardHeat, MarketData, sync, import, admin, CQRS, command | DEC-002, SUG-003, RES-023 |
| RES-025 | DEC-002 旧结构退场与最终收口结果 | `../RES/RES-025-DEC-002旧结构退场与最终收口结果.md` | [SOLVED] | Infra / Backend / Architecture / Migration / Testing / Closure | DEC-002, composition-root, compatibility, closure | DEC-002, SUG-003, RES-024 |
| RES-026 | 后端缓存系统治理 Phase 0 落地结果 | `../RES/RES-026-后端缓存系统治理Phase0落地结果.md` | [SOLVED] | Infra / Backend / Cache / Architecture / Testing | 后端缓存, UnifiedCache, registry, bootstrap, pytest | SUG-006, PRB-001, SUG-001, DEC-002, RES-014 |
| RES-027 | 后端缓存系统治理 Phase 1 容量与 Metrics 落地结果 | `../RES/RES-027-后端缓存系统治理Phase1容量与Metrics落地结果.md` | [SOLVED] | Infra / Backend / Cache / Architecture / Testing | 后端缓存, ObjectStore, LRU, metrics, FileStore | SUG-006, RES-026, PRB-001, SUG-001, DEC-002, RES-014 |
| RES-028 | 后端缓存系统治理 Phase 2 策略失败语义落地结果 | `../RES/RES-028-后端缓存系统治理Phase2策略失败语义落地结果.md` | [SOLVED] | Infra / Backend / Cache / Reliability / Testing | 后端缓存, WriteThrough, WriteBehind, Syncer, failure-semantics | SUG-006, RES-026, RES-027, PRB-001, SUG-001, DEC-002, RES-014 |
| RES-029 | 后端缓存系统治理 Phase 3 管理 API 增强落地结果 | `../RES/RES-029-后端缓存系统治理Phase3管理API增强落地结果.md` | [SOLVED] | Infra / Backend / Cache / Operations / Testing | 后端缓存, Operations, cache stats, health, clear, reload | SUG-006, RES-026, RES-027, RES-028, PRB-001, SUG-001, DEC-002, RES-014 |
| RES-030 | DEC-004 frontend-client 架构骨架落地结果 | `../RES/RES-030-DEC-004-frontend-client架构骨架落地结果.md` | [PARTIAL] | Infra / Frontend / Architecture / Refactor / Testing | 前端架构, React Router, TanStack Query, module registry, AppShell | DEC-004, SUG-005, PRB-002, SUG-002, SUG-004, RES-001, RES-002, RES-013 |
| RES-031 | DEC-004 frontend-client 联调前架构收敛结果 | `../RES/RES-031-DEC-004-frontend-client联调前架构收敛结果.md` | [PARTIAL / READY-FOR-INTEGRATION] | Infra / Frontend / Architecture / Refactor / Testing | 前端架构, navigationConfig, TanStack Query, HotSpots, Electron bridge | DEC-004, SUG-005, PRB-002, SUG-002, SUG-004, RES-030 |
| RES-032 | 后端缓存系统治理 Phase 4 历史缓存收口落地结果 | `../RES/RES-032-后端缓存系统治理Phase4历史缓存收口落地结果.md` | [SOLVED] | Infra / Backend / Cache / Architecture / Testing | 后端缓存, UnifiedCache, NumpyCache, HotSpotsCache, logical region | SUG-006, RES-026, RES-027, RES-028, RES-029, PRB-001, SUG-001, DEC-002, RES-014 |
| RES-033 | 后端缓存系统治理 Phase 5 实验运行态外部化落地结果 | `../RES/RES-033-后端缓存系统治理Phase5实验运行态外部化落地结果.md` | [SOLVED / EXPERIMENTAL] | Infra / Backend / Cache / Security / Runtime / Testing | 后端缓存, RuntimeStateStore, session_keys, replay nonce, diskcache | SUG-006, RES-026, RES-027, RES-028, RES-029, RES-032, PRB-001, SUG-001, DEC-002, RES-014 |
| RES-034 | 本地前后端联调启动验证结果 | `../RES/RES-034-本地前后端联调启动验证结果.md` | [SOLVED] | Experiment / Infra / Backend / Frontend / Integration | 本地联调, secure-login, secure gateway, Numpy cache, HotSpots, IndustryTrend | DEC-002, DEC-004, SUG-004, SUG-006, PRB-002, RES-031 |
| RES-035 | DevOps 脚本归拢与部署入口审核结果 | `../RES/RES-035-DevOps脚本归拢与部署入口审核结果.md` | [SOLVED] | Infra / DevOps / Documentation | devops, 部署脚本, 一键部署, 脚本治理 | DEC-001, RES-034 |
| RES-036 | frontend-client 服务器公钥 Electron 目录包重打结果 | `../RES/RES-036-frontend-client服务器公钥Electron目录包重打结果.md` | [SOLVED] | Infra / Frontend / Electron / Packaging / Security | frontend-client, Electron, secure-login, 服务器公钥, win-unpacked | DEC-004, SUG-004, RES-034 |
| RES-037 | 导入后缓存刷新与外部板块同步卡死修复结果 | `../RES/RES-037-导入后缓存刷新与外部板块同步卡死修复结果.md` | [SOLVED / UNIT-VERIFIED / INTEGRATION-BLOCKED-BY-DB] | Infra / Backend / Cache / Sync / Bugfix / Testing | 导入, 运行态缓存, NumpyCache, HotSpotsCache, 外部板块同步, 子进程超时 | SUG-006, DEC-002, RES-024, RES-033, RES-034 |

---

## META 规范文档

| 文件名 | 说明 |
|--------|------|
| SKILL-DPRS.md | DPRS 决策流程核心规范 |
| 规范-PRB-引用提问流.md | 外部 AI 咨询工作流 |
| INDEX.md（本文档） | 文档索引总览 |
