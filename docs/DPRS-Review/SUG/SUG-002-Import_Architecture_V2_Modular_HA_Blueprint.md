# SUG-002: Import Architecture V2（模块化 / 可扩展 / 高可用）重构蓝图
**日期**: 2026-02-09  
**状态**: [OPEN]  
**类型**: Infra / Architecture  
**层级**: 模块-import  
**关联**: PRB-001-Import_Idempotency_Failure_Analysis, RES-001-Import_Duplicate_Key_Fix, SUG-001-Import_Idempotency_Robustness_Hardening

---

## 背景与结论先行

SUG-001 已经覆盖了“先止血”的修补路径，本方案不重复小修复。  
SUG-002 的目标是给出 **并行落地的新一代导入架构（V2）**，满足以下硬要求：

- 真正幂等（不仅是“先删后导”）
- 并发安全（同日期/同数据集并发导入不破坏一致性）
- 高可用（导入失败不拖垮 API 启动与主服务可用性）
- 模块化（拆分职责，支持 stock/sector/ext_board 等插件扩展）
- 与旧实现共存（`update_daily_data.py` 与既有后端调用先保留）

结论：推荐 **选项 B（双轨并行的 Import V2 全新架构）**。  
选项 B 不是“改造旧脚本”，而是 `backend/scripts` 下新建一套可独立演进的架构，旧逻辑保留并通过兼容层平滑迁移。

---

## 现状关键问题（基于当前代码链路）

- 状态真相分裂：当前以 JSON 状态文件为主（`import_state_manager.py`），数据库事实与状态文件可能漂移，存在“状态覆盖/竞态”风险。
- 导入链路重复耦合：CLI（`update_daily_data.py`）、脚本（`data_importer.py`）、API（`admin.py`）、启动检查（`main.py` -> `run_startup_checks()`）均直接耦合导入细节。
- 原子边界不统一：stock 与 sector 的异常处理策略不一致，部分逻辑存在“行级异常后重开 session”的副作用风险。
- 幂等策略脆弱：当前主要通过“状态判断 + 删除当日再导入”实现，缺少数据库级任务幂等与批次语义。
- 可观测性不足：缺少统一的 run/task/attempt 指标模型，无法稳定支持审计、重放、告警、SLA。
- 高可用风险：应用启动阶段执行导入/校验会拉长启动时间，且导入失败可能影响服务可用。

---

## 选项对比

## 选项 A：在现有脚本基础上继续演进（中等改造）
- **做法**: 保留现有脚本文件结构，只抽取少量公共模块，逐步替换状态与事务逻辑。
- **收益**: 变更小、上线快、短期心智负担低。
- **风险**: 遗留耦合仍在，长期会回到“脚本堆叠 + 隐式副作用”，难满足高可用和可扩展目标。
- **验证**: 可通过，但只能达到“改良版旧架构”。

## 选项 B：Import V2 双轨并行新架构（推荐）
- **做法**: 在 `backend/scripts` 下新增 `v2` 架构，建立任务编排、插件驱动、数据库状态真相、统一可观测体系。
- **收益**: 一次性解决幂等/并发/可用性/扩展性问题；支持无停机迁移和逐步切流。
- **风险**: 设计与实施成本高，需要分阶段推进和严格验收。
- **验证**: 支持并发、重试、故障注入、回放校验、灰度切换。

## 选项 C：维持现状（不建议）
- **做法**: 继续依赖 SUG-001 的补丁路径。
- **收益**: 无额外改造成本。
- **风险**: 架构债务持续累积，后续任何新数据类型都会放大维护成本与故障概率。
- **验证**: 不满足“全新架构”目标。

---

## 推荐

推荐 **选项 B：Import V2 双轨并行新架构**。

理由：
- 这是唯一能同时满足“模块化、可扩展、高可用、真幂等”的路径。
- 可以不动旧入口先落地新体系，降低迁移风险。
- 支持“先旁路验证、后灰度切换、再默认启用”的工程化落地。

---

