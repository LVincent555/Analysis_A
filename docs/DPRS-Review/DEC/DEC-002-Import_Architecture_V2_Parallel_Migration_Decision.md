# DEC-002: Import Architecture V2 并行重构与迁移决策

**日期**: 2026-02-09  
**状态**: [ACTIVE]  
**类型**: Infra / Architecture  
**层级**: 模块-import  
**关联**: PRB-001-Import_Idempotency_Failure_Analysis, RES-001-Import_Duplicate_Key_Fix, SUG-001-Import_Idempotency_Robustness_Hardening, SUG-002-Import_Architecture_V2_Modular_HA_Blueprint

---

## 决策

采用 `SUG-002` 的推荐方案（选项 B）：  
在 `stock_analysis_app/backend/scripts/importScript` 下建设 Import V2 新架构，与旧导入链路并行运行；旧模块继续维护使用，当前阶段不替换、不下线。

---

## 决策冻结项（已拍板）

1. 并行周期：`2~4 周`（默认 4 周窗口，2026-02-10 至 2026-03-09）。  
2. 运行模式：`独立 orchestrator + worker`，不绑定 API 启动。  
3. 状态真相：`数据库任务表为主`，JSON 状态文件仅做兼容镜像。  
4. 幂等策略：`idempotency_key + UPSERT + 字段级覆盖规则`。  
5. 锁粒度：`dataset + trade_date`。  
6. 重试策略：`指数退避，最多 3 次，失败进入 DLQ`。  
7. 质量门禁：`计数 + 哈希 + 关键指标` 三重校验。  
8. 灰度策略：`按日期分批切流`，支持一键回退旧链路。  
9. 替换条件：并发/幂等/恢复/性能验收全部通过后再替换。  
10. 当前动作：先建设新版本与目录骨架，不接管生产入口。

---

## 范围

**做**
- 在 `backend/scripts/importScript` 建立 V2 分层结构与插件化骨架。  
- 构建统一任务模型（run/task/attempt/checkpoint）与数据库状态真相。  
- 建立 stock/sector 插件链路（discover/plan/transform/load/reconcile）。  
- 建立可观测与审计体系（run_id 全链路日志、指标、告警基础）。  
- 提供 legacy/api 适配层，保障旧入口可并行共存。

**不做**
- 不修改当前生产默认入口行为。  
- 不删除或重命名旧脚本。  
- 不在本 DEC 阶段进行强制切流。  
- 不把启动流程继续耦合全量导入任务。

---

## 里程碑与时间窗

1. 2026-02-10 至 2026-02-16：Phase 0（模型与契约冻结，目录骨架完成）。  
2. 2026-02-17 至 2026-02-23：Phase 1（Shadow 并行运行，主链路不切换）。  
3. 2026-02-24 至 2026-03-02：Phase 2（Canary 灰度，按日期切流）。  
4. 2026-03-03 至 2026-03-09：Phase 3 预备（验收汇总，决定是否进入默认切换）。  

备注：如并行验证数据不足，可延长至 2026-03-16 再做切换决策。

---

## 责任与协作

- 业务决策 Owner：项目负责人（你）。  
- 架构与实施 Owner：导入重构工作流（Codex 协作执行）。  
- 变更原则：旧链路优先稳定，新链路独立演进，任何切流需通过验收门。

---

## 验收标准（切换前必须全部满足）

1. 幂等：同一 `idempotency_key` 重复执行 10 次，主表结果一致。  
2. 并发：同 `dataset + trade_date` 并发触发 N 次，仅 1 次执行成功，其他安全复用/跳过。  
3. 恢复：故障中断后重启可恢复，不产生重复/脏写。  
4. 性能：导入总时长不劣于旧链路（基线允许 ±10% 波动）。  
5. 可用性：导入失败不影响 API 启动与核心查询接口。  
6. 可观测：按 `run_id` 可追踪全流程，失败原因可归类可审计。  

---

## 回退与风险控制

- 灰度阶段保留旧链路为默认可回退路径。  
- 任一关键验收项失败：立即停止切流，回到旧链路，V2 继续修复。  
- 回退不做 destructive 操作，不清理旧状态数据，保留复盘证据。  

---

## 后续动作

1. 基于本 DEC 创建 Phase 0 任务清单与文件级 WBS。  
2. 在 `backend/scripts/importScript` 建立 V2 空骨架与契约文档。  
3. 完成 Shadow 运行脚本与验收报表模板（为 Phase 1 准备）。

