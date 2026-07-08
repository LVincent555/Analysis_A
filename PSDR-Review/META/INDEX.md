# DPRS 文档索引

> **说明**：本索引管理 Review 系统中的 PRB/SUG/DEC/RES 文档。
>
> 状态/类型/关联如未确定，请填 TBD。Temp 文件与临时资源未列入。

---

## 项目结构概览

```
project/
├── review/                    ← 本索引管理范围
│   ├── META/                  # 规范、技能、索引
│   ├── DEC/                   # 决策记录
│   ├── PRB/                   # 问题记录
│   ├── SUG/                   # 方案建议
│   └── RES/                   # 结果/复盘
```

---

## DEC（决策记录）

| 编号 | 标题 | 路径 | 状态 | 类型 | 标签 | 关联 |
|------|------|------|------|------|------|------|
| DEC-001 | 文档迁移与 PSDR 流程统一 | `../DEC/DEC-001-文档迁移与PSDR流程统一.md` | [ACTIVE] | Infra / Documentation / Governance | 文档治理, 归档, 流程 | 无 |

---

## PRB（问题记录）

| 编号 | 标题 | 路径 | 状态 | 类型 | 标签 | 关联 |
|------|------|------|------|------|------|------|
| PRB-001 | 后端认证会话与缓存职责混用风险 | `../PRB/PRB-001-后端认证会话与缓存职责混用风险.md` | [OPEN] | Infra / Backend / Auth / Cache / Audit | 认证, 会话, 缓存, 加密网关 | SUG-001, RES-001, RES-003 |
| PRB-002 | frontend-client 请求链路与状态刷新一致性风险 | `../PRB/PRB-002-frontend-client请求链路与状态刷新一致性风险.md` | [OPEN] | Infra / Frontend / API / UX / Audit | 前端, 请求链路, 登录态, 日期刷新 | SUG-002, RES-001, RES-002 |

---

## SUG（方案建议）

| 编号 | 标题 | 路径 | 状态 | 类型 | 标签 | 关联 |
|------|------|------|------|------|------|------|
| SUG-001 | 后端认证会话与缓存修复建议 | `../SUG/SUG-001-后端认证会话与缓存修复建议.md` | [OPEN] | Infra / Backend / Auth / Cache / Refactor | 认证, 会话, 缓存, 修复建议 | PRB-001, RES-003 |
| SUG-002 | frontend-client 请求与状态一致性修复建议 | `../SUG/SUG-002-frontend-client请求与状态一致性修复建议.md` | [OPEN] | Infra / Frontend / API / UX / Refactor | 前端, 请求层, 下载, 登录态, 状态刷新 | PRB-002, RES-002 |

---

## RES（结果/复盘）

| 编号 | 标题 | 路径 | 状态 | 类型 | 标签 | 关联 |
|------|------|------|------|------|------|------|
| RES-001 | backend 与 frontend-client 现状探查 | `../RES/RES-001-backend与frontend-client现状探查.md` | [SOLVED] | Infra / Documentation / Audit | 现状盘点, 后端, 客户端 | DEC-001 |
| RES-002 | frontend-client 请求与状态一致性修复结果 | `../RES/RES-002-frontend-client请求与状态一致性修复结果.md` | [SOLVED] | Infra / Frontend / API / UX / Bugfix | 前端, 请求层, 下载, 登录态, 状态刷新 | PRB-002, SUG-002 |
| RES-003 | 后端认证会话与缓存修复结果 | `../RES/RES-003-后端认证会话与缓存修复结果.md` | [SOLVED] | Infra / Backend / Auth / Cache / Bugfix | 认证, 会话, 缓存, 登录有效期 | PRB-001, SUG-001 |

---

## META 规范文档

| 文件名 | 说明 |
|--------|------|
| SKILL-DPRS.md | DPRS 决策流程核心规范 |
| 规范-PRB-引用提问流.md | 外部 AI 咨询工作流 |
| INDEX.md（本文件） | 文档索引总览 |