## Import V2 目标架构

### 1) 分层模型

- `Domain`：导入任务、批次、幂等键、失败分类、重试策略等纯业务语义
- `Application`：工作流编排（扫描 -> 计划 -> 执行 -> 提交 -> 校验 -> 发布）
- `Infrastructure`：数据库仓储、文件读取、锁、队列、日志、指标、告警
- `Interface`：CLI/API/调度器/兼容层

### 2) `backend/scripts` 新目录形态（仅设计，不改现有代码）

```text
backend/scripts/
  v2/
    cli/
      import_cli.py                 # 新 CLI 入口（可被 update_daily_data 兼容调用）
    interfaces/
      api_adapter.py                # 给 app/routers/admin.py 的统一入口
      legacy_adapter.py             # 兼容老调用签名
    application/
      orchestrator.py               # 导入编排器（核心）
      scheduler.py                  # 任务调度（立即/定时/重试）
      services/
        import_service.py
        reconciliation_service.py
    domain/
      models.py                     # ImportRun/Task/Batch/Checkpoint
      policies.py                   # 幂等、重试、冲突策略
      events.py                     # 领域事件
      ports.py                      # 抽象接口
    infrastructure/
      db/
        repositories.py             # Run/Task/Result 仓储
        unit_of_work.py             # 事务边界
        locking.py                  # PG advisory lock / 行级锁
      io/
        file_discovery.py           # 文件发现
        excel_reader.py             # Excel 流式读取
        schema_mapper.py            # 列映射与校验
      execution/
        workers.py                  # 并发 worker
        retry.py                    # 回退与重试
      observability/
        logging.py
        metrics.py
        tracing.py
    plugins/
      stock/
        plugin.py
        transform.py
        load.py
      sector/
        plugin.py
        transform.py
        load.py
      ext_board/
        plugin.py
    contracts/
      dto.py                        # 统一输入输出契约
```

### 3) 插件化扩展点

每个数据域（stock/sector/ext_board/未来新数据集）实现统一插件接口：

- `discover()`：发现输入文件
- `plan()`：产生导入任务（按日期/分片）
- `parse_validate()`：读取与校验
- `transform()`：规范化、修补、去重
- `load()`：写入策略（upsert/merge/replace）
- `reconcile()`：导入后校验（计数、校验和、关键指标）

这样新增一个数据域时，不改编排器核心，只加插件。

---

## 状态真相与幂等模型（V2 核心）

### 1) 状态真相来源

由 “JSON 状态文件为主” 升级为 “数据库任务表为主，文件状态为辅”：

- `import_runs`：一次导入运行实例
- `import_tasks`：运行内任务（按 dataset/date/file 分解）
- `import_attempts`：每次尝试与重试明细
- `import_checkpoints`：断点进度（可选）
- `import_artifacts`：输入文件哈希、版本、快照信息

JSON 状态文件转为 **缓存/兼容视图**，不再作为唯一事实来源。

### 2) 幂等键设计

`idempotency_key = dataset + trade_date + file_hash + schema_version`

保障：
- 同一输入重复提交不会重复入库
- 文件变更自动形成新键，可被识别为新任务
- 任务可重放，但结果可判重

### 3) 写入策略

- 主表保留唯一键：`(stock_code, date)` / `(sector_id, date)`
- 默认写入采用 `UPSERT`（冲突策略可配置：覆盖/保留/按字段优先级）
- 对“整日覆盖”场景采用 `staging -> merge -> finalize`，禁止“先删后导”裸流程

---

## 并发与高可用设计

### 1) 并发控制

- 任务级锁：`dataset + trade_date` 粒度分布式锁（优先 PostgreSQL advisory lock）
- 单任务串行，跨日期并行（可配置 worker 数）
- 所有 worker 无状态，可水平扩展

### 2) 故障恢复

- at-least-once 执行 + 幂等去重，达到业务上的 exactly-once 效果
- 重试策略：指数退避 + 最大重试 + 死信队列（DLQ）
- 可恢复失败：网络抖动、临时锁冲突、瞬时文件占用
- 不可恢复失败：结构校验失败、关键字段缺失，直接标记终态并告警

