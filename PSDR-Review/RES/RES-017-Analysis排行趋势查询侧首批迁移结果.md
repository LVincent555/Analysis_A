# RES-017: Analysis 排行趋势查询侧首批迁移结果

**日期**: 2026-07-08
**状态**: [PARTIAL]
**类型**: Infra / Backend / Architecture / Migration / Testing
**层级**: Backend
**关联**: DEC-002, SUG-003, RES-016

---

## 结果摘要

已完成 DEC-002 Level 3 的第一批低风险查询侧迁移：`rank_jump` 与 `steady_rise` 从旧 router 业务编排中迁入 `contexts.analysis`，外部 API 路径、查询参数、响应模型和旧算法实现保持兼容。

本次迁移只处理排行跳变和稳步上升两个 read-heavy 查询入口，尚不代表 Level 3 全部完成。`analysis.py`、`stock.py`、`sector.py`、`industry_detail.py`、`strategies.py` 仍需后续批次继续迁移。

---

## 已完成改动

1. 新增 Analysis 查询 DTO：
   - `contexts.analysis.application.queries.AnalyzeRankJumpQuery`
   - `contexts.analysis.application.queries.AnalyzeSteadyRiseQuery`
   - `contexts.analysis.application.queries.SignalThresholdSettings`

2. 新增 Analysis application port：
   - `RankJumpAnalysisPort`
   - `SteadyRiseAnalysisPort`

3. 新增查询用例：
   - `AnalyzeRankJumpUseCase`
   - `AnalyzeSteadyRiseUseCase`

4. 新增 infrastructure adapter：
   - `contexts.analysis.infrastructure.rank_trend_analysis.LegacyRankTrendAnalysisAdapter`
   - 该 adapter 继续调用旧 `rank_jump_service_db` 与 `steady_rise_service_db`，不改 Numpy/cache/算法逻辑。
   - `SignalThresholdSettings` 会转换为旧 `SignalThresholds`，保持信号阈值行为一致。

5. 新增 Analysis API adapter：
   - `contexts.analysis.api.rank_router.rank_jump_router`
   - `contexts.analysis.api.rank_router.steady_rise_router`

6. 旧 router 退为兼容入口：
   - `app.routers.rank_jump`
   - `app.routers.steady_rise`

---

## API 契约

保持以下路径不变：

```text
GET /api/rank_jump
GET /api/rank-jump
GET /api/steady-rise
```

API contract 导出结果：

```text
126 routes
```

三条迁移路径当前 endpoint 已指向新 Analysis API adapter：

```text
app.contexts.analysis.api.rank_router.analyze_rank_jump
app.contexts.analysis.api.rank_router.analyze_steady_rise
```

---

## 测试与验证

后端全量单元测试：

```powershell
cd backend
uv run pytest -q
```

结果：

```text
83 passed
```

API contract 验证：

```powershell
cd backend
uv run python scripts/export_api_contract.py
```

结果：

```text
126 routes
```

新增测试：

1. `AnalyzeRankJumpUseCase` 会完整传递 query DTO 到 port。
2. `AnalyzeSteadyRiseUseCase` 会完整传递 query DTO 到 port。
3. legacy adapter 会把 rank jump 查询参数和信号阈值转换到旧 service。
4. legacy adapter 在不计算信号时保持 `signal_thresholds=None`。

---

## 遗留项

1. Level 3 仍需继续迁移：
   - `routers/analysis.py`
   - `routers/stock.py`
   - `routers/sector.py`
   - `routers/industry_detail.py`
   - `routers/strategies.py`

2. 当前 `rank_jump_service_db.py` 与 `steady_rise_service_db.py` 仍位于旧 `app.services`，本次只通过 infrastructure adapter 包装，后续可按风险逐步内迁或重命名为 read repository。

3. 缓存 key 与算法仍由旧 service 维护。后续如果迁移算法本体，需要补充固定日期的结果一致性测试，覆盖排序、空结果、`sigma_*` 字段和信号开关两种模式。

4. `admin.py` 的数据导入/删除 command 仍需随 MarketData / Analysis 后续迁移拆分。

---

## 后续建议

下一批建议迁移 `routers/analysis.py` 中的基础查询，但 `/api/hot-spots/full` 与 BoardHeat 边界有交叉，应单独评估或留到 BoardHeat 批次处理。
