# RES-018: Analysis 基础查询侧迁移结果

**日期**: 2026-07-08
**状态**: [PARTIAL]
**类型**: Infra / Backend / Architecture / Migration / Testing
**层级**: Backend
**关联**: DEC-002, SUG-003, RES-017

---

## 结果摘要

已完成 DEC-002 Level 3 的第二批 Analysis 查询侧迁移：`/api/dates`、`/api/analyze/{period}`、`/api/market/volatility-summary` 从旧 `routers/analysis.py` 的业务编排中迁入 `contexts.analysis`。

`/api/hot-spots/full` 暂时保留在旧兼容入口，因为它与热点榜/BoardHeat 边界有交叉，后续应在 BoardHeat 或 Analysis/BoardHeat 协作边界明确后再迁移。

---

## 已完成改动

1. 新增 Analysis 基础查询 DTO：
   - `AnalyzePeriodQuery`
   - `MarketVolatilitySummaryQuery`

2. 新增 Analysis 基础查询 port：
   - `BasicAnalysisQueryPort`

3. 新增查询用例：
   - `ListAvailableDatesUseCase`
   - `AnalyzePeriodUseCase`
   - `GetMarketVolatilitySummaryUseCase`

4. 新增 infrastructure adapter：
   - `contexts.analysis.infrastructure.basic_analysis.LegacyBasicAnalysisQueryAdapter`
   - 继续调用旧 `analysis_service_db` 与 `numpy_cache`，不改缓存 key 和分析算法。

5. 新增 API adapter：
   - `contexts.analysis.api.basic_router`

6. `app.routers.analysis` 退为兼容入口：
   - include 新 `basic_analysis_router`
   - 仅保留 legacy `/api/hot-spots/full`

---

## API 契约

保持以下路径不变：

```text
GET /api/dates
GET /api/analyze/{period}
GET /api/market/volatility-summary
GET /api/hot-spots/full
```

API contract 导出结果：

```text
126 routes
```

迁移后的 endpoint：

```text
GET /api/dates -> app.contexts.analysis.api.basic_router.get_available_dates
GET /api/analyze/{period} -> app.contexts.analysis.api.basic_router.analyze_period
GET /api/market/volatility-summary -> app.contexts.analysis.api.basic_router.get_market_volatility_summary
GET /api/hot-spots/full -> app.routers.analysis.get_hot_spots_full
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
85 passed
```

新增测试：

1. 基础分析查询 use case 会完整委托给 port。
2. legacy adapter 会把 `AnalyzePeriodQuery` 翻译为旧 `analysis_service_db.analyze_period(...)` 参数。
3. legacy adapter 会把 `MarketVolatilitySummaryQuery` 翻译为旧 `numpy_cache.get_market_volatility_summary(days=...)`。

---

## 遗留项

1. `/api/hot-spots/full` 仍在旧 router 中，等待 BoardHeat/热点榜边界明确。
2. `analysis_service_db.py` 仍位于旧 `app.services`，当前只通过 infrastructure adapter 包装。
3. Level 3 后续仍需迁移：
   - `stock.py`
   - `sector.py`
   - `industry_detail.py`
   - `strategies.py`
   - `industry.py`

---

## 后续建议

下一批建议优先处理 `stock.py` 或 `sector.py` 查询侧。`stock.py` 更靠 MarketData 基础 read model，`sector.py` 路由内计算更多且通配路径顺序敏感，建议先做 `stock.py` 建立 MarketData read adapter 形状。