### 3) 服务可用性

- 导入从 API 启动流程解耦：应用启动只做轻量健康检查，不阻塞于全量导入
- 导入执行迁移到独立 orchestrator/worker（同进程或独立进程均可）
- API 始终可用，导入状态通过任务 API 查询

---

## 可观测与运维治理

### 1) 统一日志与审计

- 每个 `run_id / task_id / attempt_id` 全链路关联日志
- 错误分类：解析失败、校验失败、数据库冲突、超时、系统异常
- 审计字段：触发来源（CLI/API/Scheduler）、操作者、参数、文件摘要

### 2) 指标体系

- 吞吐：tasks/min、rows/s
- 稳定性：成功率、重试率、失败率、DLQ 数
- 时延：任务排队时间、执行时间、端到端完成时间
- 数据质量：去重数、异常修补数、校验差异率

### 3) 告警

- 连续失败阈值告警
- 同日期重复冲突异常告警
- 任务长时间 `running` 告警
- 数据校验 mismatch 告警

---

## 兼容与迁移方案（保留旧模块）

### 迁移原则

- 不改 `update_daily_data.py` 现有行为（第一阶段）
- 旧导入脚本继续可用，作为回退路径
- 新架构通过适配层承接 CLI/API 调用

### 分阶段路线

1. **Phase 0 - 设计与基线**  
   建立 V2 数据模型与契约；梳理现有调用清单（CLI/API/startup）。

2. **Phase 1 - 双写观测（Shadow）**  
   旧链路继续写生产表；V2 并行跑“只校验不落主表”。

3. **Phase 2 - 小流量切换（Canary）**  
   按日期/数据集灰度到 V2，保留一键回切旧链路。

4. **Phase 3 - 默认走 V2**  
   `admin/import` 与调度入口默认调用 V2；旧链路降级为 fallback。

5. **Phase 4 - 收敛与退役**  
   删除重复能力，旧脚本只保留最小兼容壳，最终归档。

---

## 现有模块到 V2 的归位映射

- `import_data_robust.py` -> `plugins/stock/*` + `application/orchestrator.py`
- `import_sectors_robust.py` -> `plugins/sector/*` + `application/orchestrator.py`
- `import_state_manager.py` -> `infrastructure/db/repositories.py` + `contracts/dto.py`
- `data_fixer.py` -> `plugins/*/transform.py`（规则引擎化）
- `deduplicate_helper.py` -> `plugins/stock/transform.py`（策略化）
- `data_importer.py` -> `interfaces/legacy_adapter.py`（仅兼容入口）
- `app/routers/admin.py` 的导入段 -> `interfaces/api_adapter.py`

---

## 验收标准（必须全部满足）

- 幂等：同一 `idempotency_key` 重复执行 10 次，主表结果完全一致
- 并发：同 dataset/date 并发触发 N 次，只允许 1 次执行，其余安全跳过/复用结果
- 恢复：中断后重启可继续任务或安全重试，不产生重复数据
- 可用：导入失败不影响 API 启动与在线查询
- 兼容：旧入口命令与 API 契约不破坏，支持灰度回退
- 可观测：可按 `run_id` 追踪全链路，关键指标可用于告警

---

## 风险与前置条件

- 需要新增导入任务元数据表（数据库变更）
- 需要明确冲突更新策略（覆盖、字段优先、时间优先）
- 需要确定调度模型（进程内 worker vs 独立 worker）
- 需要定义数据质量基线（计数、哈希、关键字段统计）
- 需要预留灰度开关与回退开关（配置中心/环境变量）

---

## 对 SUG-001 的关系说明

- SUG-001 继续作为“当前生产止血方案”，不修改。
- SUG-002 是下一阶段架构升级蓝图，两者并行存在。
- 实施顺序：先稳住现网（SUG-001），再按阶段推进 V2（SUG-002）。

