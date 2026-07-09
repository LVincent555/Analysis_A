# RES-022: Analysis 策略查询侧迁移结果

**日期**: 2026-07-08
**状态**: [PARTIAL]
**类型**: Infra / Backend / Architecture / Migration / Testing
**层级**: Backend
**关联**: DEC-002, SUG-003, RES-021

---

## 结果摘要

已完成 DEC-002 Level 3 的第六批迁移：`strategies.py` 中的单针下二十策略查询迁入 `contexts.analysis`，旧 router 退为兼容入口。

本次只移动策略查询编排边界，不重写策略算法本体。`NeedleUnder20Strategy`、`get_washout_detector`、`numpy_cache` 与统一 API cache 仍作为 legacy infrastructure 依赖保留，避免把架构迁移和算法行为变更混在一起。

---

## 已完成改动

1. 新增 Analysis strategy 查询 DTO：
   - `GetNeedleUnder20StocksQuery`
   - `GetNeedleUnder20StockDetailQuery`

2. 新增 application port：
   - `StrategyAnalysisQueryPort`

3. 新增查询用例：
   - `GetNeedleUnder20StocksUseCase`
   - `GetNeedleUnder20StockDetailUseCase`

4. 新增 infrastructure adapter：
   - `LegacyNeedleUnder20StrategyAdapter`

5. 新增 API adapter：
   - `contexts.analysis.api.strategy_router`

6. 旧 `app.routers.strategies` 退为兼容入口。

---

## API 契约

保持以下路径不变：

```text
GET /api/strategies/needle-under-20
GET /api/strategies/needle-under-20/{stock_code}
```

API contract 导出结果：

```text
126 routes
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
98 passed
```

新增测试：

1. strategy use case 完整委托给 port。
2. legacy strategy adapter 可计算并写入 `needle20` API cache。
3. 单股策略详情可保留行业字段。
4. 架构边界检查通过，application 层未引入 FastAPI、SQLAlchemy、JWT、`app.services` 或 `app.core`。
5. API contract 保持 126 routes，策略端点已切换到 `contexts.analysis.api.strategy_router`。

---

## 遗留项

1. 策略算法本体仍位于旧 `app.services.strategies`，当前只由 infrastructure adapter 包装。
2. `min_score` 参数在旧实现中未实际参与过滤，本次为保持行为兼容没有顺手修正；后续若要调整策略语义，应另立 PRB/SUG。
3. `/api/hot-spots/full` 已在后续 RES-023 中迁入 Analysis 查询侧。

---

## 后续建议

DEC-002 Level 3 尚余 `/api/hot-spots/full`，应先收口 Analysis 热点榜查询，再进入 Level 4。
