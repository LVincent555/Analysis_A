# RES-019: MarketData 股票查询侧迁移结果

**日期**: 2026-07-08
**状态**: [PARTIAL]
**类型**: Infra / Backend / Architecture / Migration / Testing
**层级**: Backend
**关联**: DEC-002, SUG-003, RES-018

---

## 结果摘要

已完成 DEC-002 Level 3 的第三批迁移：`routers/stock.py` 中的股票查询入口迁入 `contexts.market_data`，旧 router 退为兼容入口。

本次迁移建立了 MarketData read adapter 的基本形状，同时保留旧 `stock_service_db`、`numpy_cache` 与信号计算链路，不改变外部 API 与缓存/算法行为。

---

## 已完成改动

1. 新增 MarketData 查询 DTO：
   - `GetStockRawDataQuery`
   - `SearchStockFullQuery`
   - `SearchStockQuery`
   - `StockSignalThresholdSettings`

2. 新增 MarketData port：
   - `StockQueryPort`

3. 新增查询用例：
   - `GetStockRawDataUseCase`
   - `SearchStockFullUseCase`
   - `SearchStockUseCase`

4. 新增 infrastructure adapter：
   - `contexts.market_data.infrastructure.stock_queries.LegacyStockQueryAdapter`
   - `/api/stocks/raw-data` 的 Numpy cache 读取逻辑从 router 迁入 adapter。
   - `/api/stock/search` 与 `/api/stock/{stock_code}` 继续通过旧 `stock_service_db` 执行。
   - 股票详情中的信号阈值转换为旧 `SignalThresholds`，暂不拆信号算法。

5. 新增 API adapter：
   - `contexts.market_data.api.stock_router`

6. 旧 `app.routers.stock` 退为兼容入口。

---

## API 契约

保持以下路径不变：

```text
GET /api/stocks/raw-data
GET /api/stock/search
GET /api/stock/{stock_code}
```

API contract 导出结果：

```text
126 routes
```

迁移后的 endpoint：

```text
GET /api/stocks/raw-data -> app.contexts.market_data.api.stock_router.get_stock_raw_data
GET /api/stock/search -> app.contexts.market_data.api.stock_router.search_stock_full
GET /api/stock/{stock_code} -> app.contexts.market_data.api.stock_router.query_stock
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
88 passed
```

新增测试：

1. MarketData stock use case 会完整委托给 port。
2. legacy stock adapter 会从 Numpy cache 构造 `/api/stocks/raw-data` 响应。
3. legacy stock adapter 会把搜索参数与信号阈值转换到旧 `stock_service_db`。

---

## 遗留项

1. `stock_service_db.py` 仍位于旧 `app.services`，当前只通过 adapter 包装。
2. 股票详情的 signals 仍属于 Analysis 信号增强逻辑，后续可在 Analysis/MarketData 边界稳定后拆分。
3. Level 3 仍需迁移：
   - `sector.py`
   - `industry.py`
   - `industry_detail.py`
   - `strategies.py`
   - `/api/hot-spots/full`

---

## 后续建议

下一批建议处理 `sector.py`。它既有 MarketData read model，也有较多 router 内直接计算和路径顺序敏感问题，迁移时应优先保持路由顺序与空结果行为。
